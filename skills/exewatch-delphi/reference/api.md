# ExeWatch Delphi SDK 0.25.0 - API reference

Every name below was read in `ExeWatchSDKv1.pas` 0.25.0 and used in a program compiled with Delphi 13
(`dcc32`, `-U` pointing at the SDK folder). Behaviour marked **run** was observed against a local HTTP
listener; **read** means from the source only.

Declared in `ExeWatchSDKv1` unless stated. `EW` and `ExeWatch` are the same function (the global instance).

## TExeWatchConfig (a record)

Build it with `TExeWatchConfig.Create(ApiKey, CustomerId)`, which fills the defaults; set fields; pass it to
`InitializeExeWatch(Cfg)` or `TExeWatch.Create(Cfg)`. The instance keeps a copy: `EW.Config` is read-only.

| Field | Default | Meaning |
|---|---|---|
| `ApiKey` | argument | prefix picks the platform; checked at construction |
| `CustomerId` | argument | may be `''` (see the empty-customer rule in SKILL.md) |
| `AppVersion` | `''` | your release label; shown per event and device |
| `AppBinaryVersion` | `''` | `''` = file version of the exe, then its product version, else `'not available'` |
| `BufferSize` | `100` | events held in memory before a write to disk (the server may override) |
| `FlushIntervalMs` | `5000` | how often the buffer is written |
| `RetryIntervalMs` | `30000` | wait after a failed upload |
| `StoragePath` | `%LOCALAPPDATA%\ExeWatch\pending\<key[1..16]>` | queue directory |
| `SampleRate` | `1.0` | share of Debug/Info/Warning kept; Error and Fatal bypass it |
| `GaugeSamplingIntervalSec` | `30`, minimum `10` | period of periodic gauges |
| `MaxPendingAgeDays` | `7` | unsent files older than this are deleted; `0` = never |
| `AnonymizeDeviceId` | `False` | hash user name and host name inside the device id (GDPR) |
| `Endpoint` | `''` = `https://exewatch.com` | base URL, no trailing slash; tests and self-hosting only |
| `GlobalTags` | empty | `TArray<TPair<string, string>>`, applied before the first event |
| `InitialCustomDeviceInfo` | empty | `TArray<TPair<string, string>>`, sent with the first device info |
| `DeviceInfo` | from the system | record; `DeviceInfo.DeviceId` (default `user@host`) can be overridden |

`InitializeExeWatch(Key, Customer, AppVersion = '', AnonymizeDeviceId = False)` is the short form of the
same thing. Both overloads raise `Exception` for a key that does not start `ew_win_`, `ew_lin_`, `ew_mac_`,
`ew_and_`, `ew_ios_` or `ew_desk_` (run); the global instance stays `nil`.

## Lifetime and access

| Call | Behaviour |
|---|---|
| `InitializeExeWatch(...)` | creates the global instance; replaces an existing one. Starts a shipper thread and a persist thread, queues device info, logs `Application started` (tag `exewatch`). 13 ms here (run) |
| `FinalizeExeWatch` | `Shutdown` + free; one last upload attempt, blocking. The unit's `finalization` calls it too (run: events logged before an unhandled exception arrived with no explicit call) |
| `ExeWatchIsInitialized` | `True` between the two |
| `EW` / `ExeWatch` | the instance; raises `Exception` when there is none (run) |
| `TExeWatch.Create(Cfg)` / `Free` | extra instances (one per tenant, see `server-and-targets.md`). `Free` shuts down |
| `Shutdown` (method) | stops the threads and clears all callbacks; the global instance stays assigned (run) |

Thread safety (read, plus run with 8 threads x 250 events, all 2021 events arrived): `Log` and the level
methods, counters, gauges, tags, user, custom device info, `Flush`, `WaitForSending`, `GetPendingCount` take
internal locks and are callable from any thread. `SetUser` and `SetTag` are process-wide, not per thread.
Breadcrumbs and timings are per thread.

## Logging

```delphi
EW.Debug(Msg, Tag);  EW.Info(Msg, Tag);  EW.Warning(Msg, Tag);  EW.Error(Msg, Tag);  EW.Fatal(Msg, Tag);
EW.Info('User %s from %s', [UserName, IP], 'auth');            // Format overload: (Format, Args, Tag)
EW.Log(llWarning, 'text', 'orders', LJson);                    // extra data: SDK owns LJson
EW.Log(llInfo, 'text', 'tag', ATimestamp, AThreadId);          // forward from another logger
EW.ErrorWithException(E, 'tag', 'context');                    // 'context: E.Message'
```

