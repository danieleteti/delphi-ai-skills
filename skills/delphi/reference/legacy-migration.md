# Delphi — moving old code forward

A procedure first, then the facts behind each step. The hazards below share one property: **most of them
compile**, many without a single warning, and fail at run time or on a customer's data. A clean build proves
nothing here, so the procedure leans on tests and on search.

Verified by compiling (and where it can run, running) with `dcc32` and `dcc64` of **13 Florence** (folder
`37.0`) and of **12 Athens** (folder `23.0`, compiler 36.0). Results are identical on both unless a line
says otherwise. 11 Alexandria and older were not available: nothing here is confirmed for them.

---

## The procedure

1. **Establish the target.** Release *and* platforms: Win32 only, or Win32 + Win64. Use *Establish the
   target* in `SKILL.md`. A 64-bit target adds a whole class of work (below); do not do it by accident.
2. **Get a baseline build** of the unchanged code with the target compiler. Fix only what stops the build.
   Save the compiler output: the list of warnings is the baseline you will shrink, and the count must never
   grow unexplained. Blockers you will meet:
   - `F2613 Unit 'SysUtils' not found`: unprefixed legacy names (`SysUtils`, `Classes`, `Windows`) resolve
     **only** through *unit scope names*. Compiled: `uses SysUtils, Classes, Windows` fails with no
     scope list and builds with `-NSSystem;Winapi;System.Win`. In the IDE it is the project option *Unit
     scope names*.
   - `WinTypes` and `WinProcs` build because the shipped `bin\dcc32.cfg` (both trees) carries the unit
     aliases `-aWinTypes=Windows;WinProcs=Windows;DbiProcs=BDE;DbiTypes=BDE;DbiErrs=BDE`. Compiled with
     scope names `System;Winapi;System.Win` and no other option. The IDE's own alias setting was not
     checked.
   - **BDE.** `uses DBTables` / `Bde.DBTables`: on 13 Florence `F2613 Unit not found` for Win32 and
     Win64. On 12 Athens `Bde.DBTables` compiles for **Win32 only** (a `Bde.DBTables.dcu` ships in
     `lib\win32\release`, and `DBTables` additionally needs the scope `Bde`); for Win64 it is `F2613`.
     See *From BDE, ADO and dbExpress to FireDAC*.
   - Third-party components and packages must be recompiled for the target. Not checkable from here.
3. **Write characterization tests before touching behaviour.** Pin what the code does *today*, including
   what looks wrong. Capture, as golden values:
   - the **bytes** of every file it writes, using text with an accented letter, a euro sign and a
     non-Latin letter (the defaults below destroy exactly those);
   - numeric results printed at full precision, and every binary record or stream it reads or writes;
   - row counts and sort orders from the data layer.

   ```delphi
   procedure ExpectBytes(const AFileName: string; const AExpected: TBytes);
   begin
     var lActual := TFile.ReadAllBytes(AFileName);       // System.IOUtils
     if (Length(lActual) <> Length(AExpected)) or
        ((Length(lActual) > 0) and not CompareMem(@lActual[0], @AExpected[0], Length(lActual))) then
       raise Exception.CreateFmt('%s: bytes differ (%d vs %d)',
         [AFileName, Length(lActual), Length(AExpected)]);
   end;
   ```
   Compiled on both compilers. For a test runner and structure see the `delphi-testing` skill.
4. **Change one class of problem at a time**, in this order, and **build and run the tests after each
   class** (both platforms if both are targets): build blockers → strings and encodings → pointer-size and
   Win64 API → assembler → data access → deprecations and hints. Mixing classes makes a test failure
   unattributable.
5. **Discover by search**, not by reading. The compiler finds the loud problems; these find the quiet ones.

One pattern per line, plain regex that both `rg` and PowerShell's `Select-String` accept. Triage every hit by
eye: a pattern finds candidates, not bugs.

