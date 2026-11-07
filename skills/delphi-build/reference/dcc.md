# Calling `dcc32` / `dcc64` directly

Use it when there is only a `.dpr`, for a fast check of one program, or to see exactly what the compiler
says without msbuild in between. If a `.dproj` exists, prefer `scripts/build.bat`: msbuild already knows the
namespaces, the library paths and the output folders.

Every line below was run with `Studio\37.0\bin\dcc32.EXE` / `dcc64.exe` (13 Florence). The warning switches
were also run on 12 Athens (`23.0`) with identical results.

## Contents

1. Minimal working command
2. The switches that matter
3. Which files are written, and where
4. What `dcc32.cfg` gives you, and `--no-config`
5. `{$R *.res}`
6. Win32 and Win64: which executable
7. Exit codes
8. Failures, by message

---

## 1. Minimal working command

```
call "C:\Program Files (x86)\Embarcadero\Studio\37.0\bin\rsvars.bat"
mkdir out out64 dcu dcu64
dcc32 -B -NSSystem -Iinc -Usrc -NUdcu -Eout Two.dpr
dcc64 -B -NSSystem -Iinc -Usrc -NUdcu64 -Eout64 Two.dpr
```

`rsvars.bat` is for `PATH` only: a bare `dcc32` otherwise resolves to whichever Studio comes first on a
machine with several. Or call the compiler by full path: `"...\Studio\37.0\bin\dcc32.EXE"` (that is the
real spelling of the file; Windows does not care).

Run it **from the project folder**: a `uses Foo in 'src\Foo.pas'` clause is resolved against the current
directory, not against the `.dpr`. From another folder, `dcc32 ..\Two.dpr` failed with
`F1026 File not found: 'src\UnitA.pas'`.

## 2. The switches that matter

Copied from `dcc32` with no arguments (37.0). `<paths>` are separated by `;`.

| Switch | Meaning | Seen |
|--------|---------|------|
| `-B` | build all units (rebuild everything) | writes every `.dcu` |
| `-M` | make: recompile modified units | writes `.dcu` |
| *(neither)* | compile what is needed, **write no `.dcu`** | `UnitA.dcu` not written |
| `-Q` | "quiet compile" | no visible difference in any run: the banner and the `N lines` summary still print |
| `-E<path>` | exe/dll output folder | default: next to the `.dpr` |
| `-NU<path>` | `.dcu` output folder | default: next to each source. `-N0<path>` is still accepted as an alias |
| `-NS<list>` | namespace search path | **required** for `SysUtils`-style short names |
| `-U<paths>` | unit search path | |
| `-I<paths>` | include folders (`{$I x.inc}`) | |
| `-O<paths>` / `-R<paths>` | object / resource folders | |
| `-D<syms>` | define conditionals | `-DDEBUG` |
| `-W[+\|-\|^][NAME]` | warnings: on, off, **error**; with a name, one warning | see `reference/warnings.md` |
| `-H` / `-H-` | hints on / off | hints are on by default |
| `-CC` / `-CG` | console / GUI target | |
| `-V` | debug information in the exe | |
| `-GD` | detailed map file | |
| `-$<letter><+\|->` | compiler switch, e.g. `-$R+` range checks, `-$Q+` overflow checks, `-$D0` | |
| `--no-config` | do not read `dcc32.cfg` | see section 4 |
| `--version` | `dcc (Embarcadero Delphi for Windows) 37.0` | |

Ask the compiler itself for anything else: `dcc32 --help` lists every switch for the installed version.
`-U`, `-I`, `-O` and `-R` take the same kind of list; msbuild sets all four from one property.

A **nonexistent** folder in `-U` is only `Hint: H2675 Directory not found: thirdparty\src` with exit 0. A
typo in a search path shows up later as `F1026` or `F2613`.

## 3. Which files are written, and where

Test: `Two.dpr` uses its own `src\UnitA.pas`; `-NSSystem -Iinc`, run from the project folder, outputs
deleted before each run.

| Command | Result |
|---------|--------|
| `dcc32 -NSSystem -Iinc Two.dpr` | `Two.exe` next to `Two.dpr`; **no** `UnitA.dcu` |
| same with `-M` or with `-B` | `Two.exe` and `src\UnitA.dcu` (next to the source) |
| same with `-Q` | same as the first row |
| `-B -NUdcu -Eout` (both folders exist) | `dcu\UnitA.dcu`, `out\Two.exe` |
| `-NUdcu -Eout` with the folders missing | `Fatal: F2039 Could not create output file 'out\Two.exe'`, exit 1 |

`dcc` never creates `-E` or `-NU` folders. A missing one is `F2039`, naming the file it could not write.
After a rebuild with `-B` the `.dcu` files in the `-NU` folder are the product to throw away; keep that
folder out of version control and **empty it on a CI agent**.

