---
name: exewatch-delphi
description: Use when adding, changing or debugging ExeWatch monitoring in a Delphi app - the ExeWatchSDKv1 unit, TExeWatch, InitializeExeWatch, remote logging, crash reporting, stack trace in production, application monitoring, telemetry (timings, counters, gauges, breadcrumbs), offline buffering, the map file, ExeWatchMapCLI. Triggers on "ExeWatch", "ExeWatchSDKv1", "TExeWatch", "application monitoring", "remote logging", "crash reporting", "stack trace in production", "telemetry in a Delphi app".
---

# ExeWatch Delphi SDK

ExeWatch (bit Time Professionals) collects logs, crashes, timings and metrics from an application. The
Delphi SDK is plain source: `ExeWatchSDKv1.pas` plus `ExeWatchSDKv1.VCL.pas` / `ExeWatchSDKv1.FMX.pas`.

**Verified against Delphi SDK 0.25.0** (`EXEWATCH_SDK_VERSION` in `ExeWatchSDKv1.pas`), ExeWatch product
1.90.1 (2026-11-05). Compiled on Delphi 13, 12 and XE8 (Win32), 13 (Win64, Linux64); run on 13 (Win32,
Win64) and XE8 (Win32), against a local HTTP listener only.

**Before writing code, compare the project's version** (`grep EXEWATCH_SDK_VERSION ExeWatchSDKv1.pas` in the
project or in `%EXEWATCH_SDK%`). If it is not `0.25.0`, read the interface section of that copy and check
every name below against it. The shipped `INTEGRATION_GUIDE.md` and the docs are partly stale: where they
disagree with the code, the code wins (table in `reference/api.md`).

## Critical rules - each one costs data or a day

1. **`EW` raises before `InitializeExeWatch` and after `FinalizeExeWatch`** (`Exception: ExeWatch not
   initialized`). Code that can run at start-up or in a `finalization` section: `if ExeWatchIsInitialized then`.
2. **An empty customer id keeps every event in memory.** Nothing reaches disk, nothing is sent; if the
   process ends before `EW.SetCustomerId('...')`, those events are gone. Pass a non-empty id (even a
   placeholder) unless the real one arrives within seconds.
3. **Initialize once per process**, at start-up. Never per request, per form or per thread: a second
   `InitializeExeWatch` destroys the first instance (its shutdown makes one send attempt) and starts new
   threads.
4. **The SDK owns every `TJSONObject` you hand it** (`Log` extra data, `AddBreadcrumb` data, `StartTiming`
   metadata, `EndTiming` end metadata), also when the call is filtered out. Do not free it, do not reuse it:
   freeing it is a double free (a leak test with and without the free confirms ownership).
5. **GUI app: add exactly one hook unit** (`ExeWatchSDKv1.VCL` or `.FMX`) after `ExeWatchSDKv1`. Without it
   exceptions raised in event handlers are never reported; the SDK only logs a Warning (tag `exewatch`).
   Service, console, DLL: add neither.
6. **A stack trace is only readable with symbols.** Detailed map file + stack frames, linked into the exe.
   Without any map a frame reads `MyApp.exe!__dbk_fcall_wrapper+0x1B7FFB`: a real name, the wrong one.
   Details in `reference/stacktraces.md`.
7. **Exceptions that escape a `TThread` are not reported** (no hook sees them). Catch in `Execute` and call
   `EW.ErrorWithException`.
8. **Callbacks run on SDK threads**: `OnError`, `OnLogsSent`, `OnDeviceInfoSent`, the listener's
   `OnExeWatchLogsSent`/`OnExeWatchError` and gauge callbacks. No VCL/FMX access; `TThread.Queue` instead.
9. **Breadcrumbs and timings are per thread.** `EndTiming` on another thread finds nothing and returns -1.
   On pooled server threads clear breadcrumbs at the start of each request.
