# The Assert API: semantics and failure messages

`Assert` is a class with only `class` methods, declared in `DUnitX.Assert` / `DUnitX.Assert.Ex` and exposed
through `DUnitX.TestFramework` (`Assert = class(DUnitX.Assert.Ex.Assert)`). The last parameter of nearly
every call is `message`: it is appended to the failure text (`Expected [1] but got [2] while adding`).
All results below were run on 13 Florence; 12 Athens gave the same except where marked.

## Strings

| Call | Semantics |
|------|-----------|
| `AreEqual(expected, actual: string; message = '')` | **case-insensitive** unless `Assert.IgnoreCaseDefault := False` |
| `AreEqual(expected, actual: string; ignoreCase: Boolean; message = '')` | explicit. `AreEqual('ABC','abc', False)` fails: `Expected [ABC] but got [abc]` |
| `AreNotEqual` | same two overloads |
| `Contains(theString, subString [, ignoreCase] [, message])` | whole string **first**. Case-insensitive by default |
| `DoesNotContain` | same shape |
| `StartsWith(subString, theString [, ignoreCase] [, message])` | substring **first**. `StartsWith('Hello','Hel')` fails with `[Hel] does not start with [Hello]` |
| `EndsWith(subString, theString ...)` | substring first, like `StartsWith` |
| `NoDiff(expected, actual: string [, ignoreCase] [, message])` | **case-sensitive** (the 3-argument form passes `ignoreCase = False`). Reports the first difference |
| `IsMatch(regexPattern, theString [, message])` | `System.RegularExpressions` match |
| `IsEmpty` / `IsNotEmpty` | string, `TStrings`, `TList`, `IInterfaceList`, `Variant` |

`Assert.IgnoreCaseDefault` is a class property, initialised to `True`. It is global: set it back after a
test that changes it, or set it once in the `.dpr`, before `Execute`.

A third argument that is a `Boolean` is `ignoreCase`; one that is a `string` is `message`:
`AreEqual('a', 'b', 'why')` is a message, `AreEqual('a', 'b', True)` is `ignoreCase`.

`NoDiff` failure text names the position: `Difference at position 14: ['ine2 ok'] does not match ['ine2 KO']`.
The quoted window differs by release (text is escaped, so a line break shows as `#13#10`):

- 13: from 5 characters before the difference to 5 after (`HALF_LENGTH = 5`).
- 12: from the difference, 10 characters forward. Same position, different window.

## Numbers

| Call | Semantics |
|------|-----------|
| `AreEqual(expected, actual: Integer / Int64 / Cardinal / Word / Boolean / Currency; message)` | exact |
| `AreEqual(expected, actual: Double; tolerance: Double; message)` | `Expected [1] but got [1,1]` when outside the tolerance |
| `AreEqual(expected, actual: Double; message)` and the `Extended` pair | no explicit tolerance. `Assert.AreEqual(0.1 + 0.2, 0.3)` **passes** (verified). Give a tolerance when the amount matters |
| `AreEqual(expected, actual: Currency)` | exact; failure reads `Expected [123] equals actual [122]` (the wording is odd; the order is still expected, actual) |

Pass `Currency(122)` for an integer literal, or the overload may resolve to `Integer`.

## Objects, interfaces, classes

| Call | Semantics |
|------|-----------|
| `AreSame(expected, actual: TObject)` / `IInterface` | same reference |
| `AreEqual<T>(expected, actual: T)` | uses `TComparer<T>.Default`. For classes this compares **references**. `Assert.AreEqual<TObject>(a, b)` on two `TStringList` with the same lines fails: `Expected [(TStringList @ ...)] but got [(TStringList @ ...)]`. Without `<TObject>`, two arguments typed `TStringList` resolve to the `TStrings` overload and compare lines (verified) |
| `AreEqual(expected, actual: TClass)` | same class |
| `IsNull(x)` / `IsNotNull(x)` | `TObject`, `Pointer`, `IInterface`, `Variant` |
| `InheritsFrom(descendant, parent: TClass)` | `InheritsFrom(TStrings, TStringList)` fails: `TStrings does not inherit from TStringList.` |
| `Implements<T: IInterface>(value: IInterface; message): T` | fails with `value does not implement <interface name>.`; on success **returns the interface**, so you can chain: `lGreeter := Assert.Implements<IGreeter>(lObj as IInterface)` (`IGreeter` being your own interface) |

`Assert.IsType<T>` is declared `deprecated 'use inheritsfrom - istype is useless'`.

## Collections

