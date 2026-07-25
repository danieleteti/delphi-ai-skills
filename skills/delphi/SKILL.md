---
name: delphi
description: Use when writing, reviewing or fixing Delphi / Object Pascal code — any .pas or .dpr unit, the RTL or the VCL — independently of any framework. Covers language level and version gating, inline var, generics, anonymous methods, memory and lifetime (Free, try/finally, interfaces, managed records), strings and encodings, exceptions, System.Generics.Collections, RTTI and attributes, threading, and the naming/formatting conventions. Triggers on "Delphi", "Object Pascal", "pas unit", "TStringList", "TObjectList", "memory leak", "double free", "interface reference", "anonymous method", "TThread", "TStringBuilder", "access violation", "compiler version".
---

# Delphi / Object Pascal — language and RTL guide

The foundation the DMVCFramework skills sit on. **Nothing here assumes a framework or a project layout** —
it applies to a console app, a VCL form, a service, a library.

Everything below was copied from the Delphi 13 Florence RTL/VCL source on disk, or confirmed on the
official docwiki. Version boundaries were checked release by release, not recalled.

---

## When in doubt about an API — verify it, never guess

A plausible-but-wrong RTL identifier costs the user a compile error and their trust. Do not answer from
memory. Verify, in this order:

1. **Read the shipped source.** It is on every developer machine:
   ```
   C:\Program Files (x86)\Embarcadero\Studio\<n>.0\source\rtl\sys\      System.pas, System.SysUtils.pas, System.Types.pas
   C:\Program Files (x86)\Embarcadero\Studio\<n>.0\source\rtl\common\   System.Classes.pas, System.Generics.*, System.IOUtils.pas,
                                                                       System.Rtti.pas, System.Threading.pas, System.JSON.pas, …
   C:\Program Files (x86)\Embarcadero\Studio\<n>.0\source\vcl\          Vcl.Forms.pas, Vcl.Controls.pas, …
   ```
   `<n>` is the product version: **37** = 13 Florence, **23** = 12 Athens, **22** = 11 Alexandria.
   Ask the user for the path if the folder is not there — do not guess the version.
2. **The docwiki**, always current: https://docwiki.embarcadero.com/RADStudio/Florence/en/Delphi_Language_Reference ·
   library reference at https://docwiki.embarcadero.com/Libraries/Florence/en/ (swap `Florence` for
   `Athens` / `Alexandria` to check whether something existed on an older target).
3. **If you cannot verify it, say so.** "I am not sure `TFoo.Bar` exists — check `System.Classes.pas`" is a
   useful answer. A confidently wrong one is not.

---

## Language level — get this right before writing a line

Feature availability is the single most common source of "it looks fine and does not compile".
`CompilerVersion` and the product version, from the docwiki *Compiler Versions* table:

| Release | `CompilerVersion` | Conditional | Studio folder |
|---------|------------------|-------------|---------------|
| 10.3 Rio | 33.0 | `VER330` | 20.0 |
| 10.4 Sydney | 34.0 | `VER340` | 21.0 |
| **11 Alexandria** | **35.0** | `VER350` | 22.0 |
| 12 Athens | 36.0 | `VER360` | 23.0 |
| 13 Florence | 37.0 | `VER370` | 37.0 |

**The DMVCFramework skills in this repository target Delphi 11 Alexandria as the minimum. Unless the user
states a higher target, write code that compiles on 11.**

### Safe on Delphi 11 (introduced in 10.3 Rio or 10.4 Sydney)

```delphi
var lTotal := 0;                          // inline var + type inference       (10.3)
var lName: string := 'ok';                // inline var, explicit type         (10.3)
const cHalf = (L + H) div 2;              // inline const                      (10.3)
for var i := 0 to List.Count - 1 do ...   // for-var                           (10.3)
for var lItem in Collection do ...        // for-in-var                        (10.3)
class operator Initialize(out Dest: TRec);  // custom managed records          (10.4)
```

Added *by* 11 Alexandria, so also safe there:

```delphi
const cFlags = %1001001;                  // binary literal
const cMillion = 1_000_000;               // digit separator
TMySingleton = class(TNoRefCountObject)   // non-refcounted IInterface impl
```

### Delphi 12 Athens only — do NOT use on an 11 target