```text
# 1. Pointer or object stored in an Integer. Hit = address (bug) or small number (fine)?
\b(Integer|LongInt|Cardinal|LongWord|DWORD)\s*\(\s*(@|Self\b|Sender\b|Obj\w*|P[A-Z]\w*|Pointer)
\b(Pointer|TObject)\s*\(\s*\w+\s*\)
# 2. SetWindowLong and the GWL_ constants: replace with the Ptr pair
\b(Set|Get)WindowLong\b
\bGWL_(USERDATA|WNDPROC|HINSTANCE|HWNDPARENT|ID)\b
# 3. Byte counts taken from Length: right only for AnsiChar/Byte buffers, a string needs * SizeOf(Char)
\b(Move|FillChar|CopyMemory|ZeroMemory|BlockRead|BlockWrite)\s*\(.*\bLength\s*\(
\b(Read|Write)Buffer\s*\(.*\bLength\s*\(
# 4. Extended: keep the files that also contain Stream, BlockWrite or a packed record
\bExtended\b
# 5. AnsiString-era types and char sets: text -> string, bytes -> TBytes, sets -> CharInSet
\b(AnsiString|PAnsiChar|AnsiChar|ShortString|WideString|RawByteString)\b
\bin\s*\[
\bset\s+of\s+Char\b
# 6. Assembler: every block needs a Win64 body or plain Pascal
^\s*asm\b
# 7. BDE, dbExpress, ADO in uses
\b(Bde\.)?DBTables\b
\b(DbiProcs|DbiTypes|DbiErrs|BDE)\b
\b(Data\.)?SqlExpr\b
\bDBXCommon\b
\b(Data\.Win\.)?ADODB\b
# 8. Text I/O with the default encoding: pass an encoding
(LoadFrom|SaveTo)File\s*\([^,]*\)\s*;
\b(AssignFile|TIniFile\.Create|TMemIniFile\.Create|TStringStream\.Create)\b
```

```powershell
rg -n -i -g '*.{pas,dpr,inc}' '^\s*asm\b'

Get-ChildItem -Recurse -Include *.pas,*.dpr,*.inc,*.dfm |
  Select-String -Pattern '^\s*asm\b','\bset\s+of\s+Char\b' |
  ForEach-Object { "$($_.Path):$($_.LineNumber): $($_.Line.Trim())" }
```

Every pattern above was run against a sample unit holding the hazards, with `rg` and with `Select-String`;
both tools matched the same lines (the `set of Char` pattern had no instance in the sample). Known limits: they read **one line**;
`(LoadFrom|SaveTo)File` misses a call with a comma inside its argument (`Format('%s', [a, b])`);
`Length` patterns also match the correct `Length(s) * SizeOf(Char)`. Triage by eye.

---

## A. Strings: from AnsiString-era code to Unicode

`string` is `UnicodeString`: UTF-16, `SizeOf(Char)` is 2 (compiled: `SizeOf(Char)=2`, `SizeOf(AnsiChar)=1`,
`SizeOf(string)` is 4 on Win32 and 8 on Win64, because it is a pointer).

### What the compiler tells you, and what it does not

All compiled with default warning settings:

| Code | Text | Triggered by | By default |
|------|------|--------------|-----------|
| W1058 | Implicit string cast with potential data loss from 'string' to 'AnsiString' | `a := s;` (also to `ShortString`) | **on** |
| W1057 | Implicit string cast from 'AnsiString' to 'string' | `s := a;`, `a = s` | **on** |
| W1050 | WideChar reduced to byte char in set expressions | `c in ['a'..'z']`, `set of Char` | **on** |
| W1044 | Suspicious typecast of string to PAnsiChar (and of AnsiString to PWideChar) | `PAnsiChar(s)`, `PChar(a)` | **on** |
| W1000 | Symbol 'StrLen' is deprecated: 'Moved to the AnsiStrings unit' | `StrLen(PAnsiChar)` with `System.SysUtils` only | **on** |
| W1060 | Explicit string cast with potential data loss from 'string' to 'AnsiString' | `AnsiString(s)` | **off**: `{$WARN EXPLICIT_STRING_CAST_LOSS ON}` |
| W1059 | Explicit string cast from 'AnsiString' to 'string' | `string(a)` | **off**: `{$WARN EXPLICIT_STRING_CAST ON}` |