- Default tag is `'main'`. Levels: `llDebug, llInfo, llWarning, llError, llFatal` (`TEWLogLevel`).
- An empty or blank message is dropped. A message longer than the server limit (50000 until the server says
  otherwise) is cut and ends with `[MESSAGE TRUNCATED]`.
- `Error` and `Fatal` attach `stack_trace` (or `no_stacktrace_reason`), `symbol_source`, and the calling
  thread's breadcrumbs, then clear those breadcrumbs (run).
- `ErrorWithException(E, ...)` adds `exception_class`, `exception_message` and the trace taken at the raise
  (run: a worker thread's exception, logged later from the main thread, showed `TW.Execute (line 13)`).
  `E = nil` is accepted and logs a plain message.
- Timestamps are UTC (`...Z`). Event JSON also carries thread id, process id, session id.
- Global tags and the user ride on every event as `tag_<key>`, `user_id`, `user_email`, `user_name` (run).
- Automatic events: Fatal `Unhandled exception: <msg>` (ExceptProc, tag `exception`, `exception_source:
  unhandled`); Error `GUI exception: <msg>` (VCL/FMX hook, tag `exception`, `exception_source: vcl|fmx`);
  Warning `GUI application detected but no VCL/FMX exception hook installed...` (tag `exewatch`).

## User, customer, tags

| Call | Notes |
|---|---|
| `SetUser(Id, Email = '', Name = '')`, `SetUser(TUserIdentity)`, `ClearUser`, `GetUser` | one user for the whole process: a server must put the user in extra data instead |
| `TUserIdentity.Create(Id, Email, Name)` | record with `IsEmpty` |
| `SetCustomerId(Id)`, `GetCustomerId` | first non-empty id (or a change) queues device info; every event still in memory is sent under the id that is current when it is written |
| `SetTag(Key, Value)`, `SetTags(array)`, `RemoveTag`, `ClearTags`, `GetTags` | `TArray<TPair<string, string>>` |

A customer change re-sends the device info under the new id. Setting the same id again does nothing.

## Breadcrumbs

```delphi
EW.AddBreadcrumb('Pressed Save', 'ui');                         // type btCustom
EW.AddBreadcrumb(btNavigation, 'ui', 'Opened orders', LData);   // LData: TJSONObject, SDK owns it
EW.GetBreadcrumbs;  EW.ClearBreadcrumbs;
```

`TBreadcrumbType`: `btClick btNavigation btHttp btConsole btCustom btError btQuery btTransaction btUser
btSystem btFile btState btForm btConfig btMessage btDebug`. At most 20 per thread (oldest dropped). Attached to
Error/Fatal events of the same thread only, then cleared; Info events carry none (run).

## Timings and traces

```delphi
EW.StartTiming('order.save', 'orders');             // id, tag (default tag is '' here, not 'main')
EW.StartTiming('order.%d', [Id], 'orders');          // format form
try
  Save;
  EW.EndTiming('order.save');                        // Double ms; Info '[TIMING] order.save: 1,20ms'
except
  EW.EndTiming('order.save', nil, False);            // success = False
  raise;
end;
EW.EndTiming;                                        // ends the last started on this thread
EW.CancelTiming('id');  EW.CancelTiming;  EW.IsTimingActive('id');  EW.GetActiveTimings;
EW.StartTrace('report');  ...nested StartTiming/EndTiming...  EW.EndTrace;   // Double ms, -1 if none
```

- `EndTiming` returns `-1` and logs a Debug line (tag `exewatch`) when the id is unknown **or was started on
  another thread** (run).
- Starting an id that is already open closes the old one as failed (Warning, `auto_closed`). Past 100 open
  timings on a thread the oldest is closed the same way.
- Inside `StartTrace`/`EndTrace` the nested timings carry `trace_id`, `span_id`, `parent_span_id` (run).
  One open trace per thread; `EndTrace` force-closes forgotten children as failed.
- Metadata objects: `StartTiming(Id, Tag, LMeta)` and `EndTiming(Id, LMeta, Success)`; the SDK frees both.

## Metrics

```delphi
EW.IncrementCounter('orders', 1, 'shop');            // name, delta (default 1.0), tag
EW.RecordGauge('queue', 9, 'shop');
EW.RegisterPeriodicGauge('heap_mb', function: Double begin Result := HeapMb; end, 'sys');
EW.UnregisterPeriodicGauge('heap_mb');
```

Counters sum, gauges keep last/min/max/avg, keyed by name plus tag, pre-aggregated in memory and written
about every 30 s (`EXEWATCH_METRIC_FLUSH_INTERVAL_MS = 30000`; the source comments say 60, run: first upload
about 30 s after start). `Flush`/`WaitForSending` write them at once. Up to 20 periodic gauges
(`EXEWATCH_MAX_REGISTERED_GAUGES`); the callback runs on a background thread, first sample one interval
after registration, exceptions in it are swallowed. A plan limit answers HTTP 429 and the metric file is
dropped.

## Device info

- Sent automatically (hardware, OS, binary version, custom info) when a customer id is known; one `.ewdevice` file.
- `EW.SetCustomDeviceInfo(Key, Value)` only stores the pair. It reaches the server through:
  - `EW.SendCustomDeviceInfo` - sends the pairs set at run time only (no hardware, not the initial pairs) (run);
  - `EW.SendDeviceInfo` - re-sends hardware plus initial and run-time pairs merged (run).
- `ClearCustomDeviceInfo(Key)`, `ClearAllCustomDeviceInfo`. Whether the server replaces or merges is not
  verifiable from the SDK.
- `TExeWatchHelper.GetHostname`, `GetUsername`, `GetDeviceId`, `GetDefaultStoragePath`: class functions.

## Events and listener

```delphi
type
  TForwarder = class(TInterfacedObject, IExeWatchClientListener)   // compiled and run
    procedure OnExeWatchLog(ALevel: TEWLogLevel; const AMessage, ATag: string);
    procedure OnExeWatchLogsSent(AAcceptedCount, ARejectedCount: Integer);
    procedure OnExeWatchError(const AErrorMessage: string);
  end;

EW.OnError := Handler;        // procedure(const AErrorMessage: string) of object
EW.OnLogsSent := Handler;     // procedure(AAcceptedCount, ARejectedCount: Integer) of object
EW.OnDeviceInfoSent := H;     // procedure(ASuccess: Boolean; const AErrorMessage: string) of object
EW.OnCustomDeviceInfoSent := H;
EW.ClientListener := TForwarder.Create;    // reference counted: never Free it
```

`IExeWatchClientListener` has `OnExeWatchLog(ALevel, AMessage, ATag)` (called on the thread that logged, only
for events that pass the level and sampling filters), `OnExeWatchLogsSent`, `OnExeWatchError` (shipper
thread). `Shutdown` sets all of them to `nil`. Use it to forward events to another logger.

## Other members

`EW.Flush` (buffer and metrics to disk, no upload), `EW.WaitForSending(Seconds)` (flush, then wait for the
queue to drain; returns events left), `EW.GetPendingCount` (files plus buffered events), `EW.Enabled`
(local kill switch: log events are dropped; counters and gauges still accumulate), `EW.SessionId`, `EW.DeviceInfoSent`,
`EW.GetAppVersion`.

## Guide and docs versus the code

Where the shipped `INTEGRATION_GUIDE.md`, the DevGuide or a header comment disagrees with the source, trust
the source:

| Text says | Code does |
|---|---|
| Deferred customer id: "logs are sent normally, even without customer_id" | Nothing is written or sent while it is empty; lost if the process ends first (run) |
| `Config.InitialCustomDeviceInfo := reference to procedure(...)` | Not valid Delphi (compile error E2029); the field is `TArray<TPair<string, string>>` (compiled) |
| `SetCustomDeviceInfo`: "changes are sent on next batch" | It only stores; send with `SendCustomDeviceInfo` or `SendDeviceInfo` (run) |
| `SendCustomDeviceInfo` "DEPRECATED" | Not marked in the source; it is the call that sends run-time pairs |
| Default endpoint `https://api.exewatch.com` | `EXEWATCH_ENDPOINT = 'https://exewatch.com'` |
| No map: "a column of bare addresses" | module+offset and PE export names, e.g. `p3.exe!__dbk_fcall_wrapper+0x2B8EAA` (run) |
| Counters and gauges flushed "every 60 seconds" | 30 s constant, about 30 s observed (run) |
| Source header: "Win32 walk lands with the per-architecture work" | Win32 traces work (run) |
| DMVC sample README: put the key in the `.dpr` | the sample keeps it in `ExeWatchConfig.pas`; never copy a key from a sample |
