---
name: delphi-code-smells
description: Use when reviewing existing Delphi / Object Pascal code for defects, hunting a memory leak or an access violation, or hardening new code against the classic mistakes. Covers compiler warnings and hints that indicate a real bug, warnings-as-errors, leak detection and how to make a leak fail a build, third-party static analysis, a catalogue of smells each with a search that finds it, and a staged review procedure with evidence labels. Triggers on "code smell", "code review", "review this unit", "refactor this unit", "memory leak", "leak", "leaking", "double free", "access violation", "AV", "static analysis", "lint", "compiler warning", "W1035", "$WARN", "warnings as errors", "FastMM", "ReportMemoryLeaksOnShutdown", "audit this code", "false positive", "review report".
---

# Delphi code smells — make the machine find them first

A review pass that starts with an opinion is worth little. A review pass that starts with the compiler and
a leak report is worth a lot, because it is objective and free. Do that half first, every time.

Every warning code, directive and API below was **produced by `dcc32.exe` 37.0 on this machine or copied
from the shipped RTL/DUnitX source**, not recalled. Where something could not be verified it says so.

---

## Critical rules

Facts that, if you get them wrong, make a review confidently wrong.

- **`ReportMemoryLeaksOnShutdown` only prints.** It never fails a build, it says nothing if the process
  crashes, and it does nothing in a DLL or package that shares another module's memory manager. A silent DLL
  is not a clean DLL.
- **The leak report names a class and a count, not a line.** Globals created in `initialization` and never
  freed appear in *every* report. Run a baseline first and report only the difference.
- **DUnitX's leak monitor is a no-op until you register a real one.** The default returns 0 from every
  measurement, so out of the box every test passes its leak check.
- **There is no blanket "warnings as errors".** Promote one at a time, by name: `-W^NO_RETVAL` on the command
  line, `{$WARN NO_RETVAL ERROR}` in source. The `W1035` number is not accepted there (`F1030` / `E1030`).
- **The compiler is silent on** a discarded function result, a hidden *non-virtual* method, and an object
  reference mixed with an interface reference to the same instance. Those are found by search and by reading.
- **`FreeAndNil` nils your reference, not anybody else's.** It does not make a shared object safe to destroy.
- **A pattern hit is a candidate, not a finding.** Never report one you did not read, and never report one
  without an evidence label (VERIFIED / INFERRED / ASSUMED). `reference/review-procedure.md`.
- **In `rg`, `-L` is `--follow`**, multi-line patterns need `-U`, look-ahead needs `-P`. Get these wrong and
  the search silently finds nothing. `reference/discovery.md`.

---

## What this skill owns, and what it does not

| Question | Where it is answered |
|----------|---------------------|
| *Why* does this leak? How does ownership work? `Free`, `try/finally`, interfaces, refcounting, `TObjectList<T>`, `TComponent`, managed records | `delphi`, `reference/memory.md` — **not restated here** |
| What is the right `try/except` shape? What must I never catch? | `delphi`, `reference/exceptions.md` |
| `Synchronize` vs `Queue`, locks, `FreeOnTerminate` | `delphi`, `reference/concurrency.md` |
| Who frees the object a DMVC action returns? What is `ToFree`? | `dmvcframework` SKILL.md — **not restated here** |
| **How do I find the leak? How do I prove it? How do I stop it coming back?** | **here** |

This skill is diagnosis. When a smell needs semantics to explain, it links; it does not re-teach.

---

## Which unit declares what

Read from `…\Studio\37.0\source`. A missing `uses` is the commonest compile error in a probe.