An explicit cast silences W1057/W1058 *and* is itself silent unless you switch W1059/W1060 on. Switch them on
for the migration (they are the complete inventory of every conversion point), then decide per site.
Explicit `AnsiChar(c)` and `Char(ac)` give no warning at all. The W1050 text on 12 Athens ends
`... Consider using 'CharInSet' function in 'SysUtils' unit.`; on 13 it also names `TCharHelper.IsInArray`.

Hard errors, so these cannot hide: assigning `Char` to `AnsiChar` or back (`E2010 Incompatible types`),
`for c in a` with `c: Char` over an `AnsiString` (`E2010`), and `a[1] = s[1]` mixing the two
(`E2015 Operator not applicable to this operand type`).

**`PAnsiChar(s)` compiles and lies.** It reinterprets UTF-16 memory as bytes: for `s := 'abc'`,
`StrLen(PAnsiChar(s))` is **1** while `Length(s)` is 3 (the second byte of `a` is 0). W1044 is the only hint.
To pass text to an 8-bit API, convert: `UTF8String(s)` / `AnsiString(s)` and cast *that*.

### Byte counts: `Length` is characters

```delphi
Move(s[1], lBuf, Length(s));                     // copies 4 bytes of 'ABCD', not 8: 41 00 42 00
Move(s[1], lBuf, Length(s) * SizeOf(Char));      // the 8 bytes; ByteLength(s) is the same, 8
lStream.WriteBuffer(s[1], Length(s));            // Size = 4: half the text, no error
```

`ByteLength` is in `System.SysUtils` (compiled: `ByteLength('ABCD')` = 8 for a `string`, 4 for an
`AnsiString`). Same trap for `FillChar`, `ReadBuffer`, `BlockRead`/`BlockWrite`, `CopyMemory`, and
for any `array[Char] of …`: `SizeOf(array[Char] of Byte)` is 65536, `array[AnsiChar] of Byte` is 256.

### Char sets

`set of Char` compiles (with W1050) but a set holds only the byte range. A non-ASCII character is never a
member (compiled: `#$0416 in ['a'..'z']` and `#$0161 in ['a'..'z', #$61]` are both `False`). Replace with
`CharInSet(c, ['a'..'z'])` (`System.SysUtils`; its set type is `TSysCharSet = set of AnsiChar`, so it can
only test the ASCII/ANSI range, which is what the old code meant) or, for real Unicode classes, with
`System.Character` (`c.IsLetter`).

### The defaults that silently lose data

Compiled and read back byte by byte. The code page is `GetACP`: 1252 on the test machine, **different on
another PC**.

| Call, no encoding given | Writes | Reads |
|-------------------------|--------|-------|
| `TStringList.SaveToFile` / `LoadFromFile` | ANSI, no BOM: `€` becomes `80`, two Cyrillic letters become `3F 3F` (`??`) | a UTF-8 BOM is honoured; **no BOM → ANSI**, so UTF-8 `C3 A9 E2 82 AC 78` reads as 6 characters, not 3 |
| `TFile.WriteAllText` / `ReadAllText` | **UTF-8, no BOM** (`D0 96 D0 96`) | valid UTF-8 even without a BOM; invalid UTF-8 falls back to ANSI |
| `TStreamWriter.Create(fn)` / `TStreamReader.Create(fn)` | UTF-8, no BOM | UTF-8 (CodePage 65001 without a BOM) |
| `TIniFile.Create(fn)` / `TMemIniFile.Create(fn)` | ANSI: Cyrillic becomes `3F` | — |
| `AssignFile` + `Writeln` (text file) | ANSI: `#$0416` becomes `3F` | — |
| `TStringStream.Create(string)` | ANSI (CodePage 1252): 3 characters incl. `€` = **3 bytes** | — |

