# Discovery: one search per smell

Stage 1 of the review procedure (`reference/review-procedure.md`): find **candidates** by a deterministic
search instead of reading the code base into context. Each smell in `reference/smells.md` has the same number
here.

**A hit is a candidate, never a finding.** Every pattern below was run on three small sample units written for
this purpose (a "bad" unit with one instance of each smell, a "good" unit with the correct look-alikes, and a
unit of awkward variants). Each entry says what it found, whether it also hit the good code, and what it
cannot see. Tested on `rg` 15.1.0 and PowerShell 7. Not tested: Windows PowerShell 5.1, and source files that
are ANSI or UTF-16 without a BOM.

---

## How to run the patterns

Every pattern is written once and works unchanged in both runners, because it uses only the syntax that
PCRE2 (`rg -P`) and .NET share.

```bash
rg -n -U -P --glob '*.{pas,dpr,dpk}' 'PATTERN'
```

```powershell
function Find-Delphi([string]$Pattern) {
  Get-ChildItem -Recurse -Include *.pas,*.dpr,*.dpk -File | ForEach-Object {
    $f = $_; $t = Get-Content -Raw $f
    $hit = $t | Select-String -Pattern $Pattern -AllMatches
    if ($hit) { $hit.Matches | ForEach-Object { '{0}:{1}: {2}' -f $f.FullName,
      $t.Substring(0, $_.Index).Split("`n").Count, $_.Value.Split("`n")[0].Trim() } }
  }
}
Find-Delphi 'PATTERN'
```

For a pattern that fits on one line, plain `Get-ChildItem -Recurse -Include *.pas | Select-String 'PATTERN'`
also works and gives line numbers natively. The helper exists because `Select-String` reads line by line and
most smells span lines.

Things that bite, all observed while testing:

- **Delphi is case-insensitive, regex is not.** Every pattern starts with `(?i)`. Where one part must stay
  case-sensitive (`l[A-Z]` for an `l`-prefixed local) it is written `(?-i:l[A-Z])`.
- **`rg` needs `-U` for a match that crosses a line** and `-P` for look-ahead and back-references. Without
  `-P`, a look-ahead is a regex error; without `-U` a multi-line pattern silently finds nothing.
- **`rg -L` is `--follow`, not "files without a match".** The flag you want is `--files-without-match`.
- **`rg` prints every line of a multi-line match.** The first line is where the match starts; that is the
  location to report.
- Patterns use `[\s\S]` rather than `.` so no dot-all flag is needed, and `\r?\n`-safe constructs, because
  Delphi files are usually CRLF.
- Patterns use `\x27` for an apostrophe so they survive both shells' quoting.
- When a pattern starts with `(?im)`, `^` means "start of a line".
- **Patterns do not skip comments**, except 16. A commented-out `// FreeOnTerminate := True` is a hit.

Names written with a prefix convention (`l` for locals, `f` for fields, `T` for classes) only work on code
that follows it. Check that first: `rg -c '^\s*var\s+l[A-Z]' --glob '*.pas'` on a few files tells you.

---

## Lifetime

### 1. Constructor inside the `try`

```regex
(?i)\btry\s+\w+\s*:=\s*T\w+(?:<[^;()]*?>)?\.Create\w*
```

Found the bad case; no hit in the good unit. Also found a generic constructor written in mixed case
(`TRY x := TObjectList<TFoo>.Create(True)`).
**Misses:** a constructor that is not the first statement of the `try`; a class not named `T…`
(`Connection.Create`). The compiler adds a second net: `W1036` fired on the bad case here, but it is not
guaranteed in every shape.

### 2. Created, no `try` straight after

```regex
(?im)^[ \t]*(?:var\s+)?(?!Result\b|(?-i:f[A-Z])|Self\b)\w+(?:\s*:\s*[\w.<>]+)?\s*:=\s*T\w+(?:<[^;()]*?>)?\.Create\w*[^;]*;(?!\s*try\b)
```

Found the plain no-`try` case, the loop case, the constructor-in-`try` line, and a global created in
`initialization`. One hit in the good unit: that same global (it is freed in `finalization`, so it is fine).
`Result :=`, fields (`fFoo :=`) and `Self` are excluded on purpose.
**False positives:** setup lines between `Create` and `try` (`lList.Sorted := True;` then `try`); a handoff
to an owner on the next line; `TTask.Create(...)`, which is a class function that returns `ITask`.
**Misses:** objects assigned to something that is not a plain identifier; classes not named `T…`.

Second shape, a temporary that is built and used but never stored:

```regex
(?i)\bT\w+(?:<[^;()]*?>)?\.Create\w*(?:\([^;()]*\))?\.\w+
```

Found `TStringList.Create.Add('x')`; nothing in the good unit.

### 3. Created in a loop, freed after it