| Unit | Declares |
|------|----------|
| `System` (implicit, never in `uses`) | `ReportMemoryLeaksOnShutdown`, `RegisterExpectedMemoryLeak`, `UnregisterExpectedMemoryLeak`, `GetMemoryManagerState`, `TMemoryManagerState`, `TSmallBlockTypeState`, `TInterfacedObject`, `IInterface`, `TMethod`, `TMonitor`, `WeakAttribute` (`[weak]`), `UnsafeAttribute` (`[unsafe]`) |
| `System.SysUtils` | `FreeAndNil`, `TStringBuilder`, `Exception`, `TryStrToInt`, `TryEncodeDate`, `Supports`, `EAbstractError`, `EAssertionFailed`, `ERangeError`, `EIntOverflow`, `EInvalidPointer`, `EAccessViolation` |
| `System.Classes` | `TStringList`, `TStrings`, `TMemoryStream`, `TFileStream`, `TNotifyEvent`, `TComponent` (`FreeNotification`, `RemoveFreeNotification`), `TThread` (`Queue`, `Synchronize`, `RemoveQueuedEvents`, `CreateAnonymousThread`, `FreeOnTerminate`) |
| `System.Generics.Collections` | `TObjectList<T>`, `TDictionary<K,V>`, `TObjectDictionary<K,V>` (`TDictionaryOwnerships`: `doOwnsKeys`, `doOwnsValues`) |
| `System.Threading` | `TTask`, `ITask` |
| `System.IOUtils` | `TFile` |
| `Vcl.Controls` | `TControl`, including the class property `TControl.RaiseOnNonMainThreadUsage` |
| `DUnitX.TestFramework` | `IMemoryLeakMonitor`, `IMemoryLeakMonitor2`, `TTestResultType` (member `MemoryLeak`), `IRunResults`, `EXIT_ERRORS`, `IgnoreMemoryLeaks` (an alias of the one in `DUnitX.Attributes`) |
| `DUnitX.ServiceLocator` | `TDUnitXServiceLocator` (13 Florence; 12 Athens has `TDUnitXIoC` in `DUnitX.IoC`) |
| `System.Sharemem`, `System.SimpleShareMem` | Share another module's memory manager. In such a module `ReportMemoryLeaksOnShutdown` has no effect (RTL comment on the declaration) |

Notes that are not obvious from the names:

- **There is no `FastMM` unit to add.** The memory manager is in `getmem.inc`, which `System.pas` includes. The
  full FastMM is a separate download (`reference/leaks.md` §5).
- `RegisterExpectedMemoryLeak` and `GetMemoryManagerState` are declared `platform`: using them prints `W1002`
  on 37.0 (seen when compiling a probe).
- `DUnitX.MemoryLeakMonitor.FastMM4` uses no external FastMM unit and registers only when
  `USE_FASTMM4_LEAK_MONITOR` is defined. `DUnitX.MemoryLeakMonitor.FastMM5` needs `FastMM5.pas` first in the
  `.dpr` and registers itself unconditionally in `initialization`.
- `FreeAndNil` is declared `procedure FreeAndNil(const [ref] Obj: TObject)` in both the 23.0 and 37.0 trees.

---

## Order of attack — an unfamiliar unit

The five stages (discover, judge, refute, verify, report) are in `reference/review-procedure.md`. Within
discovery, work down this list. **Stop reporting when you run out of items that cost the user something.**

1. **Compile it with warnings and hints on and read every line of output.** Free, objective, and the single
   highest-yield step. `reference/static-analysis.md`.
2. **Run it with `ReportMemoryLeaksOnShutdown := True`.** If there is a test suite, run that.
   `reference/leaks.md`.
3. **Ownership by hand** — every `Create` in the unit: who frees it, on which paths, including the raising
   one. This is where the compiler cannot help you.
4. **Exception handling** — every `except` without an `on`, every empty handler, every `try/except` that
   should have been `try/finally`.
5. **Concurrency** — anything reachable from a `TThread.Execute` or a `TTask.Run` body.
6. **Everything else.** Naming, `with`, long methods, magic numbers.

**A leak the compiler cannot see outranks a naming convention, always.** If the review output is a wall of
style nits and no lifetime finding, the review was not done. Report defects in the order above, and say for
each one what it costs at runtime — a leak, an AV, a silently wrong result. "This is ugly" is not a finding.