A plain run after editing one unit recompiled that unit. Whether a plain or `-M` run can ever reuse a stale
`.dcu` was not established: for the compile that decides "it works", use `-B`.

## 4. What `dcc32.cfg` gives you, and `--no-config`

`bin\dcc32.cfg` contains only unit aliases (`-aWinTypes=Windows;...`) and
`-u"...\Studio\37.0\lib\win32\release"` (`dcc64.cfg`: `lib\win64\release`). It has **no namespaces**:

```
dcc32 -Iinc Two.dpr           ->  Two.dpr(5) Fatal: F2613 Unit 'SysUtils' not found.
dcc32 -NSSystem -Iinc Two.dpr ->  compiles
dcc32 --no-config Three.dpr   ->  Three.dpr(1) Fatal: F1027 Unit not found: 'System' or binary equivalents (.dcu)
```

So `-NS` is yours to supply: `-NSSystem` for a console program using `System.*`. For a VCL program, copy the
exact list msbuild uses (`reference/msbuild.md`, section 8) rather than writing it from memory. With
`--no-config` you must also pass the RTL folder (`-U"%BDS%\lib\win32\release"`); msbuild does exactly that.

The IDE's *Library path* (third-party packages, `EnvOptions.proj`) is **not** read by `dcc`. Every
third-party unit needs its folder in `-U`.

## 5. `{$R *.res}`

A `.dpr` containing `{$R *.res}` needs `X.res` **next to the `.dpr`** (the file the IDE or msbuild writes).
Compiling directly without it:

```
Error: E1026 File not found: 'Hello.res'            (exit 1)
```

Run `msbuild X.dproj` once with a `.dproj`: it creates `Hello.res` in the project folder, and a following
direct `dcc32 -NSSystem Hello.dpr` then compiled and produced `Hello.exe`. With a `.dpr` and no `.dproj` at
all, either the `.res` is already in the repository (then it works), or the `{$R *.res}` line has to be
dealt with by the user. A malformed `.res` is `E2161 RLINK32: Error reading file`.

## 6. Win32 and Win64: which executable

| Target | Compiler | Config next to it |
|--------|----------|-------------------|
| Win32 | `bin\dcc32.EXE` (banner "for Win32") | `dcc32.cfg` |
| Win64 | `bin\dcc64.exe` (banner "for Win64") | `dcc64.cfg` |

There is **no** `dcc32` that targets Win64: choosing the platform means choosing the executable. Use
separate `-NU` and `-E` folders per platform (`dcu` / `dcu64`). A `.dcu` is platform-specific, and `dcc64`
pointed at a folder holding Win32 `.dcu` files stops with:

```
Two.dpr(5) Fatal: F2048 Bad unit format: 'dcu\UnitA.dcu' - Expected version: 37.0, Windows Unicode(x64) Found version: 37.0, Windows Unicode(x86)
```

(msbuild avoids this with `.\$(Platform)\$(Config)`.) `Studio\37.0\bin64\` holds 64-bit-hosted copies of both
compilers (PE machine type 0x8664, against 0x14C in `bin`). `bin64\dcc64.exe` compiled a Win64 program and
`bin64\dcc32.exe --version` still says "for Win32": same targets, different host. `rsvars.bat` puts `bin`
first on `PATH`; the `bin64` copies were not otherwise exercised.

## 7. Exit codes

| Situation | Exit |
|-----------|------|
| compiled, with or without warnings and hints | 0 |
| any `Error` or `Fatal` | 1; no exe |
| project file not found (`F1026 File not found: 'Missing.dpr'`) | 1 |

Do not test the exit code through a pipe (`dcc32 ... | findstr ...` reports `findstr`'s code in cmd).
Redirect to a file, then read `%ERRORLEVEL%`.

## 8. Failures, by message

| Message | Cause | Fix |
|---------|-------|-----|
| `F2613 Unit 'SysUtils' not found` | no `-NS` | add `-NSSystem` |
| `F1026 File not found: 'ver.inc'` | include folder missing | `-I<folder>` |
| `F1026 File not found: 'src\UnitA.pas'` | wrong working directory | `cd` to the project folder, or pass `-U` |
| `F2613 Unit 'UnitB' not found` | not on `-U` | add the folder |
| `F1027 Unit not found: 'System'` | `--no-config` without the RTL path | `-U"...\lib\win32\release"` or drop the switch |
| `F2039 Could not create output file 'out\X.exe'` | folder missing | `mkdir` it first |
| `E1026 File not found: 'X.res'` | `{$R *.res}`, no resource file | section 5 |
| `F2063 Could not compile used unit 'U.pas'` | follows an error inside `U.pas` | fix the error printed **above** it |
| `F1030 Invalid compiler directive: 'W1035'` | a warning given by number | use the name: `-W^NO_RETVAL` |
| `F2048 Bad unit format: ... Windows Unicode(x86)` | a `.dcu` from the other platform in `-NU` | one `-NU` folder per platform |