```regex
(?i)\b(?:for|while)\b[^;]{0,120}?\bdo\s+begin(?:(?!\b(?:try|procedure|function|constructor|destructor)\b)[\s\S]){0,300}?:=\s*T\w+(?:<[^;()]*?>)?\.Create\w*[^;]*;(?!\s*try\b)
```

Found the bad loop; nothing in the good unit (there the `Create` is followed by `try`).
**False positive:** `lX := TFoo.Create; lList.Add(lX);` inside a loop (handed to an owning list).
**Misses:** a loop body that is a single statement without `begin`; `repeat … until`; a `Create` more than
300 characters into the body.

### 4. `FreeAndNil` on a local

```regex
(?i)\bFreeAndNil\s*\(\s*(?-i:l[A-Z])\w*\s*\)
```

Found the bad case; nothing in the good unit. **Misses:** locals that do not start with `l`, and every
`FreeAndNil` on a field (those are the ones that need the aliasing question, so read them by listing
`FreeAndNil\s*\(\s*f` separately).

### 5. Object and interface reference to the same instance

Two steps. List the classes at risk, then every `Free` in the files that declare one:

```regex
(?i)class\s*\(\s*TInterfacedObject\b
```

```bash
rg -l -i 'TInterfacedObject' --glob '*.pas' | xargs rg -n -i '\.Free\b'
```

```powershell
Get-ChildItem -Recurse -Include *.pas | Select-String 'TInterfacedObject' -List |
  ForEach-Object { Select-String -Path $_.Path -Pattern '\.Free\b' }
```

This is a shortlist generator, not a discriminator: the bad and the good unit both appear, with every `Free`
in them. The judgement is whether the variable being freed holds an instance that an interface variable also
holds. **Misses:** classes that inherit it indirectly, classes in another unit, and `TInterfacedObject`
descendants created in one unit and freed in another. No compiler warning exists for this smell.

### 6. Interfaces pointing at each other

```regex
(?im)^(?![ \t]*\[(?:weak|unsafe)\])[ \t]*(?-i:f[A-Z])\w*\s*:\s*(?-i:I[A-Z])\w*\s*;
```

Lists interface-typed fields (`fName: IName;`), skipping any line that starts with `[weak]` or `[unsafe]`.
Found both ends of the bad cycle. In the good unit it found only the parent-to-child field; the child's
`[weak]` back-reference was skipped. One strong direction is normal, so the finding is a **pair** that point
at each other, which the pattern cannot decide.
**Misses:** fields not named `f…`; an attribute on its own line above the field (this pattern would then
report a field that is in fact weak). The stronger signal is the shutdown report: two classes leaked with equal
counts.

### 7. A function that returns a new object

```regex
(?i)\bfunction\s+(?:\w+\.)?(?!Create|Extract)\w+\s*(?:\([^)]*\))?\s*:\s*T\w+(?:<[^;()]*?>)?\s*;(?:(?!\bend;)[\s\S]){0,300}?\bResult\s*:=\s*T\w+(?:<[^;()]*?>)?\.Create\w*
```

Found both bad functions, including the one with no parameter list. Names that start with `Create` or `Extract`
are skipped, because the name already says the caller owns the result. One hit in the good unit: a function
named `…_Result` that returns a new `TFileStream` with no hint in its name. That one **is** the smell unless
its documentation says otherwise.
**Misses:** a function that builds the object into a local first and assigns `Result` later, and factories
that call another factory.

Step two is the call sites, because the leak is at the caller. For each function name the search found:

```regex
(?i)\b(?:Find|MakeList)\s*\([^)]*\)\.\w+
```

A method call chained straight off a call is a temporary nobody owns. Replace the name list with the real
names. Do not search for `\)\.\w+` alone: it matches every `Format(...).Trim`.

### 8. A global that is never freed

Two steps. Creation in `initialization`:

```regex
(?im)^initialization\b(?:(?!^finalization\b)[\s\S])*?:=\s*T\w+(?:<[^;()]*?>)?\.Create\w*
```

then the units that have an `initialization` but no `finalization`:

```bash
rg --files-without-match -i '^finalization\b' $(rg -l -i '^initialization\b' --glob '*.pas')
```

```powershell
Get-ChildItem -Recurse -Include *.pas | Where-Object {
  (Select-String -Path $_ -Pattern '^initialization\b' -Quiet) -and
  -not (Select-String -Path $_ -Pattern '^finalization\b' -Quiet) }
```

(In PowerShell the `rg` form is `rg --files-without-match -i '^finalization\b' (rg -l -i '^initialization\b' --glob '*.pas')`.)
The first pattern hits both samples (creating in `initialization` is legitimate). The second isolates the bad
one. **Misses:** a lazily created singleton (`if GX = nil then GX := TFoo.Create` inside an accessor), a
`finalization` that exists but does not free this object, and class-level `var` singletons.

