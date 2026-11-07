# The review procedure

A review has five stages. The order is the point: each stage throws away what the previous one cannot
support, so what reaches the report has survived an attempt to disprove it.

| Stage | Question it answers | Output |
|-------|--------------------|--------|
| 1. Discover | Where could something be wrong? | A candidate list, from searches, not from reading |
| 2. Judge | Is each candidate a defect, and what does it cost? | Candidates with a runtime cost, or dropped |
| 3. Refute | Can I prove this one is *not* a defect? | Survivors only |
| 4. Verify | Can I make the machine confirm it? | An evidence label per survivor |
| 5. Report | What does the user need to act? | One entry per finding, in the template below |

---

## Stage 1: discover, do not read

Reading a code base into context to look for problems finds the problems that look like problems. Search
for them instead, then read only what a search returned.

1. **Compile with warnings and hints on and keep the output.** `reference/static-analysis.md`. Every line is a
   candidate that needs no judgment about style.
2. **Run it once with `ReportMemoryLeaksOnShutdown := True`**, or run its tests. `reference/leaks.md`. Write
   down the report *before* you change anything: it is the baseline stage 4 subtracts from.
3. **Run the pattern for each smell** in `reference/discovery.md`, in the order of the ranking in `SKILL.md`.
4. **Record every hit** in a list, one line each, before reading any of them:

```text
id  file:line            smell  source        status
C1  Orders.pas:219       2/3    discovery #2  open
C2  Orders.pas:312       11     discovery #11 open
C3  Orders.pas:196       1      W1036         open
```

For a hit, read the **enclosing routine** and the declaration of the types it touches, not the file. If a
smell needs a second unit (an owner, a destructor), read that routine too. Stop when the list is exhausted.
A hit that is not on the list was not reviewed, and the report must not imply it was.

The search does not find everything. `reference/discovery.md` says what each pattern misses; the report says
which smells were searched for, so the reader knows what "none found" covers.

---

## Stage 2: judge each candidate

For each open candidate answer three questions in writing, one line each:

1. **What happens at runtime if this is a defect?** A leak, an access violation, a wrong value, a hang. If
   the honest answer is "nothing observable", drop it (`reference/smells.md` "What not to report").
2. **On which path?** Every call, only the error path, only after a refactor. This sets the severity.
3. **What would make it not a defect?** Write the sentence now, because stage 3 tests it.

---

## Stage 3: try to refute

Take each judged candidate and try to prove it is **not** a defect. A finding that survives an honest attempt
is worth the user's time; one that was never attacked is a guess. Drop a candidate the moment one of these
holds, and record why next to it.

**Ownership moved.** The object is not leaked because someone else owns it now:
- It was added to a `TObjectList<T>`. That list owns by default: the parameterless constructor calls
  `Create(True)` (`System.Generics.Collections.pas`). Check the list was not built with `Create(False)`.
- It was added to a `TObjectDictionary<K,V>`. Unlike the list, this one owns **nothing** unless told to:
  the flags are `Create([doOwnsValues])` (`TDictionaryOwnerships`, `doOwnsKeys` / `doOwnsValues`). A call
  with no argument compiles, and a probe that added one `TStringList` to such a dictionary and freed the
  dictionary printed `TStringList x 1`. Read the constructor call, not the type name.
- It was created with an `Owner` (`TFoo.Create(Self)` on a `TComponent`), or handed to a constructor that
  stores and frees it. Open that destructor and look for the `Free`.
- It is returned (`Result := lObj`) and the caller owns it. Then the finding, if any, is that nothing says so
  (smell 7), not a leak.

**Freed somewhere you did not look.** Search the whole project for the other half before claiming a leak:
the field's `Free` in the destructor, a `finalization` section, a caller's `try/finally`. The pairs to
search for are in `reference/discovery.md` (steps two for smells 5, 8 and 20).

**Held by an interface.** If the variable's type is an interface, reference counting frees it. A leak report
for such a type means a cycle (smell 6), not a missing `Free`.

