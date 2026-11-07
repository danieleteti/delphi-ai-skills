# Runner, exit codes, loggers, leak detection, CI

Verified with `dcc32` / `dcc64` 37.0 and 23.0. "12" = the 23.0 tree (Delphi 12 Athens), "13" = 37.0.

## 1. Project layout

```
MyApp\
  src\            units under test (also used by the app)
  tests\
    MyAppTests.dpr          console project: runner setup only (SKILL.md skeleton)
    Acme.Foo.Tests.pas      one test unit per unit under test
  golden\                   golden-master files (reference/characterization.md)
```

- The test project is a **separate console program**. It `uses` the units under test directly. Do not put
  a test in the application's own `.dpr`.
- Test units go into the `.dpr` `uses` clause (or are reached through it). `{$STRONGLINKTYPES ON}` keeps their
  classes from being dropped by the linker.
- Keep GUI units and `Vcl.*` out of the code under test. A console test project cannot create forms
  (separate the logic from the form: `reference/testable-code.md`).
- The DUnitX precompiled units are in `lib\win32\release` and `lib\win64\release`, which are in the IDE
  and `dcc` search path by default. The sources (`source\DUnitX`) are **not** on the path.

Build and run from a shell, with the stock compiler configuration (verified; `dcc64.cfg` supplies the
library path). The `-NU` directory must already exist, or the compiler stops with `F2039`:

```
mkdir obj
"C:\Program Files (x86)\Embarcadero\Studio\37.0\bin\dcc64.exe" -B -E. -NUobj MyAppTests.dpr
MyAppTests.exe -cm:Quiet -xml:C:\build\results.xml
```

The 32-bit compiler is `dcc32.EXE` in the same folder (upper-case extension in `37.0\bin`).

For `msbuild` builds see the `delphi-build` skill.

## 2. Exit codes

| Situation | Exit code |
|-----------|-----------|
| all passed, and the `.dpr` did not touch `ExitCode` | 0 |
| tests failed, and the `.dpr` did not touch `ExitCode` | **0** (verified: 4 failures, exit 0) |
| tests failed, `.dpr` has `if not results.AllPassed then System.ExitCode := EXIT_ERRORS` | 1 |
| unknown command line option | 100 (`EXIT_OPTIONS_ERROR`, set by `TDUnitX.CheckCommandLine`, which then raises `ECommandLineError`) |
| `-h` | 0, usage printed, `Halt(EXIT_OK)` |
| no fixtures found (`ENoTestsRegistered`) caught by a handler that only prints | **0** |
| `-r:` / `-i:` matching nothing | **0**, `Tests Found: 0` |

`EXIT_OK = 0`, `EXIT_ERRORS = 1`, `EXIT_OPTIONS_ERROR = 100` are in `DUnitX.TestFramework`.
`AllPassed` is False for any result that is not Pass or Ignored, so **Failure, Error and MemoryLeak all
count**. `ITestRunner.Execute` never sets `ExitCode` itself.

The DUnitX test project shipped in the source tree (`Tests\DUnitXTest.dpr`) sets `EXIT_ERRORS` only under
`{$IFDEF CI}`, and its `except` branch prints the exception and exits 0. Do not copy that handler.

`-exit:` (`--exitbehavior`) takes `Continue` (default) or `Pause`. It controls only whether the program
waits for Enter at the end. Under CI leave it at `Continue`; `Pause` blocks the job on `Readln`.

Guard against an empty run, the silent way to a green build:

```delphi
if (not results.AllPassed) or (results.TestCount = 0) then
  System.ExitCode := EXIT_ERRORS;
```

If a CI job runs a deliberate subset (`-r:`), an empty subset is then an error, which is what you want.

## 3. Command line

Options are parsed by `TDUnitX.CheckCommandLine`. **A project that never calls it ignores every option**
(verified: `-r:` ran all the tests). Form: `-name:value` or `--name:value`; the short forms are in the table.