### 9. A handler assigned and never removed

```regex
(?im)^[ \t]*(?!Self\.)\w+(?:\.\w+)*\.(?-i:On[A-Z])\w*\s*:=\s*(?!nil\b)\w+\s*;
```

Finds `x.OnSomething := Method;` on another object. Hit in both samples (the good one unsubscribes in its
destructor). The companion search is the evidence:

```regex
(?i)\bOn[A-Z]\w*\s*:=\s*nil\b
```

For each hit, the finding is the absence of a matching `:= nil` in the owning class's destructor.
**False positives:** assigning a handler to a component you own (`lBtn.OnClick := HandleClick`) is fine and is
the bulk of the hits in VCL code; narrow to publishers that outlive the subscriber. **Misses:** subscription
by method call (`fFeed.Subscribe(HandleTick)`, `Add…Listener`), and anonymous-method handlers.

---

## Exceptions and control flow

### 10. `except` with nothing in it

```regex
(?i)\bexcept\s*(?:(?://[^\r\n]*|\{[^}]*\})\s*)*end\b
```

Found both empty handlers in the bad unit, including one that holds only comments; nothing in the good unit.
Handlers that name a class and do nothing:

```regex
(?i)\bon\s+\w+\s*:\s*[\w.]+\s+do\s*(?:;|begin\s*end\b)
```

**Misses:** a handler that only calls `Exit` or `Abort`, and `(* … *)` comments inside the block.

### 11. `try/except` that frees the object

```regex
(?i)\bexcept\b(?:(?!\bend;)[\s\S]){0,120}?(?:\.Free\b|\bFreeAndNil\b)
```

Found the bad case. It also hit the good unit's handoff idiom (`except lStream.Free; raise; end` followed by
`AOwner.Add(lStream)`), which is correct. Each hit needs the "does ownership move on afterwards" read from
`reference/smells.md` entry 11.

### 12. Empty `except` in a destructor

```regex
(?i)\bdestructor\s+\w+\.Destroy\b(?:(?!\b(?:procedure|function|constructor|destructor)\b)[\s\S])*?\bexcept\s*(?:(?://[^\r\n]*|\{[^}]*\})\s*)*end\b
```

Found the bad destructor; the good one (a named handler that logs) was not hit.
**Misses:** a handler that names a class and does nothing (use pattern 10b inside destructors by hand).

### 13. `Result` not assigned on every path, and 17. Hiding a virtual

No source pattern is worth running; the compiler is the discovery tool. Compile, then filter its output for
the codes that matter:

```bash
dcc32.exe -H MyProject.dpr | rg 'W10(35|36|37|10)'
```

```powershell
& dcc32.exe -H MyProject.dpr | Select-String 'W10(35|36|37|10)'
```

On the bad sample this printed `W1010` (hidden virtual), `W1036` twice and `W1035` (function result), and
nothing on the good sample. Without any `-W` flag the compiler printed those four anyway: they are on by
default. A bare `-W` additionally turns on warnings that are off by default (`W1048` appeared). Hiding a
**non-virtual** method gives no warning at all, so that case cannot be discovered by any tool here.

### 14. A function result thrown away

```regex
(?im)^[ \t]*(?:(?:\w+\.)*(?:TryStrTo\w+|TryEncode\w+|Supports)|\w+\.(?:Wait|TryEnter|TryGetValue|Extract))\s*\(
```

Found `TryStrToInt(…);` as a statement; `if TryStrToInt(…) then` in the good unit was not hit. The functions in
the list are the ones whose return type was read in the 37.0 source: `ITask.Wait` returns `Boolean`,
`TMonitor.TryEnter` returns `Boolean`, `TDictionary<K,V>.TryGetValue` returns `Boolean`, `TList<T>.Extract`
returns `T`. **Misses:** every other function; extend the list from what the project calls. Not every hit is a
defect: `lTask.Wait;` with the default infinite timeout, when nobody needs the answer, is fine.

### 15. A magic number

```regex
(?i)\b(?!Result\b)\w*(?:State|Status|Kind|Mode|Code)\w*\s*(?:=|<>|:=)\s*-?(?:[2-9]|\d{2,})\b
```

Found `AOrder.State = 3`; the good unit (a scoped enumeration) was not hit. Case labels:

```regex
(?im)^[ \t]*-?(?:[2-9]|\d{2,})\s*:\s*\S
```

Found `2:` and `3:` in a `case`. **Noisy by nature:** `StatusCode = 404` is a hit and may well be fine;
`0` and `1` are excluded so counts and flags stay quiet. **Misses:** a domain value held in a variable with a
name outside the list.

---

## Structure

### 16. `with`