10. **Never log secrets or personal data** (passwords, tokens, card numbers, full request bodies) in a
    message, tag, extra data, user, device info. Queued files are plain JSON on disk, and the device info
    carries the full command line, paths and local IPs. The API key is configuration: keep it out of public
    repos.
11. **`ReportMemoryLeaksOnShutdown := True` prints SDK-internal leaks** (`TSTExportCache`, thousands of
    `UnicodeString`) once any exception was raised. Win32 and Win64. They are the SDK's symbol cache, not
    your code: do not "fix" them by freeing things.

## Which unit declares what

| Identifier | Unit |
|---|---|
| `InitializeExeWatch`, `FinalizeExeWatch`, `EW`, `ExeWatch`, `ExeWatchIsInitialized`, `TExeWatch`, `TExeWatchConfig`, `TEWLogLevel`, `TBreadcrumbType`, `TUserIdentity`, `IExeWatchClientListener`, `TExeWatchHelper`, `EXEWATCH_SDK_VERSION` | `ExeWatchSDKv1` |
| (no identifiers; installs the GUI exception hook in its `initialization`) | `ExeWatchSDKv1.VCL` or `ExeWatchSDKv1.FMX` |
| `TJSONObject` for extra data | `System.JSON` |
| `TPair<string, string>` for `GlobalTags`, `InitialCustomDeviceInfo` | `System.Generics.Collections` |
| DLL route: `EWInitialize`, `EWInfo`, `ew_Shutdown` | `ExeWatchSDKv1Imports` |

Requirements: Delphi XE8 or later, Windows Vista or later, HTTPS (TLS 1.2) to the endpoint. `EXEWATCH_SDK`
is set by the RAD Studio setup and points at the SDK folder; add it to the Library Path, or copy the units
into the project.

## The four questions

**1. Start-up and shut-down** (VCL; compiled on Delphi 13):

```delphi
program MyApp;
uses
  Vcl.Forms,
  ExeWatchSDKv1,
  ExeWatchSDKv1.VCL,
  MainFormU in 'MainFormU.pas' {MainForm};
begin
  InitializeExeWatch('ew_win_XXXXXXXX', 'ACME', '1.2.3');   // api key, customer id, release label
  try
    Application.Initialize;
    Application.CreateForm(TMainForm, MainForm);
    Application.Run;
  finally
    FinalizeExeWatch;      // ships what is left; the unit's finalization does it too
  end;
end.
```

The key must start `ew_win_`, `ew_lin_`, `ew_mac_`, `ew_and_`, `ew_ios_` (or old `ew_desk_`); `ew_web_` and any
other prefix raise `Exception` from `InitializeExeWatch`. For more settings build a `TExeWatchConfig`
(`TExeWatchConfig.Create(Key, Customer)`, set fields, `InitializeExeWatch(Cfg)`): `reference/api.md`.
The RAD Studio menu **Project > ExeWatch > Enable ExeWatch Telemetry** generates `ExeWatchConfig.pas`
(`StartExeWatch`, `SetExeWatchCustomer`, `FlushExeWatch`; key constant `EXEWATCH_API_KEY`) and wires
`StartExeWatch('customer-name')` and `FlushExeWatch` into the `.dpr`. If a project has that unit, edit it; do
not add a second `InitializeExeWatch`.

**2. Error log, exception, user identity:**

```delphi
EW.Error('Payment refused', 'billing');                 // message, tag (default tag 'main')
EW.Error('Order %d failed for %s', [Id, Name], 'orders');
try
  Save;
except
  on E: Exception do
  begin
    EW.ErrorWithException(E, 'billing', 'Save failed'); // message becomes 'Save failed: <E.Message>'
    raise;
  end;
end;
EW.SetUser('u-42', 'jane@example.com', 'Jane Doe');      // on every later event; EW.ClearUser on logout
```