**Guarded elsewhere.** The routine looks unprotected, but every caller wraps it, or an outer `finally`
covers the object. Read the callers: `rg -n '\bRoutineName\b'`.

**Dead code.** The routine has no callers, sits under an `{$IFDEF}` that is not defined in any
configuration, or lives in a unit no project includes. A defect in dead code is a deletion, not a bug.

**Deliberate and written down.** `RegisterExpectedMemoryLeak` with a comment, a `{$WARN … OFF}` with a
reason, or a hidden-virtual marked `reintroduce`. The finding is gone if the reason holds.

**Already caught.** The compiler promotes this warning to an error in this project, or the test suite has a
leak monitor that fails on it. Then it is not reachable in a green build.

Counter-analysis is not a courtesy pass. On the sample units used to test the patterns, 2, 5, 8, 9, 11 and 20
hit the **correct** code as well; every one of those hits is dropped here.

---

## Stage 4: verify what can be verified

The label in the report is earned by what you ran. Choose the cheapest check that could prove the finding
**wrong**, and run it.

| Smell | Cheapest check | What counts as proof |
|-------|----------------|----------------------|
| 1 constructor in `try` | Compile; look for `W1036` on the `Free` line | The compiler line, copied. It fired in the sample, but not in every shape: no line is not an acquittal |
| 2, 3 leak | Leak probe (below) calling the routine, on the raising path for 2 | The leak report naming the class and the count |
| 5 object and interface | Leak probe calling the routine | In the sample on 37.0 Win32 it ended in `EInvalidPointer`; the exception name is the proof |
| 6 cycle | Leak probe | Two classes leaked with equal counts |
| 7 returned object | Leak probe that calls the function and drops the result | The leak report |
| 8 global | Run the program and let it exit | The report lists it |
| 13 result, 17 hidden virtual | Compile | `W1035` / `W1010`, copied |
| 18 concatenation | Time it with the real row count | The two timings. Below a few hundred appends there is no finding |
| 9, 10, 11, 12, 14, 15, 16, 19, 20 | Usually only reading | Label INFERRED. Do not invent a probe that proves nothing |

### A leak probe

A console program that calls the suspect routine once and exits. `ReportMemoryLeaksOnShutdown` prints, so a
**console** host is required: on a GUI host the report is a modal dialog (`reference/leaks.md` §2).

```delphi
program Probe;
{$APPTYPE CONSOLE}
uses
  System.SysUtils, System.Classes, Bad;       // Bad = the unit under review
begin
  ReportMemoryLeaksOnShutdown := True;
  var lRows := TStringList.Create;
  try
    lRows.CommaText := 'a,b,c,d';
    S03_CreateInLoop(lRows);                  // the routine in question, once
  finally
    lRows.Free;
  end;
end.
```

Compile with `dcc32.exe -B Probe.dpr` and run it. With a loop that creates one object per row and frees the
last one, four rows printed:

```text
Unexpected Memory Leak
An unexpected memory leak has occurred. The unexpected small block leaks are:

13 - 20 bytes: TOrderLine x 3
45 - 52 bytes: TDictionary<System.string,System.TObject> x 1
```

Three things to do with it:

- **Subtract the baseline.** The `TDictionary` line is a global created in an `initialization` section of the
  unit under review and never freed; it appears in every run. Run the probe once **without** calling the
  routine, and report only the lines that differ. Otherwise an old leak is blamed on the new finding.
- **Run the fix too.** The same probe against the corrected routine printed only the baseline line. A fix
  that was not run is INFERRED.
- **Count matters.** `x 3` from four rows is `Count - 1`: the signature of smell 3. `x 1` from a single call
  is smell 2. A count that does not scale with the input is something else.

Run the probe under a timeout and make sure no process survives it:

```powershell
$p = Start-Process .\Probe.exe -PassThru -NoNewWindow
try { if (-not $p.WaitForExit(15000)) { $p.Kill() } }
finally { Get-Process Probe -ErrorAction SilentlyContinue | Stop-Process -Force }
```

### What cannot be verified here

