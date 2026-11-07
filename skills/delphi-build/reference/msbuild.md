# msbuild on a `.dproj`

Everything here was run with `MSBuild.exe` 4.8 from `rsvars.bat`, on a hand-written `.dproj` that follows
Embarcadero's `SDIAPP.dproj` template, with Delphi 13 (`37.0`). 12 Athens (`23.0`) was run for the build
itself and for the warning-as-error property; its `rsvars.bat` is identical apart from the version number.
Projects saved by a real IDE carry many more property groups (one per platform) but the same mechanism.

## Contents

1. The command and what it turns into
2. Config and Platform: where the defaults live
3. Targets: Make, Build, Clean
4. Output folders and the generated `.res`
5. `/p:` overrides the project
6. Which `DCC_` properties exist
7. Where the unit search path comes from
8. Seeing what msbuild really runs
9. Failures, by symptom

---

## 1. The command

```
call "C:\Program Files (x86)\Embarcadero\Studio\37.0\bin\rsvars.bat"
msbuild MyApp.dproj /t:Build /p:Config=Release /p:Platform=Win64 /v:m /nologo
```

For Win64 release this runs `Studio\37.0\bin\dcc64.exe`, not `bin64`:

```
dcc64.exe -$D0 --no-config -B -Q -TX.exe -DRELEASE -E.\Win64\Release -NU.\Win64\Release -NSSystem;Xml;Data;Datasnap;Web;Soap; ... MyApp.dpr
```

(`-$D0` came from the project's `DCC_DebugInformation=0` in its Release group; a template-style Release
group also produced `-$L- -$Y-`.)

Always present: `--no-config` (so `dcc32.cfg` is **not** read; msbuild supplies the RTL path itself) and `-Q`.
Win32 runs `dcc32.exe`. Both exe and `.dcu` output are relative to the `.dproj`, not to the current
directory.

## 2. Config and Platform