| Call | Semantics |
|------|-----------|
| `AreEqual<T>(expected, actual: TArray<T>)` | element by element; `Arrays are different at position [2]. Expected [3] but got [4]` (position is zero-based: the third element) |
| `Contains<T>(const arr: array of T; value)` / `DoesNotContain<T>` | `List does not contain value 9.` |
| `Contains<T>(list: IEnumerable<T>; value)` | `IEnumerable<T>` here is DUnitX's own interface type, not what `TList<T>` implements: **not verified with a `TList<T>`**; a `TList<string>` argument did not compile |

## `TStrings` (multi-line text, golden masters)

```delphi
Assert.AreEqual(expected, actual: TStrings; const message: string = '');
Assert.AreEqual(expected, actual: TStrings; const ignoreLines: array of Integer; const message: string = '');
```

- Line count is compared first: `Number of strings is not equal: Expected [2] but got [1]`.
- Each line is then compared with `NoDiff`, so **case-sensitive**, and a failure ends `... at line 2`.
- `ignoreLines` holds **1-based** line numbers (the source computes `lineNumber := index + 1`). A timestamp on
  the second line is `[2]`. Verified: `[1]` still failed at line 2, `[2]` passed.

## Exceptions

Two forms: the attribute `[WillRaise(...)]` on the test method (`reference/attributes.md`), and the calls
below inside the body. The method argument can be an anonymous method (`TTestLocalMethod = TProc`) or a
method of object (`TTestMethod`).

| Call | Passes when |
|------|-------------|
| `WillRaise(proc, EConvertError, msg)` | the class is **exactly** `EConvertError`. Raising a subclass fails: `Method raised [EArgumentOutOfRangeException] was expecting [EArgumentException]` |
| `WillRaise(proc, nil)` | any exception (a `nil` class means "no class check") |
| `WillRaiseDescendant(proc, EConvertError)` | `EConvertError` or a subclass |
| `WillRaiseAny(proc)` | any exception |
| `WillRaiseWithMessage(proc, EConvertError, 'text')` | exact class **and** exact message. Failure: `Exception [EInvalidOperation] was raised with message [bad thing] was expecting [good thing]` |
| `WillRaiseWithMessageRegex(proc, EConvertError, pattern)` | exact class and message matching the regular expression |
| `WillNotRaise(proc [, EConvertError])` | no exception of that exact class (`Method raised [Exception] was expecting not to raise Any exception.` when one escapes) |
| `WillNotRaiseDescendant`, `WillNotRaiseAny`, `WillNotRaiseWithMessage` | declared in `DUnitX.Assert.pas`. `WillNotRaiseAny` with an anonymous method did **not** resolve in a probe: not verified, prefer `WillNotRaise` |

If nothing is raised, `WillRaise*` fails with `Method did not throw any exceptions.`

An unexpected exception inside a test is reported as an **Error** (the third result kind next to Pass and
Failure); a failed assertion is a **Failure**. Both make `AllPassed` False.

## Control flow

| Call | Effect |
|------|--------|
| `Assert.Fail(message)` / `FailFmt(message, args)` | fails now |
| `Assert.Pass(message)` | ends the test now as passed (it raises `ETestPass`). **With leak detection on this makes the test report a leak** (measured: 28 bytes Win32, 56 bytes Win64; probable cause, not checked in the source: the exception object is still alive when memory is measured). End a test with a real assertion instead |
| `Assert.NotImplemented` | fails with `Not Implemented!` |
| `Assert.IsTrue(cond, msg)` / `IsFalse` | `Condition is False when True expected. [msg]` |

A test with no assertion at all passes, unless `runner.FailsOnNoAsserts := True`: then it fails with
`No assertions were made during the test`.

## Mistakes this API invites

| Wrong | Why | Right |
|-------|-----|-------|
| `Assert.AreEqual<TObject>(lObjA, lObjB)` or `AreEqual` on two objects of your own class | generic `AreEqual<T>` compares references | compare the fields that matter, one assert each. Two `TStringList` variables go to the `TStrings` overload and compare lines |
| `Assert.AreEqual(expectedStr, actualStr)` to check exact case | case-insensitive by default | `Assert.AreEqual(expectedStr, actualStr, False)` or `NoDiff` |
| `Assert.StartsWith(lFullText, 'prefix')` | arguments reversed | `StartsWith('prefix', lFullText)` |
| `[WillRaise(Exception)]` to accept "any" | exact match: `EArgumentException` fails | `[WillRaise(Exception, exDescendant)]` |
| `Assert.AreEqual(1.5, lValue)` for computed floats | tolerance is not under your control | pass a tolerance |
| `[TestCaseSource('Src')]` | not a DUnitX attribute | `[TestCaseProvider]` |