Also: passing `TEncoding.UTF8` *explicitly* to `TFile.WriteAllText` **adds a BOM** (compiled: 5 bytes for
`é`, i.e. `EF BB BF C3 A9`), while the no-encoding overload does not. Choose on purpose. For a format that
leaves the machine: `TEncoding.UTF8` on every call, never `TEncoding.Default`
(`GetDefault` returns `ANSI` on Windows, per `System.SysUtils`). `TMemIniFile.Create(fn, TEncoding.UTF8)` takes an
encoding (compiled: it wrote a BOM and `D0 96`); `TIniFile` only has `Create(const FileName: string)`, so
for non-ANSI text use `TMemIniFile` with an encoding.

A literal in a `.pas` file saved as UTF-8 **without** a BOM is read by the compiler as ANSI (seen:
`é€` typed in a `.dpr` became 5 characters). Save migrated sources as UTF-8 **with** BOM, or write
`#$00E9`.

---

## B. 64-bit

### Pointers in `Integer`

On Win64 `Pointer`, `NativeInt`, `NativeUInt`, `THandle`, `HWND`, `WPARAM`, `LPARAM` are 8 bytes;
`Integer`, `LongInt`, `Cardinal`, `LongWord`, `DWORD` stay 4 (compiled, `dcc64`). `Integer(Obj)`,
`Pointer(i)`, `LongInt(@x)`, `Cardinal(p)` are accepted casts: **no warning, no hint**. The high half is
dropped; when bit 31 of the address is set it is replaced by sign extension
(compiled: `00007FF47CB20000` came back as `000000007CB20000`, bit 31 clear; `00007FF486360000` came
back as `FFFFFFFF86360000`, bit 31 set).
A pointer below 4 GB survives, so it works in testing and breaks in production.

`SetWindowLong` still exists on Win64: it is an RTL wrapper taking `NativeInt` that calls
`SetWindowLongPtr` (`Winapi.Windows`). It compiles, and with `Integer(Obj)` as the value it stores the
truncated pointer (compiled; `GetWindowLongPtr` returned the truncated value, while
`SetWindowLongPtr(h, GWLP_USERDATA, LONG_PTR(p))` kept it whole). `TComponent.Tag` is `NativeInt`
(8 bytes on Win64), so only the cast through `Integer` loses data.

```delphi
SetWindowLongPtr(h, GWLP_USERDATA, LONG_PTR(lFoo));           // not SetWindowLong, not Integer(...)
lBack := TFoo(GetWindowLongPtr(h, GWLP_USERDATA));
lFoo.Tag := NativeInt(lBack);                                 // TObject(lFoo.Tag) to read it back
PostMessage(h, WM_USER, WPARAM(lFoo), LPARAM(lFoo));          // Winapi.Messages for WM_USER
```
Compiled on both compilers; run: `TObject(lFoo.Tag) = lFoo` is `True`. Keep `Integer` for what is a number
(`TObject(5)` stored in `TStringList.Objects` and read back as `Integer` is a legitimate idiom for small
values).

### Let the compiler list them: 13 Florence only

Two directives exist in 13 and are **rejected on 12** (`E1030 Invalid compiler directive`). Both are off by
default, so a plain build is silent:

| Directive | Where it fires | Warning |
|-----------|----------------|---------|
| `{$WARN POINTER_CAST_NARROWER ON}` | `dcc64`: pointer ↔ `Integer`/`Cardinal` | W1076 Typecasting between pointer and narrower integer types |
| `{$WARN POINTER_CAST_MIGRATION ON}` | `dcc32`: pointer ↔ any 32-bit integer | W1077 Typecasting between pointer and 32-bit integer types can cause problems on 64-bit target |

Use **W1076 on `dcc64`**: it flags `Integer(p)`, `Cardinal(p)`, `Pointer(u + 4)` and stays silent on the
fixed `NativeInt` / `LONG_PTR` code above (compiled, zero warnings). W1077 on `dcc32` is a noisy first
inventory only: on Win32 `NativeInt` and `LONG_PTR` *are* 32-bit, so it flags the correct code too. On 12
Athens use the `rg` patterns.

### `Extended`