```delphi
var lSql := '''                           // multiline string literal
  select *
  from customers
  ''';
```
- String literals may exceed 255 characters (they were `ShortString`-limited before).
- `NativeInt` became a *weak alias* — it stopped being a distinct type for overload resolution.
- `System.Generics.Collections`, `System.Generics.Defaults` and `System.Classes.TList` switched every index
  and `Count` from `Integer` to `NativeInt`. Code that declares `var lCount: Integer := MyList.Count;`
  still compiles; code that passes `Count` to a `var Integer` parameter does not.

### Delphi 13 Florence only — do NOT use on an 11 or 12 target

```delphi
X := if Left < 100 then 22 else 45;       // if-then-else *expression* (ternary)
ShowMessage(NameOf(Sender));              // NameOf intrinsic
if Obj is not TFoo then ...               // "is not" / "not in" operators
procedure Fail(const AMsg: string); noreturn;
class operator Initialize;                // implicit Self, no out parameter
TFoo<T: interface> / TFoo<T: unmanaged>   // new generic constraints
{$PUSHOPT} {$POPOPT}
```

`THashSet<T>` and `TOrderedDictionary<K,V>` are **not in Delphi 11** (no docwiki page under
`Libraries/Alexandria`). They exist in 13. Verify before using them on a 12 target.

Gate anything version-dependent explicitly, never by hoping:

```delphi
{$IF CompilerVersion >= 36}    // Delphi 12 Athens and later
  ...
{$ENDIF}
```

---

## Reference files — read the one you need

This SKILL.md is the working core. Depth lives in `reference/`; open a file only when the task needs it.

| File | Read it when the task involves |
|------|-------------------------------|
| `reference/memory.md` | Object lifetime: `try/finally`, `FreeAndNil`, interfaces and reference counting, the mixed object/interface bug, `TObjectList<T>` and `TComponent` ownership, custom managed records, smart pointers |
| `reference/strings.md` | `string`/`UTF8String`/`RawByteString`/`TBytes`, 1-based vs the 0-based `TStringHelper`, `TEncoding`, `Format`, `TStringBuilder`, `SameText` vs `AnsiSameText`, `TStringList` |
| `reference/exceptions.md` | The `Exception` hierarchy, `raise ... at`, re-raise, `InnerException` / `RaiseOuterException`, `try/except/finally` nesting, what not to catch |
| `reference/generics-and-rtti.md` | `System.Generics.Collections` / `.Defaults`, comparers, ownership flags, iteration invalidation, generic constraints, `System.Rtti`, writing and reading attributes |
| `reference/concurrency.md` | `TThread`, `Synchronize`/`Queue`/`ForceQueue`, `TTask`/`ITask`, `TParallel.&For`, `TMonitor`, `TInterlocked`, and the VCL single-thread rule |
| `reference/style.md` | Naming and formatting: the docwiki style guide, one widely-used community guide, and this repository's own house style — plus where they disagree |

---

## Memory and lifetime — the non-negotiables

Delphi objects are **not** garbage collected and **not** reference counted. Interfaces are. Records are
managed by the compiler. Mixing the three is where the bugs live. Full treatment in `reference/memory.md`;
these four rules cover most code:

```delphi
// 1. Create OUTSIDE the try. Inside is the classic bug: if Create raises,
//    the finally frees an uninitialised reference.
lList := TStringList.Create;
try
  ...
finally
  lList.Free;            // .Free is nil-safe; "if x <> nil then x.Free" is noise
end;

// 2. An object reached only through an interface is freed by the reference count.
//    Never Free it, and never hold a second *object* reference to it.
var lLogger: ILogger := TLogger.Create;   // released at end of scope

// 3. Ownership is a property of the container, not a habit.
var lPeople := TObjectList<TPerson>.Create;  // OwnsObjects defaults to True
// Remove/Delete/Clear free the item; Extract/ExtractAt hand it back to you unfreed.

// 4. A TComponent with an owner is freed by its owner. Do not free it yourself.
lTimer := TTimer.Create(Self);   // Self frees it
```

`FreeAndNil` is not a synonym for `Free`. Use it for a **field** that outlives the statement and will be
tested for `nil` later. On a local that is about to go out of scope it buys nothing and hides the fact that
the variable is dead — see `reference/memory.md`.

---

## Common mistakes — what an LLM plausibly writes in Delphi, and why it is wrong