---

## The five-minute pass

```bash
# 1. what the compiler already knows (see reference/static-analysis.md for the codes)
dcc32.exe -H MyProject.dpr

# 2. one leak run (reference/leaks.md), then the searches in reference/discovery.md
rg -n -U -P --glob '*.{pas,dpr,dpk}' 'PATTERN'
```

`reference/discovery.md` has one tested pattern per smell below, for `rg` and for PowerShell, with what each
one misses. Start with patterns 1, 3, 10, 12 and 16 (the numbering of `smells.md`): they were silent on the
correct test code. Patterns 2, 5, 8, 9 and 11 also hit correct code and always need the refutation pass.

---

## Reference files

| File | Read it when |
|------|--------------|
| `reference/review-procedure.md` | You are about to review code and report. The five stages, the refutation checklist, how to verify with a leak probe, the evidence labels (VERIFIED / INFERRED / ASSUMED), the severity words, the report template and when not to report |
| `reference/discovery.md` | Stage 1. One search per smell (`rg` and PowerShell, same pattern), with what it found on the test units, whether it also hit the correct code, and what it cannot see |
| `reference/static-analysis.md` | Compiler warnings and hints (verified codes), `$WARN`, turning a warning into an error, the build switches, and an honest note on Pascal Analyzer / SonarDelphi / FixInsight / madExcept / Error Insight |
| `reference/leaks.md` | Finding, reproducing and fencing a leak: the shipped memory manager, `ReportMemoryLeaksOnShutdown`, reading the report, `RegisterExpectedMemoryLeak`, and DUnitX per-test leak detection — the item that makes a leak fail a build |
| `reference/smells.md` | The catalogue. Each entry: the bad code, what it costs at runtime, the fix, and how to detect it |

---

## The defects worth finding, ranked

Detail and detection for each in `reference/smells.md`; the search for each in `reference/discovery.md`
(same numbers as the entries in `smells.md`, not as this table).

| # | Defect | Costs you |
|---|--------|-----------|
| 1 | Constructor **inside** the `try` | `Destroy` called on uninitialised memory — AV |
| 2 | Object created and never freed on some path | Leak |
| 3 | `Create` in a loop, `Free` after it | Leak, once per iteration |
| 4 | Object held as *both* a class reference and an interface | Double free, or a dangling pointer |
| 5 | Two objects holding interfaces to each other | Leak the shutdown report shows as a matched pair |
| 6 | `except end` | The diagnosis is deleted; the program carries on wrong |
| 7 | `try/except` where `try/finally` was meant | Resource is released only when something raised |
| 8 | `Result` not assigned on every path | Caller reads garbage. **W1035** |
| 9 | Event handler / observer never unsubscribed | AV when the publisher fires into a freed subscriber |
| 10 | A `function` that returns an object nobody knows they own | Leak, or a double free |
| 11 | Worker thread touching the VCL | AV, once a week, on the customer's machine |
| 12 | A thread outliving the object it captured | AV at shutdown |
| 13 | Method silently hiding an ancestor's virtual | Wrong method runs. **W1010** |
| 14 | `with` | A field added later hijacks a name; silent, compiles |
| 15 | Magic literal used as a status code | Wrong branch after any refactor |

---

## Reporting a review

- Every finding carries **file:line, a severity, an evidence label, what goes wrong at runtime, the fix, and
  how it was verified.** Not an essay. The template is in `reference/review-procedure.md`.
- Lead with anything that leaks, dangles or returns a wrong value. Style last, or not at all.
- If a compiler warning already covers a finding, **cite the code** (`W1035`) — it turns your opinion into
  something the user can put in their build and never hear from you again about.
- Say what you searched for and what you dropped after trying to refute it. "None found" is only meaningful
  next to the list of what was looked for.
- Never report a smell you cannot say how to detect. If you cannot name a warning, a tool or a search for it,
  it is a preference, and the user did not ask for your preferences.