Win32: 80-bit, `SizeOf(Extended)` = 10, `packed record N: Word; V: Extended end` = 12. Win64: `Extended`
**is** `Double`, `SizeOf` = 8, the record = 10; `Extended(1/3) = Double(1/3)` is `True`, and
`1e300 * 1e300` is `INF` (it was `1E600`). Consequences: results differ in the last digits, overflow
arrives sooner, and **a file or stream written by a Win32 build with `WriteBuffer(e, SizeOf(e))` is
garbage to a Win64 build** (compiled: reading 8 bytes of a Win32-written `1/3` gave `-3.72E-103`). To read
the old 10-byte layout in either build, use the RTL record:

```delphi
var r: TExtended80Rec; d: Double;
lStream.ReadBuffer(r, SizeOf(TExtended80Rec));   // always 10 bytes
d := Extended(r);                                // explicit operator: 1/3, 1234.5 and -2.5E100 round-tripped
```
Compiled on both; the values were written by a Win32 program and read by Win32 and Win64 programs. For
new files, write `Double`.

---

## C. Assembler

The Win32 register convention (`eax`, `edx`, `ecx`) does not exist on Win64, where the first integer
arguments arrive in `rcx`, `rdx`, `r8`, `r9`. Compiled with `dcc64`:

| Win32 `asm` body | `dcc64` | Result |
|------------------|---------|--------|
| `add eax, edx` (as `AddOld(A, B: Integer)`) | compiles, **no warning** | wrong: `AddOld(2,3)` printed `-209833077` on 13 and `8598411` on 12 (garbage, not 5) |
| `mov eax, [eax]` on a pointer parameter | compiles, no warning | crashes (the probe died with a segmentation fault; not re-run here) |
| `push eax` / `pop eax` | `E2116 Invalid combination of opcode and operands` | stops |
| `pushad` / `popad` | `E2003 Undeclared identifier: 'pushad'` | stops |

So the silent ones are the dangerous ones: **grep for `asm`, do not wait for the compiler.** Win64
version, or plain Pascal if it is not hot:

```delphi
function AddInts(A, B: Integer): Integer;
{$IFDEF CPUX64}
asm
  .noframe
  mov eax, ecx
  add eax, edx
end;
{$ELSE}
begin
  Result := A + B;
end;
{$ENDIF}
```
Compiled and run on both (`AddInts(2, 3)` = 5). `.noframe` is `E2105 Inline assembler syntax error` on
`dcc32`, hence the guard. `CPUX64` and `WIN64` are defined by `dcc64`, `CPU386` by `dcc32`; both define
`UNICODE` and `MSWINDOWS` (compiled).

---

## D. Data access: what still builds

| Unit | 13 Florence | 12 Athens |
|------|-------------|-----------|
| `Bde.DBTables`, `DBTables` | `F2613` on Win32 and Win64 | Win32 builds (`DBTables` only with scope `Bde`); Win64 `F2613` |
| `Data.Win.ADODB` (ADO) | builds, Win32 and Win64 | builds |
| `Data.SqlExpr`, `Data.DBXCommon` (dbExpress) | builds, Win32 and Win64 | builds |

BDE is not a migration step you can postpone on 13: the code does not build. ADO and dbExpress still
compile; moving off them is a decision, not an emergency. In `Data.SqlExpr` the old `Commit(TransDesc)` /
`StartTransaction(TransDesc)` are marked `deprecated`; `BeginTransaction` returns a `TDBXTransaction`.

---

## The standard sequence for a pre-Unicode code base

What to change first, and why that order:

1. **Make it build** (step 2 above): unit scope names, unit aliases, BDE, third-party packages. Nothing
   else is measurable until it does.
2. **Turn on the conversion warnings** (`{$WARN EXPLICIT_STRING_CAST ON}` and
   `{$WARN EXPLICIT_STRING_CAST_LOSS ON}`) in the project, so every conversion point is listed once.
3. **Decide the type of each piece of data.** Human text → `string`. Raw bytes (protocol frames, file
   headers, blobs) → `TBytes`. A legacy 8-bit external format you must keep → `AnsiString` or
   `UTF8String` with the conversion *visible*. Do **not** mechanically turn every `AnsiString` into
   `string`: where the bytes go to a file or a socket, that changes the format.
4. **Fix every size-in-bytes expression**: `Move`, `FillChar`, `ReadBuffer`, `WriteBuffer`, `BlockRead`,
   `CopyMemory`, `array[Char]`, `PChar` arithmetic. These compile and corrupt silently.