| Fact | Evidence |
|------|----------|
| Property names are `Config` and `Platform`. | `/p:Configuration=Release` -> compiler got `-DDEBUG -E.\Win32\Debug`: ignored. `/p:Config=Release` -> `-DRELEASE -E.\Win32\Release`. |
| Their defaults are written in the `.dproj`: `<Config Condition="'$(Config)'==''">Debug</Config>`, same for `Platform`. | Template: Debug/Win32. A real IDE-saved DMVC sample: Debug/**Win64**, with Win32 marked `False` in its platform list. |
| Configuration names are whatever the project defines. | `findstr /c:"BuildConfiguration Include" X.dproj` lists them (`Base`, `Debug`, `Release` in the three projects seen). `Base` is a parent, not a target to build. |
| Release differs from Debug only by what the project says. | The template's Release added `-$D0 -$L- -$Y-` and `-DRELEASE`; Debug added `-DDEBUG`. A hand-trimmed project may differ - read the `.dproj`, do not assume. |
| A stray `PLATFORM` environment variable becomes `$(Platform)`. | `PLATFORM=x64` without `rsvars.bat` -> exe in `.\x64\Debug`. After `call rsvars.bat` -> `.\Win32\Debug`. |

## 3. Targets

`DefaultTargets="Make"` in `CodeGear.Delphi.Targets` (line 16 in 37.0).

| Command | Compiler flag | Effect |
|---------|---------------|--------|
| `msbuild X.dproj` | `-M` | Make: units whose source changed |
| `/t:Make` | `-M` | same |
| `/t:Build` | `-B` | rebuild every unit |
| `/t:Clean` | - | deletes the exe, the `.dcu` files and the generated `.res`; exit 0; the empty `Win32\Debug` folder remains |

`Build` is what a verification run wants. After editing one unit, `Make` and `Build` both produced a correct
exe in every test; whether `Make` can miss a change in some dependency chain was not established.

## 4. Output folders and the generated `.res`

- msbuild **creates** `.\Win32\Debug` and its siblings. `dcc` does not.
- `DCC_ExeOutput` and `DCC_DcuOutput` are set **by the project**. The IDE default is
  `.\$(Platform)\$(Config)` for both; the DMVC samples set `DCC_ExeOutput` to `bin`. Read them:
  `findstr DCC_ExeOutput X.dproj`.
- If the `.dpr` has `{$R *.res}`, msbuild writes `X.res` **into the project folder** (not into the output
  folder) and `Clean` removes it. A direct `dcc32` run does not create it (`reference/dcc.md`).

## 5. `/p:` overrides the project

A `/p:` value is a global property. It wins over the `.dproj`'s own assignment **completely**, including
the `X;$(X)` accumulation idiom.

| Command | Compiler got |
|---------|--------------|
| (Debug config has `<DCC_Define>DEBUG;$(DCC_Define)</DCC_Define>`) | `-DDEBUG` |
| `/p:DCC_Define=FOO` | `-DFOO`. `DEBUG` is gone; the built exe no longer sees `{$IFDEF DEBUG}`. |
| `"/p:DCC_Define=ZED%3BYEP"` | two defines, built. A bare `;` fails: msbuild reads `;` as a property separator (`MSB1006: invalid property`, option `YEP`). |

Two layers of quoting, both seen to fail:

- **Through a `.bat`** (`build.bat` forwards `%5`..`%9`), cmd splits an argument at `=`. Unquoted
  `/p:DCC_Define=ZED` reached msbuild as `/p:DCC_Define` plus `ZED`, and msbuild answered `MSB1008: only one
  project can be specified`, option `ZED`. Write `"/p:DCC_Define=ZED"`.
- **msbuild's own `;`**: escape it as `%3B`. Inside a `.bat` file, write `%%3B` (a single `%3` is the third
  batch parameter).

## 6. Which `DCC_` properties exist

The list below comes from the properties `CodeGear.Delphi.Targets` reads (a grep for `$(DCC_...)`) plus the
ones run. A property that is **not** in the targets can still be read by the compiler task, so for any name
not below, run it and look at the command line (section 8).

| Property | Becomes | Run? |
|----------|---------|------|
| `DCC_Define` | `-D...` | yes |
| `DCC_UnitSearchPath` | `-U`, `-I`, `-O` and `-R` all at once (see section 7) | yes |
| `DCC_ExeOutput`, `DCC_DcuOutput` | `-E`, `-NU` | yes |
| `DCC_Warnings` | `true`/`false` only: `false` -> `-W-` | yes |
| `DCC_Hints` | `false` hides hints | yes |
| `DCC_<NAME>` (e.g. `DCC_NO_RETVAL`) | `error` -> `-W^NAME`; `false` -> `-W-NAME`; `true` emits nothing | yes |
| `DCC_AdditionalSwitches` | appended at the end of the command line (`-DEXTRA` was seen) | yes |
| `DCC_BuildAllUnits`, `DCC_MakeModifiedUnits` | set by the `Build` / `Make` targets | read from targets |
| `DCC_ResourcePath`, `DCC_ObjPath` | resource and object paths | read from targets |
| **`DCC_IncludePath`** | **does not exist.** | yes: ignored |

`DCC_IncludePath` is the plausible name that costs an afternoon. Put in a `.dproj`, it produced no `-I`
entry and the build failed `F1026: File not found: 'ver.inc'`. The same folder in `DCC_UnitSearchPath`
built. The targets set `IncludePath = UnitSearchPath` (line 149), so one list feeds all four switches.

`DCC_Warnings=NO_RETVAL` is a mistake the compiler cannot name: the value is pasted raw and the build
fails with `error F1026: File not found: 'NO_RETVAL.dpr'` reported from `CodeGear.Delphi.Targets`.

## 7. Where the unit search path comes from

`UnitSearchPath = $(DCC_UnitSearchPath);$(DelphiLibraryPath)` (targets, line 132). `DelphiLibraryPath`
comes from `%APPDATA%\Embarcadero\BDS\<n>.0\EnvOptions.proj`, which the IDE writes from *Tools > Options >
Language > Delphi > Library*. `CodeGear.Common.Targets` imports it unless `ImportEnvOptions=false`.

Consequences, the first one seen on this machine, the rest read from the targets (*not run*):

- A command-line msbuild build sees the **same third-party library paths as the IDE**: the `-U` list in the
  compiler line held every library registered in the IDE. That is why a project builds here and may not on a
  CI agent.
- On a machine where the IDE never ran there is no `EnvOptions.proj`. The targets fall back to
  `$(BDSLIB)\$(PLATFORM)\$(CONFIG)` and print a warning, `Expected configuration file missing`. Third-party
  units must then be in `DCC_UnitSearchPath` (committed in the `.dproj`, or `/p:`).
- A CI build that must not depend on the developer's IDE can pass `/p:ImportEnvOptions=false` and list its
  paths itself.

## 8. Seeing what msbuild really runs

```
msbuild X.dproj /t:Build /v:n /nologo > build.txt
findstr /c:"dcc32.exe" build.txt
```

The line is **very long** on a machine with many registered libraries (the library list appears under
`-I`, `-O`, `-R` and `-U`). Read the head of the line and search it for the switch you care about, never
paste all of it. This is the way to settle "did my property reach the compiler" for any property.

## 9. Failures, by symptom

| You see | It means |
|---------|----------|
| `'msbuild' is not recognized` / exit 9009 | `rsvars.bat` not called |
| `error MSB4057: the target "Build" does not exist in the project` | `BDS` is not set, so the targets import was skipped. Call `rsvars.bat` |
| `error MSB1008: only one project can be specified` | a `/p:` argument with `=` was split by cmd; quote it (section 5) |
| exe in the wrong folder, `x64\Debug` | stray `PLATFORM` variable; call `rsvars.bat` |
| Debug built when you asked for Release | `Configuration=` instead of `Config=` |
| `error F1026: File not found: 'x.inc'` | include folder missing from `DCC_UnitSearchPath` |
| `error F1026: File not found: 'NAME.dpr'` | a `DCC_` property value was meant as a name, not a switch (section 6) |
| `error F2613: Unit 'X' not found` | not on the unit search path; see section 7 |
| build exits 0 and the exe is old | you looked in the wrong output folder (section 4) |
