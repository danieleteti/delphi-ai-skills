# Servers, services, tenants, other targets

Run = a program built with Delphi 13 and run against a local listener. Read = from the SDK or sample source.
For DelphiMVCFramework controllers, filters and the exception handler, use the `dmvcframework` skill.

## A process with no GUI (service, console, web server)

- Uses `ExeWatchSDKv1` only; no `.VCL`/`.FMX` unit.
- Initialize once at start-up: the `.dpr` before the server runs, or a service's `OnStart`. Finalize at stop
  (`FinalizeExeWatch`, or let the unit's finalization do it). A server stopping under a service manager has
  seconds, not minutes: `FinalizeExeWatch` waits for one upload attempt (2.1 s with a closed port, run).
- Set `Cfg.StoragePath` explicitly for services and servers. The default derives from `%LOCALAPPDATA%`
  and the key only, which is the same folder for every copy running under the same account (sample README).
- Set `Cfg.AppVersion` yourself: a server binary rarely has a useful VERSIONINFO, and "which release is
  failing" is the first question.
- Set `Cfg.DeviceInfo.DeviceId` per running copy (default `user@host` makes every copy one device).
- A Windows service is told apart from a GUI program by its window station, so the "no hook" Warning is not
  logged for it (read); a console program, or a `{$APPTYPE CONSOLE}` project, is never a GUI app.
- Unhandled exceptions in the main thread reach the Fatal `Unhandled exception: ...` event (run). Exceptions
  in worker threads do not (run): catch in `Execute` and call `EW.ErrorWithException`.

## Per request (compiled and run: 2 requests, one failing)

```delphi
procedure HandleRequest(const AEndpoint: string; AHandler: TProc);
begin
  EW.ClearBreadcrumbs;                    // pooled thread: drop what the last request left
  EW.AddBreadcrumb('request: ' + AEndpoint, 'http');
  EW.IncrementCounter('http.requests', 1, 'http');
  EW.StartTiming(AEndpoint, 'http');
  try
    try
      AHandler;
      EW.EndTiming(AEndpoint);
    except
      on E: Exception do
      begin
        EW.EndTiming(AEndpoint, nil, False);
        EW.IncrementCounter('http.errors', 1, 'http');
        EW.ErrorWithException(E, 'http', AEndpoint);
        raise;                            // let the framework answer 500
      end;
    end;
  finally
    EW.CancelTiming(AEndpoint);           // no-op when already ended
  end;
end;
```

Why each line: breadcrumbs are cleared only when an Error consumes them, so a request that ended cleanly
leaves its trail on the pooled thread (sample README); a timing left open stays on the thread and is
inherited by the next request. The timing, counter and error carry no user: `SetUser` is process-wide, so
on a server put the user in the extra data of the call, `EW.Log(llInfo, Msg, Tag, LJson)` with `user_id` in
`LJson`.

`ErrorWithException` accepts `E = nil`, so it is safe in a framework handler that may be called without an
exception (read).

## One customer per request: one TExeWatch per tenant

A batch carries `customer_id` and `device` once, so one instance cannot attribute events to different
customers, and calling `SetCustomerId` per request re-tags whatever is still in the buffer (events are
stamped when written, run). The multi-tenant sample (`DelphiSDKSingleProcessMultiTenant`) therefore makes one
instance per tenant:

```delphi
function CreateTenantLogger(const AApiKey, ATenant, AQueueRoot, AInstance: string): TExeWatch;
var
  Cfg: TExeWatchConfig;
begin
  Cfg := TExeWatchConfig.Create(AApiKey, ATenant);
  Cfg.StoragePath := TPath.Combine(TPath.Combine(AQueueRoot, AInstance), ATenant);
  Cfg.DeviceInfo.DeviceId := AInstance + '@' + TExeWatchHelper.GetHostname;
  Result := TExeWatch.Create(Cfg);        // freed with Free: shuts down, one send attempt
end;
```

Compiled and run: two tenants wrote to `inst01\ACME` and `inst01\GLOBEX` and arrived under their own customer.

- `StoragePath` per instance is mandatory (same key means same default folder).
- Keep the tenant list fixed at start-up, from configuration. Each instance costs a shipper thread, a persist
  thread, a queue folder and a device record; creating one on demand lets a request header decide how many
  threads the process runs. The sample says it fits a handful to a few dozen tenants, not thousands.
- The automatic hooks (unhandled exception, VCL/FMX) report only through the **global** instance. If you
  never call `InitializeExeWatch`, they report nothing (read).
- Drain with one shared deadline across instances (`WaitForSending` with the remaining seconds).
- Resolve the tenant once per request and carry it in the request context, not in a thread variable.

## DelphiMVCFramework and WebBroker

Sample folders in the samples repository: `DelphiDMVCFramework`, `DelphiWebBroker`,
`DelphiSDKSingleProcessMultiTenant`. What they do (read):

- DMVC: initialize in the `.dpr`; forward the framework's LoggerPro output to `EW.Log(Level, Msg, Tag,
  Timestamp, ThreadId)` so no controller changes are needed (`TLogType` in `LoggerPro.pas` has the same
  order as `TEWLogLevel`, 0 to 4, which the sample's `TEWLogLevel(Ord(...))` cast relies on); call
  `EW.ErrorWithException(E, 'unhandled')` in the engine's exception handler; `FlushExeWatch` (which is
  `EW.WaitForSending(5)`) after the server stops. Forwarding the logger and logging in the handler can report
  one failure twice: check the dashboard.
- WebBroker: the web module wraps each endpoint in a handler like `HandleRequest` above.
- ISAPI or an Apache module is a DLL: the SDK suppresses the GUI warning when `IsLibrary` (read). Initialize
  once per process from the module's start-up, never per request.

## The DLL route

For Delphi older than XE8, a non-Delphi host, or one binary shared by several languages. Files in
`SDK\DLL`: `ExeWatchSDKv1DLL.dll` (Win32), `ExeWatchSDKv1DLL_x64.dll`, `ExeWatchSDKv1Imports.pas`, a C
header. README: SDK 0.23.0, ABI 4 (older than the 0.25.0 units).

```delphi
uses ExeWatchSDKv1Imports;
if EWInitialize('ew_win_XXXXXXXX', 'ACME', '1.0.0') = EW_OK then
begin
  EWInfo('Application started', 'startup');
  EWError('Something failed', 'billing');
  ew_Shutdown;