| Wrong | Right | Why |
|-------|-------|-----|
| `s[0]` for the first character | `s[1]`, or `s.Chars[0]` | `string` is **1-based** (desktop). `TStringHelper` — `Chars`, `IndexOf`, `Substring` — is compiled with `{$ZEROBASEDSTRINGS ON}` and is **0-based**. Two indexing bases in one type. |
| `for i := 0 to List.Count do` | `... to List.Count - 1 do` | Off-by-one; `Count` is not the last index. |
| Using the loop variable after a classic `for` | declare `for var i := ...` | The value of a classic `for` counter after the loop is **undefined** by the language. With `for var` the identifier does not even exist outside. |
| `if s == 'x'` / `!=` / `&&` / `\|\|` | `=`, `<>`, `and`, `or` | C operators do not exist. `=` is comparison; `:=` is assignment. |
| `return X;` | `Result := X;` (`Exit(X)` to leave immediately) | `Result` is an implicit variable, not a statement. Reading `Result` before assigning it reads garbage. |
| `Exit;` in a `function` and no `Result` set | assign `Result` on every path | W1035; the caller gets an indeterminate value. |
| `string.Format(...)`, `s.ToUpper()` | `Format('%s', [x])` (`System.SysUtils`), `s.ToUpper` | `Format` is a plain function, not a class method. Delphi omits `()` on no-arg calls. |
| `s.IsNullOrEmpty` on an instance | `string.IsNullOrEmpty(s)` | It is a `class function` on `TStringHelper`. |
| `List.Add(x)` on `TArray<T>` | `TList<T>`, or `SetLength` + index | Dynamic arrays have no methods; `TArray` is a class of static helpers in `System.Generics.Collections`. |
| `try ... except ... finally ... end` | nest them: `try try ... except ... end; finally ... end;` | A single block cannot have both. This is a syntax error, not a style choice. |
| `catch (E: Exception)` | `on E: Exception do` | And `except` without `on` catches everything. |
| Swallowing with `except end` | re-`raise`, or handle one specific class | A bare `except end` deletes the diagnosis. |
| `with lObj do ...` | a local variable | `with` silently shadows identifiers; a later field added to `lObj` can hijack a name in the enclosing scope. Never generate `with`. |
| A method that hides an ancestor's | `override` (virtual/dynamic), `reintroduce` (deliberate hiding), `overload` (same name, other signature) | Without `override` you get a *new* method: the ancestor still calls its own. Silent, and it compiles. |
| `procedure Foo(AText: string)` | `procedure Foo(const AText: string)` | `const` on managed types (string, interface, dynamic array, record) skips the refcount/copy. Recommended by the docwiki style guide. |
| `var` where you meant `out` | `out` when the value is produced, `var` when it is read *and* written | `out` does not require the caller to initialise; both pass by reference and both forbid passing a property. |
| `TCriticalSection` from `System.Classes` | `System.SyncObjs` | Wrong unit; also `TMonitor` (in `System.pas`) locks any `TObject` with no extra field. |
| `TStringList.Create` and assuming it frees `Objects[]` | `TStringList.Create(True)` | The two containers default the opposite way: `TObjectList<T>.Create` owns, `TStringList.Create` does not. `TStringList.Create(OwnsObjects: Boolean)` is the overload that owns. |
| `Sleep` on the main thread | `TTask.Run`, `TThread.CreateAnonymousThread` | Freezes the UI. |
| Touching a control from a worker thread | `TThread.Synchronize` / `TThread.Queue` | The VCL is single-threaded. `TControl.RaiseOnNonMainThreadUsage := True` makes the violation loud. |
| `System.SysUtils` spelled `SysUtils` | the full dotted name | Both resolve, but the docwiki requires the complete unit scope name; mixed spellings break `uses`-cleanup tooling. |

---

## Key units — what you go there for