| Option | Short | Meaning |
|--------|-------|---------|
| `--run:A,B` | `-r:` | names of tests or fixtures to run, e.g. `-r:Acme.Basics.Tests.TStringListTests` |
| `--include:cat` | `-i:` | categories to include (grammar in `reference/attributes.md`) |
| `--exclude:cat` | `-e:` | categories to exclude |
| `--xmlfile:path` | `-xml:` | file for the XML loggers. **Absolute path only** (below) |
| `--consolemode:Off\|Quiet\|Verbose` | `-cm:` | Verbose is the default. `Quiet` prints dots and the summary |
| `--loglevel:Information\|Warning\|Error` | `-l:` | minimum level of `Log` messages kept |
| `--exitbehavior:Continue\|Pause` | `-exit:` | see above |
| `--hidebanner` | `-b` | hide the licence banner |
| `--dontshowignored` | `-dsi` | ignored tests are not run **and not reported** |
| `--runlist:file` | `-rl:` | file listing tests to run (format not checked) |
| `--options:file` | `-opt:` | options from a file (format not checked) |
| `-h` | `-?` | usage |

The options only fill `TDUnitX.Options`; your `.dpr` reads them (`ConsoleMode`, `XMLOutputFile`,
`ExitBehavior`). Filters are applied by the runner through `TDUnitX.Filter`, set by `CheckCommandLine`.

**`-xml:` and relative paths.** A relative path (`a.xml`, `.\a.xml`, `out\a.xml`) raised
`EInOutError: Unable to create directory` (verified on 13: the logger calls `ForceDirectories` on the
directory part). Pass an absolute path. With no `-xml:` the file is `dunitx-results.xml` next to the exe.
A bare second argument is also taken as the XML path (the unnamed option).

## 4. Loggers

| Logger | Unit | Notes |
|--------|------|-------|
| `TDUnitXConsoleLogger.Create(quietMode: Boolean = False)` | `DUnitX.Loggers.Console` | colours need the platform console unit; this unit already uses `DUnitX.AutoDetect.Console` |
| `TDUnitXXMLNUnitFileLogger.Create(AFilename = '')` | `DUnitX.Loggers.XML.NUnit` | NUnit-style XML (`<test-results ...>`); ran and produced the file |
| `TDUnitXXMLJUnitFileLogger.Create(AFilename = '')` | `DUnitX.Loggers.XML.JUnit` | JUnit-style XML (`<testsuites ...>`); ran and produced the file |
| `TDUnitXTextFileLogger` | `DUnitX.Loggers.Text` | **do not use**: every method, the constructor included, raises `ENotImplemented` |
| `DUnitX.Loggers.XML.xUnit` | | an empty unit: it declares nothing |
| GUI logger | `DUnitX.Loggers.GUI.VCL` | VCL runner, not exercised here |

`AddLogger` can be called several times: console plus one XML file is the usual CI pair. Which report
format a given CI server accepts was not verified here; the DUnitX `README.md` says the NUnit output suits
ContinuaCI and the JUnit output GitLab CI.

12 and 13 differ in the NUnit file (both ran): the root `time` attribute is a duration in 12 (`0.210`) and a
time of day in 13 (`12:44:16`). Do not parse it as a duration on 13.

## 5. Per-test leak detection

Off by default. The registered monitor is `TDUnitXDefaultMemoryLeakMonitor`, which returns 0 for every
measurement, so a leaking test **passes** (verified: `Tests Leaked : 0`). To turn it on, all three:

1. add `DUnitX.MemoryLeakMonitor.FastMM4` to the test project `uses`;
2. define `USE_FASTMM4_LEAK_MONITOR` in the project (Conditional defines, or `dcc -D`). It is commented out in
   `DUnitX.MemoryLeaks.inc`, which `DUnitX.inc` includes;
3. put `...\Studio\<n>.0\source\DUnitX` in the project's unit search path, so the monitor unit is compiled
   **with your define**. The precompiled `lib\win32\release\DUnitX.MemoryLeakMonitor.FastMM4.dcu` was built
   without it: with only the library path and the define the leak was **not** detected (verified on Win32,
   12 and 13). `lib\win64\release` has no `...FastMM4.dcu` at all (`F2613 Unit ... not found`), so on Win64 step 3
   is not optional.