end;
```

Compiled with Delphi 13, **not run**: the config record has no endpoint field, so any run would reach the
real service. Functions return integer codes (`EW_OK = 0`, negative errors) instead of raising; strings are
`PWideChar`; define `EW_DYNAMIC_LOAD` and call `EWLoadDLL` to degrade gracefully when the DLL is missing. It
does not capture exceptions for you: pass your own trace with `EWErrorWithStackTrace`. Check the DLL's own
README before using a call this skill does not list.

## Runtime packages

The `DelphiVCLWithPackages` sample puts `ExeWatchSDKv1` and `ExeWatchSDKv1.VCL` in one package that every
module package requires, so the whole process shares one global `EW` (read; not built here). A unit linked
into two modules exists twice, with two globals: one place only.

## FMX, Linux, Android

- FMX: `ExeWatchSDKv1.FMX` instead of `.VCL`; same hook (`Application.OnException`, Error `GUI exception:`,
  `exception_source: fmx`). Compiled on Win32 (run not done).
- Linux: `ExeWatchSDKv1` compiles with `dcclinux64` (13). No stack traces (reason 4); the temp folder holds
  the queue. Not run.
- Android: sample `DelphiAndroid` (FMX, key prefix `ew_and_`, the Internet permission enabled in the project).
  The queue lives in the app files folder; no stack traces. Not built here.
- macOS and iOS keys (`ew_mac_`, `ew_ios_`) pass the key check and the device info names `macos`; the unit has
  no hardware-collection code for Apple targets. Not compiled here (no compiler): unverified.