5. **Fix every file and stream call** to name its encoding (table above). Existing files in an old
   encoding: read them with the encoding they were written in, convert once, then store UTF-8.
6. **Replace `in [...]` on `Char`** with `CharInSet` or `System.Character`.
7. **Leave the Windows API alone.** The unsuffixed names bind to the wide functions
   (`OutputDebugString` is `external kernel32 name 'OutputDebugStringW'` in `Winapi.Windows`), so `PChar`
   code is already correct. Only code that casts to `PAnsiChar` needs attention.
8. **Add `System.AnsiStrings`** where `StrLen`, `StrPas`, `StrPCopy`, `StrComp` are used on `PAnsiChar`
   (W1000), and re-run the tests.
9. Run the characterization tests; compare the golden bytes. Only then move to 64-bit.

## 64-bit readiness checklist

- [ ] No `Integer`, `LongInt`, `Cardinal`, `LongWord` or `DWORD` holds a pointer, object reference,
      handle or `WPARAM`/`LPARAM`/`LRESULT` (`rg` patterns above; `W1076` on 13).
- [ ] `SetWindowLong`/`GetWindowLong`/`GWL_*` replaced by the `Ptr` versions and `GWLP_*`.
- [ ] `Tag` carries `NativeInt`, never `Integer(obj)`.
- [ ] Every `external` declaration and callback signature uses `NativeInt`/`THandle`/`HWND`/`Pointer`
      where the C side has a pointer or `HANDLE`. (Sizes verified; individual declarations are yours.)
- [ ] Every `asm` block has a Win64 body or is plain Pascal.
- [ ] No `Extended` in a file, stream, record sent to a DLL, or `packed record` that is persisted.
      Numeric results re-checked: `Extended` is `Double` on Win64.
- [ ] No `pushad`/`push eax`-style code left (compiler stops on these).
- [ ] The characterization tests pass on **both** builds, and the Win64 build was *run*, not only built.
- [ ] Third-party packages and DLLs exist in 64-bit versions.

---

## From BDE, ADO and dbExpress to FireDAC

Names below are declared in the 13 Florence sources (FireDAC, ADO, dbExpress) and, for BDE, in
`Studio\23.0\source\data\bde\Bde.DBTables.pas` (13 ships no BDE source). The *mapping* is a judgement: check
each property in `FireDAC.Comp.Client.pas` before relying on it. For FireDAC itself (drivers, pooling,
batch, macros) see the `delphi-firedac` skill.

| Concept | BDE | ADO | dbExpress | FireDAC |
|---------|-----|-----|-----------|---------|
| Connection | `TDatabase` (`AliasName`, `DatabaseName`) | `TADOConnection` (`ConnectionString`) | `TSQLConnection` (`Params`) | `TFDConnection` (`DriverName` + `Params`, or `ConnectionDefName`) |
| Named definitions | BDE alias, `TSession` | — | `TSQLConnection.ConnectionName` | `TFDManager` (`ConnectionDefs`, `AddConnectionDef`); `FDConnectionDefs.ini` |
| Link dataset to connection | `DatabaseName` (a string) | `Connection` | `SQLConnection` | `Connection` (a component reference) |
| Query | `TQuery` | `TADOQuery` | `TSQLQuery` | `TFDQuery` |
| Table | `TTable` | `TADOTable` | `TSQLTable` | `TFDTable` (`TableName`, `IndexFieldNames`, `MasterSource`, `MasterFields`) |
| Stored procedure | `TStoredProc` | `TADOStoredProc` | `TSQLStoredProc` | `TFDStoredProc` |
| Command, no result set | `TQuery.ExecSQL` | `TADOCommand` | `TSQLConnection.Execute` | `TFDConnection.ExecSQL`, `TFDCommand`; `ExecSQLScalar` for one value |
| Update SQL | `TUpdateSQL` | — | — | `TFDUpdateSQL` |
| Bulk copy | `TBatchMove` | — | — | `TFDBatchMove` (`FireDAC.Comp.BatchMove`) |
| In-memory dataset | — | — | `TSimpleDataSet` | `TFDMemTable` (`TClientDataSet` also still builds) |
| Transaction | `TDatabase.StartTransaction/Commit/Rollback` | `BeginTrans`/`CommitTrans`/`RollbackTrans` | `BeginTransaction` → `TDBXTransaction` | `TFDConnection.StartTransaction` / `Commit` / `Rollback`, `InTransaction`; no object to pass around |
| Editable result | `RequestLive` | `LockType` | — | `UpdateOptions.RequestLive` |
| Command timeout | — | `CommandTimeout` | — | `ResourceOptions.CmdExecTimeout` |
| Wait cursor | — | — | — | a `…UI.Wait` unit in `uses` (below) |

