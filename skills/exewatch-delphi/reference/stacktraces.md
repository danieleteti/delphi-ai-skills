# Stack traces: how they work and why they come out useless

Verified on Delphi 13 (`dcc32`, `dcc64`) with a small VCL program that raises from a timer event, calling
`EW.ErrorWithException`, `EW.Error`, and leaving one exception unhandled, against a local listener. The
shipped `STACKTRACE_MATRIX.md` (32 builds on Delphi 12 and 13, 512 per toolchain in the vendor's own suite)
agrees with every row marked **run** below; rows marked **matrix** were not re-run here.

## What the SDK does

- `ExeWatchSDKv1` hooks `Exception.GetExceptionStackInfoProc` (and `System.ExceptProc`) in its
  `initialization`. From then on **every exception object carries a stack captured at the raise**, including
  exceptions raised before `InitializeExeWatch`. The cost is small but not zero: 2000 raise/catch took 42 ms
  with the hook against 9 ms without, Win32, no map (run).
- `Error` / `Fatal` calls without an exception take the current stack instead.
- Win32 walks the EBP chain; Win64 uses `RtlCaptureStackBackTrace`. Linux and Android: no traces
  (`no_stacktrace_reason: 4`, read; Linux64 compiles).
- Frames are resolved per module against the symbols that module carries. The top frames inside the SDK and
  the RTL raise machinery are removed.
- A previously installed stack-trace library keeps providing `E.StackTrace` (the SDK chains to it); read.

## The symbols: what to produce

The Delphi compiler keeps names and lines out of the exe. They come from the linker's map file.

| Map file setting (`-G?`) | Frames read as | Run |
|---|---|---|
| Detailed (`-GD`), debug info on | `p3.TMainForm.Level3 (line 29)` | yes |
| Detailed, debug info off (`-$D- -$L- -$Y-`) | `p3.TMainForm.Level3` (no line) | yes |
| Publics (`-GP`) | `p3.TMainForm.Level3` (no line) | yes |
| Segments only (`-GS`) | module + offset, tool injects an empty table | matrix |
| None | `p3.exe!__dbk_fcall_wrapper+0x2B8EAA`, `ntdll.dll+0x600`: offsets, plus the nearest PE export name, which is not the real function | yes (Win32, Win64) |

Set it in the IDE: **Project > Options > Building > Delphi Compiler > Linking > Map file = Detailed**, for the
configuration and platform you ship. The command line says the same: `dcc32 -GD`, or
`msbuild /p:DCC_MapFile=3` (that text comes from the CLI's own advice, not run).

**Stack frames (`{$W+}`) matter on Win32.** The command-line compiler default is off; the IDE Debug
configuration turns it on, Release does not. Without it the trace silently loses frames (run: `Level2` and
`Tick` vanished, `Level3` and the timer frames stayed). `-$W+`, `msbuild /p:DCC_GenerateStackFrames=true`, or
`{$STACKFRAMES ON}` at the top of a unit. Win64 does not need it (run: full trace without it).
Precompiled RTL/VCL units are built without frames, so a Win32 trace usually ends at `USER32.dll!...`
inside the message loop, while a Win64 one runs up to `p3.p3 (line 70)` and `RtlUserThreadStart` (run).

Line numbers differ by one between Win32 and Win64 for the same call site (`Level2 (line 33)` vs `(line 34)`,
run): do not compare them across platforms.

## Where the symbols live (`symbol_source` on the event)

The SDK looks in this order, per module:

1. **`embedded`** - an `.ewmap` PE section (written by `ExeWatchMapCLI` or the IDE), then an `EXEWATCH_MAP`
   RCDATA resource. Travels with the exe: works on the customer's machine. Run on Win32 and Win64.
2. **`map_file`** - `MyApp.map` beside the exe. Works only where the file sits: fine on the developer's
   machine, raw offsets at the customer. Run.
3. **`none`** - nothing found. `unsupported_map_format` means the exe was linked by a newer tool than the
   SDK (update the SDK); `corrupt_map` means the section is damaged.

Events with a trace carry `symbol_source`; an Error/Fatal whose trace came out empty carries
`no_stacktrace_reason` instead: `1` capture unavailable (Win64), `2` the host module has no usable symbols,
`3` the capture returned no frames, `4` platform without trace support.

## Linking the map into the exe: ExeWatchMapCLI

```
ExeWatchMapCLI <binary> [<binary>.map] [--delete-map]
```

Installed by the RAD Studio setup to `<install>\bin\ExeWatchMapCLI.exe` (`%EXEWATCH_SDK%` is
`<install>\sdk`); also installable alone on a build machine (the setup script documents `/IDES=none`).
Run it after every build, on the exe or DLL you ship, **before Authenticode signing** (the section breaks an
existing signature). Run on Win32 and Win64 with the installed tool and the repository copy.

- Without a map argument it uses the `.map` beside the binary. `--delete-map` removes it after success.
  `/delete-map` also works in cmd; under Git Bash use `--delete-map` (the shell rewrites `/delete-map` into a
  path, run).
- First stdout line, for scripts: `RESULT=INJECTED symbols=<n> pe=<file>` or `RESULT=FAILED code=<n>
  reason=<text>`. Exit codes: 0 ok, 1 usage, 2 binary or map missing, 3 map empty, 4 write failure, 5 injected
  but the map could not be deleted (treated as 0), 6 not a PE, 7 no header room (nothing written; the SDK then
  falls back to the `.map` beside the exe).
- Then lines `WHAT`, `WHY`, `EXPECT`, `WARN`, `NOTE`, `IMPROVE`: read them, they name the exact setting to
  change (run: it asked for stack frames on a Win32 build).
- Re-running is idempotent. A project built with Map file = None makes it fail with exit 2 (run).
- The program must actually use the SDK for the trace to be taken; the tool warns if it does not.

Example, Win32 (run):

```
dcc32 -GD -$W+ -$D+ -$L+ MyApp.dpr
ExeWatchMapCLI MyApp.exe --delete-map      ->  RESULT=INJECTED symbols=18807 pe=MyApp.exe
```

## The IDE menu (read from the IDE package source, not driven)

With the RAD Studio setup installed there is an **ExeWatch** entry in the main **Project** menu and in the
project manager context menu, with **Link map file**, **Enable ExeWatch Telemetry**, **Playground and
updates...** and **About ExeWatch...**.

- **Link map file** toggles a project option. While it is on, each build forces Map file = Detailed, Stack
  frames on and debug information on for the active configuration (C++ projects: a publics map), then links
  the map into the output. It says so in the Messages view; switching it off does not restore the settings.
- **Enable ExeWatch Telemetry** creates `ExeWatchConfig.pas` beside the project (an `EXEWATCH_API_KEY`
  constant to fill in, `StartExeWatch`, `SetExeWatchCustomer`, `FlushExeWatch`), adds it and the SDK units
  (`ExeWatchSDKv1`, plus `.VCL` or `.FMX`) to the project, and in the `.dpr` inserts
  `StartExeWatch('customer-name');` as the first statement and `FlushExeWatch;` after `Run`. The customer name
  is a placeholder to replace. It also turns the map link on. An existing `ExeWatchConfig.pas` is added, not
  overwritten.

## Other things that change what a trace says

- A frame in another module (a DLL, a package) resolves against that module's own symbols, never the host's;
  without them it prints `module+offset` or the export name (matrix, read).
- Runtime packages (`-LUrtl`): works, smaller map (matrix).
- You can supply your own resolved stack: `EW.Log(llError, Msg, Tag, LJson)` with `stack_trace` already in
  `LJson` (the SDK keeps a `stack_trace` it finds). A madExcept sample exists in the samples repository
  (`SpecificScenarios\madExceptIntegration`); not examined.
- Obfuscators and executable packers: not verified.
- A trace on an unrelated machine only resolves if the map matches **that build**. Rebuilding moves addresses:
  embed the map in the exe you ship, or archive every release's `.map`.