`Error` and `Fatal` get a stack trace automatically, plus the thread's breadcrumbs. Levels:
`Debug Info Warning Error Fatal`; every one has a `(Msg, Tag)` and a `(Format, Args, Tag)` form.
`ErrorWithException` keeps the trace taken where the exception was raised, even if you catch it far away.
Identity, tags, customer: `reference/api.md`.

**3. Unhandled exceptions with unit, function and line (32-bit VCL).** Uses: `ExeWatchSDKv1` +
`ExeWatchSDKv1.VCL` (above): the first catches what reaches `ExceptProc` (Fatal, `Unhandled exception: ...`),
the second what the VCL loop swallows (Error, `GUI exception: ...`, tag `exception`). Then produce and link
the symbols:

- Project Options > Delphi Compiler > Linking > **Map file = Detailed** (`dcc32 -GD`), **Stack frames on**
  (`-$W+`), debug information on. Without stack frames a Win32 trace silently drops frames.
- Link the map **into the exe**: `ExeWatchMapCLI MyApp.exe MyApp.map --delete-map` after each build (before
  code signing), or the IDE menu **ExeWatch > Link map file**. Result in the event: `symbol_source:
  "embedded"`. A `.map` left beside the exe works only where it sits (`symbol_source: "map_file"`).
- Win64 needs no stack frames; Win32 does. `reference/stacktraces.md` has the matrix and the CLI.

**4. Network down.** `EW.Info` never waits for the network. Events go to a memory buffer; a background
thread writes `.ewlog` JSON files to `%LOCALAPPDATA%\ExeWatch\pending\<first 16 chars of the key>\` and
uploads them oldest first. On any failure except HTTP 422/429 the file is kept and retried after 30 s
(`RetryIntervalMs`), for ever, until it is 7 days old (`MaxPendingAgeDays`) and purged. After a restart the
leftovers are sent. An Error or Fatal is written to disk at once (at most one such write per second);
ordinary events within 5 s (`FlushIntervalMs`) or 100 events (`BufferSize`); a hard kill can lose what was
still in memory. Full rules:
`reference/offline-and-config.md`.

## Reference index

| Open this | When |
|---|---|
| `reference/api.md` | exact signatures: config fields and defaults, every `TExeWatch` method, tags, identity, breadcrumbs, timings and traces, metrics, device info, listener; the "guide vs code" table |
| `reference/stacktraces.md` | empty or useless stack traces, 32 vs 64 bit, map file levels, `ExeWatchMapCLI`, IDE menu, `symbol_source`, `no_stacktrace_reason` |
| `reference/offline-and-config.md` | buffering, file layout, retry by HTTP status, purge, sampling, server-provided config, shutdown time, `StoragePath`, GDPR |
| `reference/server-and-targets.md` | web server, service, per-request pattern, one instance per tenant, DMVC, WebBroker, DLL route, packages, Linux, Android, FMX |

For DelphiMVCFramework servers, load the `dmvcframework` skill for controllers, filters and the exception
handler; this skill covers only the ExeWatch calls.

## What not to do

- `InitializeExeWatch` in a request handler, a form `OnShow` or a thread.
- Logging in a tight loop "to see progress": every event costs quota and disk. Count with
  `IncrementCounter` instead.
- `Cfg.Endpoint := ...` left in committed code; defining `LOCAL_EXEWATCH` (it points the default endpoint
  at an internal address).
- Reading `EW.Config` to change settings: it returns a copy. Set the config before initializing.
- Calling `EW.Shutdown` yourself: it leaves `ExeWatchIsInitialized` True. Use `FinalizeExeWatch`.
- Trusting a trace with no map: ask for the map, do not read the offsets.

## Not verified

Android, macOS and iOS targets (no compiler here), FMX at run time (it compiles on Win32), the DLL SDK at run
time (its API has no endpoint override, so any run would call the real service), the IDE menus (read from
the IDE source, not driven), the server's replace-or-merge behaviour for custom device info, the hourly
purge, behaviour on a network that drops packets instead of refusing them.