### The behaviour that bites: `RecordCount`

FireDAC fetches on demand: `FetchOptions.Mode` defaults to `fmOnDemand` with `RowsetSize` 50. Compiled and
run against an in-memory SQLite table of 500 rows (identical on 12 and 13, Win32 and Win64):

| Moment | `RecordCount` |
|--------|---------------|
| right after `Open` | **50** (rows fetched so far) |
| after `Last` | 500 |
| after `Open` with `FetchOptions.RecordCountMode := cmTotal` | 500 |
| after `Open` with `FetchOptions.Mode := fmAll` | 500 |

`TFDRecordCountMode = (cmVisible, cmFetched, cmTotal)`. Code ported from a BDE or ADO dataset that sized a
progress bar or an array from `RecordCount` right after `Open` gets 50, with no error. `cmTotal` costs an
extra count query; `fmAll` loads everything. Decide per dataset.

### A FireDAC program that builds and runs

```delphi
program FDSketch;
{$APPTYPE CONSOLE}
uses
  System.SysUtils, Data.DB,
  FireDAC.Stan.Intf, FireDAC.Stan.Option, FireDAC.Stan.Error, FireDAC.Stan.Def, FireDAC.Stan.Pool,
  FireDAC.Stan.Async, FireDAC.Stan.Param, FireDAC.Stan.ExprFuncs, FireDAC.Phys, FireDAC.Phys.SQLite,
  FireDAC.DApt, FireDAC.ConsoleUI.Wait, FireDAC.Comp.Client;
var
  c: TFDConnection; q: TFDQuery; i: Integer;
begin
  c := TFDConnection.Create(nil);
  q := TFDQuery.Create(nil);
  try
    c.DriverName := 'SQLite';
    c.Params.Values['Database'] := ':memory:';
    c.Connected := True;
    c.ExecSQL('create table t(id integer primary key, v text)');
    c.StartTransaction;
    try
      for i := 1 to 500 do
        c.ExecSQL('insert into t(id, v) values (:a, :b)', [i, 'x']);
      c.Commit;
    except
      c.Rollback;
      raise;
    end;
    q.Connection := c;
    q.SQL.Text := 'select * from t where id > :p';
    q.ParamByName('p').AsInteger := 10;
    q.Open;
    Writeln('after Open: ', q.RecordCount);                      // 50
    q.Last;
    Writeln('after Last: ', q.RecordCount);                      // 490
    Writeln('count: ', c.ExecSQLScalar('select count(*) from t')); // 500
  finally
    q.Free;
    c.Free;
  end;
end.
```

Compiled with `dcc32` and `dcc64` on 13 and `dcc32` on 12; run on all three with the output in the
comments. The units that select the driver (`FireDAC.Phys.SQLite`) and the wait cursor
(`FireDAC.ConsoleUI.Wait`) are **not** pulled in by `FireDAC.Comp.Client`: with `FireDAC.Phys.SQLite` removed
the program builds and then raises `[FireDAC][Phys]-300. Driver [SQLite] is not registered`. A VCL application uses `FireDAC.VCLUI.Wait` (the unit exists in the source;
not compiled in a VCL program here). Other drivers: `FireDAC.Phys.MSSQL`, `FireDAC.Phys.FB`,
`FireDAC.Phys.MSAcc` each declare a `TFDPhys…DriverLink`.