A data race, a worker thread touching the UI, a thread outliving its owner, and anything that needs a
database, a network or a second machine. Say so. This skill did not run `TControl.RaiseOnNonMainThreadUsage`
(it exists in `Vcl.Controls.pas` in both the 23.0 and 37.0 trees), so "it raised" is a result you have to
produce yourself before you write it.

---

## Evidence labels

Every finding carries exactly one. A finding without a label is not reported.

| Label | Meaning | You may write |
|-------|---------|---------------|
| **VERIFIED** | You compiled or ran something and have its output | The output, copied: a compiler line, a leak report, an exception name |
| **INFERRED** | It follows from code you read in full, including the callers and the other half of the pair, but you ran nothing | "Reading X and Y, …" and name the lines |
| **ASSUMED** | It depends on something you have not seen: another unit, a DFM, a configuration, third-party source | "If Z is true, …" and name Z |

A label describes your evidence, not your confidence. A strongly worded `ASSUMED` is still `ASSUMED`.
`ASSUMED` findings go in their own section at the end, never mixed into the main list.

## Severity

Severity is the cost **if the finding is true**. It is separate from the label.

| Severity | Cost | Examples |
|----------|------|----------|
| **Critical** | Wrong data, a crash, or unbounded growth on a path every user takes | Double free on a hot path; a per-request leak |
| **High** | A crash, a leak or a wrong result on a path users reach, or an error path that is routinely hit | `Create` with no `try/finally` in code that can raise; `except end` around a commit |
| **Medium** | Correct today, wrong after a plausible change | A hidden virtual that is never called; a magic number for a status |
| **Low** | A cost that only matters at scale, or that only costs maintenance | Concatenation in a loop of a few thousand rows |

There is no "info" level. If it would be info, it is not a finding.

---

## Stage 5: the report

Order by severity, then by label (VERIFIED before INFERRED). One entry per finding:

```text
### <n>. <one-line title>            <Severity> · <LABEL>

File:      Orders.pas:219  (smell 3, reference/smells.md)
Breaks:    <what happens at runtime, in one or two sentences, on which path>
Fix:       <the change, as code if it is short>
Verified:  <the command run and the line it printed — or, for INFERRED / ASSUMED, the lines read
            or the thing not seen>
```

A filled example, from the leak probe above:

```text
### 1. Objects created in the loop are never freed            High · VERIFIED

File:      Orders.pas:219  (smell 3)
Breaks:    Every call leaks Count - 1 TOrderLine objects; only the last one is freed after the loop.
Fix:       Put the Create/try/finally inside the loop body, or collect the lines in a
           TObjectList<TOrderLine> and free that once.
Verified:  Probe.exe with 4 rows printed "TOrderLine x 3"; the fixed routine printed no TOrderLine line.
```

After the findings, three short lines the reader needs in order to trust the rest:

```text
Searched for:  smells 1-20 by discovery.md patterns; compiler output (W1010, W1035, W1036); one leak run.
Not searched:  threading (19, 20) beyond the patterns; any unit outside src\.
Dropped:       7 candidates after refutation (4 handed to an owning list, 2 dead code, 1 freed in the destructor).
```

The `Dropped` line is the evidence that stage 3 happened.

### When NOT to report

- A style opinion: naming that is consistent in the file, method length in isolation, `Free` versus
  `FreeAndNil` on a field where either works.
- A smell you cannot say how to detect. If you cannot name a warning, a pattern or a probe, it is a preference.
- A concern you cannot support with a label. "This might leak under some condition" with nothing behind it is
  not `ASSUMED`; it is noise. `ASSUMED` needs the missing fact named.
- A pattern hit you did not read.
- Something the compiler already rejects in this project (a warning promoted to an error).
- An Error Insight squiggle you did not compile.
- Dead code, except to say it can be deleted.
- A finding already listed under another number. Merge them.
- Anything the user did not ask about once the lifetime and exception findings are done. A review that ends
  "no lifetime or exception defects found; searched for X, Y, Z" is a complete review.