| Unit | Go there for |
|------|--------------|
| `System` (implicit) | `TObject`, `IInterface`, `TInterfacedObject`, `TNoRefCountObject`, `TCustomAttribute`, `TMonitor`, `ExceptObject`/`ExceptAddr`, `string`/`UTF8String`/`RawByteString` |
| `System.SysUtils` | `Exception` and its hierarchy, `FreeAndNil`, `Supports`, `Format`, `TStringHelper`, `TStringBuilder`, `TEncoding`, `TFormatSettings`, `TProc`/`TFunc`/`TPredicate`, `SameText`/`CompareText`, `TryStrToInt` |
| `System.Classes` | `TComponent`, `TPersistent`, `TStream` family, `TStringList`/`TStrings`, `TStreamReader`/`TStreamWriter`, `TThread`, `TCollection` |
| `System.Generics.Collections` | `TList<T>`, `TObjectList<T>`, `TDictionary<K,V>`, `TObjectDictionary`, `TQueue`, `TStack`, `TEnumerable<T>`, `TArray` helpers |
| `System.Generics.Defaults` | `IComparer<T>`, `IEqualityComparer<T>`, `TComparer<T>.Default` / `.Construct`, `TDelegatedComparer<T>` |
| `System.SyncObjs` | `TCriticalSection`, `TEvent`, `TMutex`, `TSemaphore`, `TInterlocked`, `TSpinLock`, `TCountdownEvent` |
| `System.Threading` | `TTask`, `ITask`, `IFuture<T>`, `TParallel`, `TThreadPool` |
| `System.Rtti` | `TRttiContext`, `TRttiType`, `TRttiProperty`, `TRttiMethod`, `TValue`, `TVirtualMethodInterceptor` |
| `System.TypInfo` | `TTypeKind`, `GetEnumName`/`GetEnumValue`, lightweight property access without `System.Rtti` |
| `System.IOUtils` | `TPath`, `TFile`, `TDirectory` |
| `System.StrUtils` | `SplitString`, `ContainsText`, `StartsText`/`EndsText`, `MatchStr`/`MatchText`, `IndexStr`, `IfThen`, `ReverseString` |
| `System.Math` | `Min`/`Max`, `IfThen`, `InRange`, `EnsureRange`, `SameValue`, `IsZero` |
| `System.DateUtils` | `IncDay`/`IncYear`, `DaysBetween`, `StartOfTheDay`, `ISO8601ToDate`, `DateToISO8601` (note: `IncMonth` lives in `System.SysUtils`) |
| `System.JSON` | `TJSONValue.ParseJSONValue`, `TJSONObject`, `TJSONArray` (DOM); `System.JSON.Serializers` for object mapping |
| `System.NetEncoding` | `TNetEncoding.Base64`, `.URL`, `.HTML` |
| `System.Hash` | `THashSHA2`, `THashMD5`, `THashBobJenkins` |
| `Vcl.Forms` | `Application`, `Screen`, `TForm`, `TCustomForm` |
| `Vcl.Controls` | `TControl`, `TWinControl`, `TControl.RaiseOnNonMainThreadUsage` |

---

## Unit skeleton

```delphi
unit Acme.Orders.Service;

interface

uses
  System.SysUtils,
  System.Generics.Collections,
  Acme.Orders.Entities;

type
  EOrderNotFound = class(Exception);

  IOrderService = interface
    ['{B0F0B7E4-9E4D-4C2E-9E97-3B5D1A2C4F10}']   // Ctrl+Shift+G in the IDE
    function GetByID(const AID: Integer): TOrder;
  end;

  TOrderService = class(TInterfacedObject, IOrderService)
  private
    fOrders: TObjectList<TOrder>;
  public
    constructor Create;
    destructor Destroy; override;
    function GetByID(const AID: Integer): TOrder;
  end;

implementation

constructor TOrderService.Create;
begin
  inherited Create;              // always chain
  fOrders := TObjectList<TOrder>.Create;
end;

destructor TOrderService.Destroy;
begin
  fOrders.Free;                  // free your own before inherited
  inherited Destroy;
end;

function TOrderService.GetByID(const AID: Integer): TOrder;
begin
  for var lOrder in fOrders do
    if lOrder.ID = AID then
      Exit(lOrder);
  raise EOrderNotFound.CreateFmt('Order %d not found', [AID]);
end;

end.
```

Notes that are not optional: the interface GUID (without it `Supports` and `as` do not work), `inherited`
in both constructor and destructor, and a destructor that survives a half-built object — `Destroy` runs
even when the constructor raised, so every field it touches must be `nil`-safe (they are: Delphi zeroes
instance memory before the constructor runs).

---

## House style, in one paragraph

Two-space indent, no tabs. `begin`/`end` on their own lines. Types `T…`, interfaces `I…`, exceptions
`E…`. Parameters `A`-prefixed, fields `F`- (docwiki) or `f`-prefixed (DMVCFramework's own source and the
skills in this repository), locals `l`-prefixed. Full dotted unit names in `uses`. `const` on managed-type
parameters. Details, sources and the places where the published guides disagree: `reference/style.md`.
**When editing an existing file, its conventions win over any guide.**