```regex
(?im)^(?![ \t]*(?://|\{|\(\*))[^\x27\r\n]*?\bwith\s+[^;\r\n]*?\bdo\b
```

Found the bad case and `if A then with B do …`. A line comment (`// with this we do …`) and a string
(`'with x do'`) were not hit, and neither was the good unit. A header split over two lines was also found.
Acute form, several objects at once:

```regex
(?i)\bwith\s+[^;]*,[^;]*\bdo\b
```

**False positive:** the word `with` inside a mid-line `{ … }` comment (`x := 1; { done with this, do not
touch }` was hit by both patterns). **Misses:** a line with a quote before the `with` is skipped, which can
hide a real one.

### 18. String concatenation in a loop

```regex
(?i)\b(?:for|while)\b[^;]{0,120}?\bdo\b(?:(?!\bend;)[\s\S]){0,200}?\b(\w+)\s*:=\s*\1\s*\+
```

Found `lCsv := lCsv + …` in a `for` loop; the good unit (`TStringBuilder`) was not hit. A `while` loop with a
single-statement body is found too. **Misses:** concatenation through `Format('%s%s', [x, y])`, and `repeat … until`
loops. **False positive:** the 200-character window can run past the end of a short loop into the next
statement. Whether it matters depends on the count: below a few hundred appends it does not.

---

## Concurrency

### 19. A worker thread touching the UI

```regex
(?i)\bprocedure\s+\w+\.Execute\s*;(?:(?!\b(?:procedure|function)\b)[\s\S]){0,800}?(?:\b(?:Label|Edit|Memo|Grid|ProgressBar|Form|Application|Screen|ListView|TreeView|StatusBar|Button|ComboBox|CheckBox)\w*\.\w+|\b(?:ShowMessage|MessageDlg)\b)
```

Found `ProgressBar1.Position := …` directly inside a thread's `Execute`. The good unit, which reaches the same
control through `TThread.Queue(nil, procedure …)`, was **not** hit, because the pattern stops at the first
`procedure` or `function` keyword. The price: a direct UI access that comes *after* an anonymous method in
the same `Execute` is missed.

Inside `TTask.Run`:

```regex
(?i)\bTTask\.Run\s*\((?:(?!\bTThread\.(?:Queue|Synchronize)\b)[\s\S]){0,400}?\b(?:Label|Edit|Memo|Grid|ProgressBar|Form|Application|Screen|ListView|TreeView|StatusBar|Button|ComboBox|CheckBox)\w*\.\w+
```

Found `Form1.Caption := …` inside the task; the good unit, which wraps it in `TThread.Queue`, was not hit.
**Misses:** a UI object reached through a field of `Self`, or through a helper method called from the thread.
The runtime net is `TControl.RaiseOnNonMainThreadUsage := True` (declared in `Vcl.Controls.pas`, in both the
23.0 and 37.0 trees); this skill did not run it, so treat "it raised" as a label you have to earn.

### 20. A thread that outlives what it uses

```regex
(?i)\bFreeOnTerminate\s*:=\s*True\b|\bCreateAnonymousThread\b
```

Found `FreeOnTerminate := True` and the `CreateAnonymousThread` call in the bad unit. It also hit
`CreateAnonymousThread` in the good unit. That is intended: `TAnonymousThread.Create` sets
`FreeOnTerminate := True` itself (`System.Classes.pas`, both trees), so an anonymous thread frees itself
without any line saying so. A search for the assignment alone would miss every one.
Step two, units that start threads but never wait for one:

```bash
rg --files-without-match -i '\bWaitFor\b' $(rg -l -i 'CreateAnonymousThread|FreeOnTerminate' --glob '*.pas')
```

```powershell
Get-ChildItem -Recurse -Include *.pas | Where-Object {
  (Select-String -Path $_ -Pattern 'CreateAnonymousThread|FreeOnTerminate' -Quiet) -and
  -not (Select-String -Path $_ -Pattern '\bWaitFor\b' -Quiet) }
```

Listed the bad unit, not the good one (whose destructor calls `Terminate`, `WaitFor`, `Free`).
**Misses:** a `WaitFor` that exists in the file but on a different thread; threads started through
`TTask`, which is a different lifetime model (`ITask`).

---

## What a pattern run cannot tell you

| It can say | It cannot say |
|------------|---------------|
| This construct exists at `file:line` | That the construct is wrong here |
| Which files lack a `finalization` or a `WaitFor` | Whether another unit supplies the missing half |
| A shortlist small enough to read | That nothing outside the shortlist is wrong |

On the samples, these patterns also hit the **good** unit, on purpose or by necessity: 2 (a global), 5, 6 (the
legitimate parent-to-child field), 7 (an unnamed factory), 8, 9, 11 and 20. A hit there cannot be reported
without the refutation pass (`reference/review-procedure.md`, stage 3). The rest were silent on the good unit.
