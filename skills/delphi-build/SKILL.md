---
name: delphi-build
description: Use when building, compiling or verifying a Delphi project from the command line - finding the newest RAD Studio, rsvars.bat, msbuild on a .dproj, dcc32/dcc64 on a .dpr, Debug/Release, Win32/Win64, reading compiler errors and warnings, making a warning fail the build, CI builds and exit codes. Triggers on "build a Delphi project", "msbuild", "dcc32", "dcc64", "rsvars", "compile error", "compiler error", "E2003", "F2613", "MSB4057", "warnings as errors", "Win64 build", "command line build", "CI build", "does it compile".
---

# Building Delphi from the command line

For an agent that must compile to verify its own work. **Nothing here is recalled.** Every command,
switch, error code and default below was run on this machine against the Delphi 13 Florence tools
(`Studio\37.0`, compiler 37.0); where it was also run against 12 Athens (`Studio\23.0`, compiler 36.0) it
says so. A claim marked *not run* was read from a shipped file, not executed.

The test projects were small console programs with a hand-written `.dproj` modelled on Embarcadero's
own template (`ObjRepos\en\DelphiWin32\SDIApp\SDIAPP.dproj`) and on a real IDE-saved one from the
DelphiMVCFramework samples. No IDE was running.

---

## Critical rules

1. **Never call `msbuild` bare.** Run `scripts/build.bat`, or `call ...\bin\rsvars.bat` first. Without it
   `msbuild` is not on `PATH` (cmd answers 9009). With `PATH` fixed but `BDS` undefined, the `.dproj`'s
   guarded `Import` of `CodeGear.Delphi.Targets` is silently skipped and you get
   `error MSB4057: the target "Build" does not exist in the project` - it reads like a broken project; it
   is a missing environment.
2. **The property is `Config`, not `Configuration`.** `/p:Configuration=Release` is silently ignored and
   Debug is built (the compiler line still says `-DDEBUG`). Write `/p:Config=Release`.
3. **Pass `/p:Platform=` yourself.** The default (Win32 or Win64) is written in the `.dproj`, not in the
   targets: a real IDE-saved console sample defaults to **Win64**. A leaked `PLATFORM=x64` environment
   variable moves the output to `.\x64\Debug`; `rsvars.bat` blanks `PLATFORM`, which is one more reason to
   always run it.
4. **The exit code and the first error are the verdict.** msbuild exits 0 or 1; so does `dcc`. Warnings
   and hints do **not** fail a build: exit 0, exe produced. "It built" never means "no warnings".
5. **There is no warnings-as-errors switch.** Promote one warning at a time, by its **name**:
   `-W^NO_RETVAL` (dcc), `/p:DCC_NO_RETVAL=error` (msbuild), `{$WARN NO_RETVAL ERROR}` (source). The
   W-number forms (`-W+W1035`, `-W^W1035`) are rejected with `F1030 Invalid compiler directive`.
6. **`dcc` never creates a directory.** A missing `-E`/`-NU` folder is `F2039 Could not create output
   file`. msbuild creates its output folders itself.
7. **Win64 is `dcc64.exe`.** `dcc32` only targets Win32; there is no `dcc32` for Win64.
8. **A `/p:` value replaces the `.dproj`'s own value completely.** `/p:DCC_Define=FOO` on a project that
   has `DEBUG;$(DCC_Define)` yields `-DFOO` only: `DEBUG` is gone and `{$IFDEF DEBUG}` code vanishes.
9. **The Studio folder number is not the compiler version.** `16.0` -> compiler 29.0, `23.0` -> 36.0,
   `37.0` -> 37.0. Ask `dcc32 --version`.
10. **A green build proves the names and types resolve. Nothing else.** See *What a compile does not prove*.

---

## Which tool declares what

