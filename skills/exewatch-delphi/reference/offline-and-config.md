# Buffering, persistence, retry, purge, sampling, server configuration

All of it observed with Delphi 13 console and VCL programs against a local HTTP listener on 127.0.0.1 (200,
401, 422, 429, 500 answers, a closed port, a configuration reply). Items marked **read** come from the
source only. The real service was never contacted.

## The path of one event

1. `EW.Info/Error/...` (any thread). The event is dropped, with no trace, if: `EW.Enabled` is False; the
   server switched the application off; the message is blank; the level is below the server `min_level`
   (this includes Error and Fatal); or, for Debug/Info/Warning only, sampling rejects it. Timings are Info
   events, so level and sampling apply to them; counters and gauges are not logged events.
2. Listener `OnExeWatchLog` is called (calling thread) for events that passed step 1.
3. Error/Fatal get the stack trace and breadcrumbs. The event goes to the **memory buffer**.
4. A persist thread or the shipper writes the buffer to a `.ewlog` file **only when a customer id is set**:
   - an Error or Fatal: at once, on the persist thread, at most one such write per second (the rest wait for
     the timer);
   - the buffer reaches the batch size (`BufferSize`, 100 by default, or the server's `batch_size`), written
     on the logging thread;
   - every `FlushIntervalMs` (5 s) on the shipper thread (a longer server `flush_interval_ms` stretches this);
   - the first event (`Application started`) when a customer id is known at start;
   - `EW.Flush`, `EW.WaitForSending`, `FinalizeExeWatch`.
5. The shipper thread uploads files oldest first.

A hard kill (task manager, power loss) loses what was still in the memory buffer: up to 5 s of Info events,
nothing from an Error after its write (milliseconds). An unhandled exception calls `Flush` itself.

## Where things are written

Default `StoragePath`: `%LOCALAPPDATA%\ExeWatch\pending\<first 16 chars of the API key>` (falls back to the
temp folder), `<temp>\ExeWatch\pending\<prefix>` on other non-Windows targets, the app files directory on Android (read). The
directory comes from the **key only**: two processes or two `TExeWatch` instances with the same key share one
queue and compete for its files. Set `StoragePath` explicitly for every instance in a server, and for
services (run: separate paths kept the tenants apart).

| File | Content |
|---|---|
| `<date>_<time>_<n>_<thread>.ewlog` | JSON: `customer_id`, `device`, `events[]`; UTF-8 with a BOM |
| `<date><time>_<thread>_<n>.ewdevice` | device info (hardware plus custom info), or custom-info-only |
| `...ewmetric` | counters and gauges |
| `.sending` | the file being uploaded; renamed back to its extension at the next start if the process died |
| `.tmp` | a log file being written (written, then renamed: a kill leaves no half file; device and metric files are written in place) |
| `exewatch_sdk.log` | SDK diagnostics: start line, every failed send, purge, `SetCustomerId` (at most 1000 lines, 7 days) |
| `exewatch_api_trace.log` | each request and response, first 500 characters (rotated at 10 MB or 12 h) |

Everything is plain text in the user's profile. The `.ewlog`, `.ewdevice` and trace files contain your
messages, extra data, user, and the device info. That info carries **host name, user name, the full command
line, executable path, working directory and the machine's local IP addresses** (run). Do not pass secrets
on the command line of a monitored program, and do not log them. `AnonymizeDeviceId := True` replaces the
user name and the device id with hashes (read); the `Hostname` field and the hardware info (command line,
paths, which usually contain the user name) are not touched.

## Upload and retry

One file per request; the first failure ends the pass and the shipper waits `RetryIntervalMs` (30 s) before
trying again, from the oldest file. While files are pending and none fails, it loops every 100 ms. A failing
file therefore **blocks every file behind it** (run: a device-info file refused with 500 held the logs back;
three attempts in 70 s, 30 s apart).

| Answer | Result | Seen |
|---|---|---|
| 200 | file deleted; `OnLogsSent(accepted, rejected)` or `OnDeviceInfoSent`; a `config` object in the reply is applied | run |
| 422 on logs | the events the reply points at are removed and the rest retried; if none remain or the reply cannot be read, the file is deleted. 422 on device info: deleted | run (reply without detail: deleted) |
| 429 (plan or quota limit) | file **deleted**, no retry, no `OnError` | run |
| 401, 403, 5xx, any other status | file kept, `OnError('HTTP n: ...')`, retry after `RetryIntervalMs` | run: 401 and 500 |
| no connection, timeout, TLS failure | file kept, `OnError('Send failed: ...')`, retry | run (closed port) |
| unreadable JSON, no `customer_id`, no events | file deleted | read |

So a wrong or revoked key (401/403) does not lose data at once; it queues until the purge. A plan limit (429)
does lose it.

Timeouts: connection 10 s, response 30 s when the SDK is compiled with Delphi 10.3 or later (read); older
compilers use the RTL defaults.

**After a restart** the leftovers are uploaded, `.sending` files first renamed back (run: three files left by
a failing run all arrived on the next start).

**Purge**: every hour the shipper deletes `.ewlog`, `.ewdevice`, `.ewmetric` and `.tmp` files whose creation
time is older than `MaxPendingAgeDays` (7; `0` disables) (read, not waited for).

## Shutdown and draining

- `FinalizeExeWatch` (or `Free` on an instance): final persist of events and metrics, then uploads until the
  first failure, and the caller **waits for it**. 58 ms when the listener answered; 2.1 s with a closed
  port (run). A network that drops packets can
  take up to the connection timeout per attempt (read, not measured).
- `EW.WaitForSending(Seconds)`: flushes, then polls until the queue is empty or the time is up; returns how
  many events remain. With an empty customer id it never drains (run: `left=3`).
- `EW.Flush` only writes to disk; the shipper uploads afterwards.
- With several instances, give `WaitForSending` a shared deadline (the multi-tenant sample computes the
  remaining seconds per instance): per-instance timeouts add up.

## Sampling and server-provided configuration

`Cfg.SampleRate` (1.0) is the starting rate for Debug/Info/Warning. Error and Fatal ignore it.

After an upload the reply may carry a `config` object. The SDK applies `version`, `flush_interval_ms`,
`batch_size`, `sampling_rate`, `max_message_length`, `enabled`, `min_level` (`debug` to `fatal`), and from
then on sends the header `X-Config-Version` (run: header `3` after a config of version 3). Effects, run with
`min_level: warning`, `max_message_length: 100`:

- Debug and Info events were dropped; the Warning and the Error went out.
- An Error of 300+ characters arrived at exactly 100, ending with `[MESSAGE TRUNCATED]`.
- `sampling_rate` replaces `SampleRate`; `enabled: false` silences everything, errors included (read).

The configuration lives in memory only: a restart starts from the local defaults until the first reply.
So a level or rate chosen in the console is not a local setting you can read back from `TExeWatchConfig`.

## Threads that touch the SDK

| Runs on | What |
|---|---|
| calling thread | `Log`, the level methods, `OnExeWatchLog`, breadcrumbs, timings, the write caused by a full buffer |
| persist thread | the write after an Error/Fatal |
| shipper thread | uploads, `OnError`, `OnLogsSent`, `OnDeviceInfoSent`, `OnCustomDeviceInfoSent`, `OnExeWatchLogsSent`, `OnExeWatchError`, the timer write, metric flush |
| sampler thread | periodic gauge callbacks |

Handlers must be quick and must not touch the UI directly. `Shutdown` clears the handlers before the threads
stop, so a form that is destroyed first is not called afterwards.
