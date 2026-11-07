# Reading compiler messages, and making a warning fail the build

All output below was produced by `dcc32` / `dcc64` / msbuild 37.0 on small files written to trigger it.
The name-based switches were also run on 12 Athens (`23.0`) with identical results. The table mapping
every warning *name* to its W-number is in the `delphi-code-smells` skill (its static-analysis
reference); this file is about how to drive the build.

## Contents

1. Anatomy of a message
2. By default, nothing fails
3. Make one warning an error: by NAME
4. The forms that do not work
5. Policy for an agent
6. Quoting traps

---

## 1. Anatomy of a message

Direct compiler:

```
Warny.dpr(8) Warning: W1035 Return value of function 'F' might be undefined
Warny.dpr(10) Hint: H2164 Variable 's' is declared but never used in 'Warny'
src\UnitA.pas(13) Fatal: F2039 Could not create output file 'dcu\UnitA.dcu'
W2.dpr(9) Error: E1036 Variable 'n' might not have been initialized
```

Through msbuild (`/v:m`), the same facts in msbuild's format, with the project path appended in brackets:

```
Warny.dpr(8): warning W1035: Return value of function 'F' might be undefined [...Warny.dproj]
Warny.dpr(11): Hint warning H2164: Variable 's' is declared but never used in 'Warny' [...Warny.dproj]
src\UnitA.pas(6): error F1026: File not found: 'ver.inc' [...Unit.dproj]
```

| Letter | Meaning | Effect |
|--------|---------|--------|
| `F` | fatal | compilation stops at once; nothing after it is reliable. msbuild prints it as `error F...` |
| `E` | error | no exe; the compiler may still report more |
| `W` | warning | build succeeds |
| `H` | hint | build succeeds; msbuild prints `Hint warning` and counts it as a warning |

`file(line)` is the line where the compiler noticed, which can be after the real mistake. A promoted warning
keeps its number and changes its letter: `W1035` becomes `E1035`.

**Order matters.** Read the first `E` or `F` and fix that; later errors are often consequences. A misplaced
`uses` gave `E2029`, then `E2003` and `E2010` on correct lines, then `F2063 Could not compile used unit`.
Also: with two warnings promoted at once, only the first error was printed (`E1036`); `E1037` appeared when
promoted alone. Expect the next problem to show up only after you fix the first.

## 2. By default, nothing fails

| Run | Result |
|-----|--------|
| `dcc32 Warny.dpr` | `W1035` and `H2164` printed, **exit 0**, `Warny.exe` built |
| `msbuild Warny.dproj /t:Build` | both printed, the summary (at `/v:n`, or in an `/fl` log) counts 2 warnings and 0 errors, **exit 0**, exe built |
| `-W-` / `DCC_Warnings=false` | hides warnings; the hint remains |
| `-H-` / `DCC_Hints=false` | hides hints; the warning remains |
| `-W-NO_RETVAL` | hides that one warning only |
| `-W+NO_RETVAL` | no change (it was already on) |

`DCC_Warnings` and `DCC_Hints` accept `true` / `false` only. They are not severity levels.

## 3. Make one warning an error: by NAME

There is **no** blanket "warnings as errors" switch in `dcc` or in the `.dproj`. Promote a warning by its
symbolic name (the `{$WARN}` identifier), in any of three places:

| Where | Form | Result |
|-------|------|--------|
| compiler command line | `"-W^NO_RETVAL"` | `Error: E1035`, exit 1, no exe |
| the source (`.dpr`, `.pas`, or a shared `.inc`) | `{$WARN NO_RETVAL ERROR}` | same, from that line on |
| msbuild, one run | `"/p:DCC_NO_RETVAL=error"` | passes `-W^NO_RETVAL`; `error E1035`; error count 1; exit 1; no exe |
| the `.dproj`, permanently | `<DCC_NO_RETVAL>error</DCC_NO_RETVAL>` in the `Base` property group | same, on every build |

For msbuild the property is `DCC_` + the name; its values are `error` (promote), `false` (`-W-NAME`, hide)
and `true` (emits nothing: plain warning).

Names verified end to end (name, W-number it controls): `NO_RETVAL` W1035, `USE_BEFORE_DEF` W1036,
`FOR_LOOP_VAR_UNDEF` W1037. The three are almost never false positives and each is a real defect:

```
dcc32 "-W^NO_RETVAL" "-W^USE_BEFORE_DEF" "-W^FOR_LOOP_VAR_UNDEF" MyApp.dpr
```

Other names come from the table in `delphi-code-smells`. A hint (`H....`) has no name: hints are on or off
(`-H`, `DCC_Hints`); no way to promote one was found.

## 4. The forms that do not work

All of these are plausible, none works; the failure is immediate and says nothing about warnings:

| Tried | Result |
|-------|--------|
| `-W+W1035`, `-W^W1035` | `Fatal: F1030 Invalid compiler directive: 'W1035'` |
| `-WE`, `-WE1035`, `-WEW1035` | `Fatal: F1030 Invalid compiler directive: '-WE...'` |
| `/p:DCC_Warnings=NO_RETVAL` | the value is pasted into the command line as a file name: `error F1026: File not found: 'NO_RETVAL.dpr'` |
| `/p:DCC_W1035=error` | silently ignored: warning and hint printed, exit 0, exe built |
| `/p:Configuration=...`, `DCC_IncludePath` | not warning settings, but the same kind of silent miss (`reference/msbuild.md`) |

## 5. Policy for an agent

- **Baseline, then compare.** A legacy project has hundreds of warnings. Do not promote everything. Build
  once, save the output, and make sure your change adds none.
- **Promote the three dangerous ones for your own run** (section 3). A function that can return garbage must
  not pass as "it built".
- **Do not turn the output green by hiding it.** No `-W-`, `-H-`, `DCC_Warnings=false`, no `{$WARN ... OFF}`
  at the top of a unit. If a warning is a false positive, silence it on the lines that need it and put the
  reason in a comment, then restore it with `{$WARN NAME DEFAULT}` (`delphi-code-smells`).
- **Hints are real, too.** `H2077` (dead store) and `H2164` (unused variable) in code you just wrote usually
  mean a typo or a forgotten line.
- **Make the project enforce it, not the agent.** If the team wants a gate, put the `DCC_<NAME>` properties
  in the `.dproj` (or a `{$WARN ... ERROR}` in a shared `.inc`) so every build, IDE or CI, applies them.
  Do not add that without being asked: it changes what other people's builds do.

## 6. Quoting traps

Both cost a wrong diagnosis while testing:

- **`^` is cmd's escape character.** Unquoted, cmd deletes it: `dcc32 -W^NO_RETVAL x.dpr` reached the
  compiler as `-WNO_RETVAL` and failed `F1030 Invalid compiler directive: '-WNO_RETVAL'`. Always write
  `"-W^NO_RETVAL"`.
- **Never read the compiler's exit code through a pipe.** `dcc32 x.dpr | findstr Error` leaves cmd's
  `%ERRORLEVEL%` as `findstr`'s. Redirect to a file, read the code, then search the file.
- **msbuild's text is localised, the compiler's is not.** On this machine msbuild printed `Avvisi` and
  `Errori`; the lines `error E1035:` and `warning W1035:` were English. Search for the compiler's words and
  the exit code, never for msbuild's summary words.