Build the project fully after changing the define (Project > Build, or `dcc -B`). When compiling from the
13 source the compiler prints `W1002 Symbol 'GetMemoryManagerState' is specific to a platform` inside the
DUnitX unit; ignore it. A FastMM5 variant exists (`DUnitX.MemoryLeakMonitor.FastMM5`, it expects `FastMM5.pas`
as the first unit of the `.dpr`); `FastMM5.pas` is not in the installed tree, so it was not run.
`delphi-code-smells` `reference/leaks.md` section 4 describes another route: registering your own monitor.

What the runner does with it: it measures allocated bytes around `[Setup]`, the test and `[TearDown]`
and compares them (`CheckMemoryAllocations` in `DUnitX.TestRunner.pas`):

| Where the bytes leaked | Message |
|------------------------|---------|
| the test only | `216 bytes were leaked in the test method` |
| setup / teardown only | `N bytes were leaked in the setup/teardown methods` |
| both | `N bytes were leaked in the setup/test/teardown methods` |

The result type is `TTestResultType.MemoryLeak`: `IRunResults.MemoryLeakCount`, a `Tests Leaked` line, a
`Tests With Memory Leak` section, no Pass, and `AllPassed` = False, so the exit code in the skeleton is 1.
`[IgnoreMemoryLeaks]` on the test skips the check. The byte counts were 216 (Win64) and 124 (Win32) for one
leaked `TStringList`.

False positives seen (so a red leak is not always your bug):

| Test body | Reported |
|-----------|----------|
| create and free a `TStringList`, end with `Assert.IsTrue(True)` | clean |
| the same, end with `Assert.Pass` | **56 bytes leaked** (Win32: 28). End with a real assertion |
| first use of `TRttiContext.GetType` in the run | 104 bytes in whichever test runs first; the second use is clean |
| `Log('text')` in a test | 240 bytes (the runner keeps the message). The shipped `DUnitX.MemoryLeaks.inc` warns about this |
| a fixture field assigned in the test and never freed | reported **in that test**, although the fixture still holds the pointer |

Objects created in the fixture constructor and freed in the destructor sit outside the per-test
measurement: use `ReportMemoryLeaksOnShutdown := True` for those (`delphi-code-smells`).

## 6. Wiring to CI

The only contract is the process exit code. In `cmd`:

```bat
MyAppTests.exe -cm:Quiet -xml:C:\build\results.xml
if errorlevel 1 exit /b 1
```

Verified: exit 1 on a failing run, `%ERRORLEVEL%` read as 1. PowerShell: `& .\MyAppTests.exe -cm:Quiet`
then `exit $LASTEXITCODE` (verified: `$LASTEXITCODE` = 1).

Checklist for a CI job:

- build both Win32 and Win64 if you ship both: behaviour differs (`[MaxTime]`, `NativeInt`, leak sizes);
- pass `-cm:Quiet` and an absolute `-xml:`; never `-exit:Pause`;
- fail the job on a non-zero exit code, then publish the XML as the report;
- treat `Tests Found: 0` as failure (section 2);
- compile with warnings visible. A test attribute that the compiler does not know (`W1074 Unknown custom
  attribute`) is a test that silently does not exist.

## 7. 12 Athens vs 13 Florence

| Item | 12 (23.0) | 13 (37.0) |
|------|-----------|-----------|
| `[AutoNameTestCase]` | not declared | available |
| `[SetupFixture]` raising | the fixture's tests still run, `[TearDownFixture]` runs | tests skipped, teardown not run |
| `NoDiff` window | 10 characters from the difference | 5 before, 5 after |
| `[MaxTime]` on Win64 | timed out correctly in the probe | Access violation (Error) in the probe |
| NUnit `time` attribute | duration | time of day |
| service container class (only for a hand-written leak monitor) | `TDUnitXIoC`, unit `DUnitX.IoC` | `TDUnitXServiceLocator`, unit `DUnitX.ServiceLocator` |
| `Assert.AreEqual(1, lDict.Count)` on Win64 | `E2532` | `E2532` (same; `Count` is `NativeInt`). Cast: `Integer(lDict.Count)` |

The last row bites every Win64 build: collection `Count` is `NativeInt` from 12 on (see the `delphi`
skill), and the generic `AreEqual<T>` cannot infer `T` from an `Integer` literal and a `NativeInt`.
Verified on `TDictionary<K,V>.Count`.