| Thing | Where | Note |
|-------|-------|------|
| `rsvars.bat` | `Studio\<n>.0\bin\` | sets `BDS`, `BDSINCLUDE`, `BDSCOMMONDIR`, `FrameworkDir`, `FrameworkVersion`, `LANGDIR`; prepends `bin`, `bin64`, `cmake` and the .NET dir to `PATH`; **blanks `PLATFORM` and `PlatformSDK`**. Sets no Config, no Platform, no library path |
| MSBuild | `C:\Windows\Microsoft.NET\Framework\v4.0.30319\MSBuild.exe` | 4.8, 32-bit, put on `PATH` by `rsvars.bat` (the 16.0 `rsvars.bat` points at .NET 3.5 - not run) |
| `dcc32.EXE` | `Studio\<n>.0\bin\` | Win32 target |
| `dcc64.exe` | `Studio\<n>.0\bin\` | Win64 target. `bin64\` holds 64-bit-host copies of both; `rsvars.bat` puts `bin` first |
| `dcc32.cfg`, `dcc64.cfg` | next to the compiler | only unit aliases and `-u<Studio>\lib\win32\release` (or `win64`); **no namespaces** |
| `CodeGear.Delphi.Targets` | `Studio\<n>.0\bin\` | the `.dproj` imports it through `$(BDS)`; `DefaultTargets="Make"` |
| `EnvOptions.proj` | `%APPDATA%\Embarcadero\BDS\<n>.0\` | the IDE's Library path; imported by msbuild, so command-line builds see the same third-party units |
| `Config`, `Platform`, `DCC_ExeOutput`, `DCC_DcuOutput` | the `.dproj` | defaults and output folders are the project's, not the toolchain's |

---

## Step 1 - pick the Studio

```
dir /b /ad "C:\Program Files (x86)\Embarcadero\Studio"          16.0  23.0  37.0
reg query "HKLM\SOFTWARE\WOW6432Node\Embarcadero\BDS\37.0" /v RootDir       (install path, if not the default)
"...\Studio\37.0\bin\dcc32.exe" --version
```

The newest install is the highest **numeric** folder (`37.0` beats `9.0` and `23.0`; do not sort as text).
`build.bat` does this. `DELPHI_BDS=23.0` forces one. A bare `dcc32` on `PATH` is whichever install comes
first - on a machine with several, never trust it; `rsvars.bat` puts the chosen one first.

If the user builds with a specific release, build with that one: a project that compiles on 13 can fail on
12 (see the `delphi` skill, *Establish the target*).

## Step 2 - build a `.dproj`

```
scripts\build.bat MyApp.dproj                       Debug, Win32, Build  (rebuild all units)
scripts\build.bat MyApp.dproj Release Win64
scripts\build.bat MyApp.dproj Debug Win32 Make      only changed units
scripts\build.bat MyApp.dproj Debug Win32 Clean
scripts\build.bat MyApp.dproj Debug Win32 Build "/p:DCC_NO_RETVAL=error"     extra msbuild args, each quoted
```

Run on 37.0 (with a leaked `PLATFORM=x64` in the environment) and on 23.0 (`DELPHI_BDS=23.0`). Exit code: msbuild's (0 built,
1 failed); 2 for a missing project, no Studio, or bad arguments. A failure looks like this (path trimmed):

```
build.bat: Studio 37.0, Broken.dproj, Config=Debug Platform=Win32 Target=Build
Broken.dpr(11): error E2010: Incompatible types: 'Integer' and 'string' [...Broken.dproj]
Broken.dpr(12): error E2003: Undeclared identifier: 'Undeclared' [...Broken.dproj]
build.bat: FAILED, exit code 1
```

`Build` passes `-B` to the compiler, `Make` passes `-M`, both with `--no-config -Q`. The default target
of a bare `msbuild X.dproj` is **Make**. `Clean` removes the exe, the `.dcu` files and the generated
`.res`, and leaves the empty folder behind. Details, the property table and the output folders:
`reference/msbuild.md`.

**Where is the exe?** In `DCC_ExeOutput` of the `.dproj` (`findstr DCC_ExeOutput X.dproj`). The IDE
default is `.\$(Platform)\$(Config)`; the DMVCFramework samples use `bin`. Do not guess.

## Step 3 - only a `.dpr`, or one quick check

No `.dproj` means no msbuild. Call the compiler directly:

```
rem after: call ...\Studio\37.0\bin\rsvars.bat
mkdir out out64 dcu dcu64
dcc32 -B -NSSystem;Winapi -Uthirdparty\src -Iinc -NUdcu -Eout MyApp.dpr
dcc64 -B -NSSystem;Winapi -Uthirdparty\src -Iinc -NUdcu64 -Eout64 MyApp.dpr
```

Three traps, all hit while testing: the output folders must exist; **namespaces are not in
`dcc32.cfg`**, so `uses SysUtils` needs `-NSSystem` (`F2613 Unit 'SysUtils' not found`); and the IDE's
Library path is **not** used, so third-party units need `-U` (a mistyped `-U` folder is only `Hint:
H2675 Directory not found`, exit 0, and the real failure comes later as `F1026`/`F2613`). Switch table, which files are written, the
`{$R *.res}` catch, `--no-config`: `reference/dcc.md`.

---

## The compile-fix-recompile loop

1. **Baseline first.** Before editing, build once and keep the output
   (`build.bat X.dproj > before.log 2>&1`). The warnings already there are not yours.
2. **Edit, then rebuild with `Build`.** Rebuild-all is cheap on a small project and cannot reuse a stale
   `.dcu`. (Whether `Make` can miss a change was not established; do not rely on it for the final check.)
3. **Read from the top and stop at the first `error`.** Letters: `F` fatal (compilation stopped, nothing
   after it matters), `E` error, `W` warning, `H` hint. One mistake cascades: a misplaced `uses`
   produced `E2029`, then `E2003` and `E2010` on lines that were fine, then `F2063 Could not compile used
   unit`. Fix the first error, rebuild, re-read.
4. **A `F1026 File not found` / `F2613 Unit ... not found` is the environment, not your code.** The unit is
   not on the search path. Find the folder and add it (`DCC_UnitSearchPath`, or `-U`). Never delete the
   `uses` entry to get a green build.
5. **Do not hide warnings to finish.** No `{$WARN ... OFF}`, `-W-`, `-H-` or `DCC_Warnings=false` to turn the
   output green. Fix the cause. If suppression is right, do it narrowly with a reason
   (see the `delphi-code-smells` skill, its static-analysis reference). Diff the new output against `before.log`.
6. **Promote the dangerous ones.** `W1035` (function result undefined), `W1036` (use before assignment) and
   `W1037` (loop variable after the loop) are real bugs: build once with them as errors
   (`reference/warnings.md`).
7. **Stop when** the exit code is 0 **and** no warning or hint appeared that is not in the baseline. Stop and
   report, rather than looping, when the same error survives three different fixes or the error is outside
   your change (a missing third-party library, an install problem).
8. **Report three different things:** it compiles; it compiles clean; I ran it and saw it work.

## For CI

Gate on the exit code, never on text: msbuild's own words are localised (here, `Avvisi` and `Errori`
instead of Warnings and Errors), while the compiler lines (`error E2010:`, `warning W1035:`) were English.

```
msbuild X.dproj /t:Build /p:Config=Release /p:Platform=Win64 /v:m /nologo /fl "/flp:logfile=build.log;verbosity=normal"
```

`/v:m` prints one line per diagnostic and no totals. The log file written by `/fl` carries the warning and
error counts. `/clp:ErrorsOnly` quiets the console. Always `Clean` or use `Build` on a CI agent; never
reuse a `.dcu` folder from a previous run.

## What a compile does not prove

It proves that identifiers resolve, types match and the linker found its pieces. It does **not** prove that
the code does the right thing, that nothing leaks (`Result := ToFree(x)` compiles and double-frees),
that an interface is released, that a query returns rows, or that the exe starts. If the claim is about
behaviour, **run the program** and look: run the exe and read its exit code and output, set
`ReportMemoryLeaksOnShutdown := True` in a debug build, run the test project. Leak hunting:
`delphi-code-smells`. Tests of a DMVC API: `dmvcframework-testing`.

---

## Reference files

| File | Open it when |
|------|--------------|
| `reference/msbuild.md` | a `.dproj` build misbehaves; you need the targets, the property table, the output folders, how `/p:` overrides work, which `DCC_` properties exist (and that `DCC_IncludePath` does not), or what msbuild really passes to the compiler |
| `reference/dcc.md` | there is no `.dproj`, or you want the exact compiler switches, the files a compile writes, `--no-config`, `.res` handling, or the full list of failures |
| `reference/warnings.md` | reading an `F/E/W/H` line, making one warning an error, the `{$WARN}` and `DCC_<NAME>` forms, or deciding whether warnings should break the build |
| `scripts/build.bat` | always; the working script (about 50 lines, no delayed expansion) |
