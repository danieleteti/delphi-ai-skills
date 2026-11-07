# DUnitX attributes, lifecycle and test data

All behaviour below was run on 13 Florence (37.0) and re-run on 12 Athens (23.0). Differences are labelled.
Attribute classes are declared in `DUnitX.Attributes` and re-exported by `DUnitX.TestFramework`, so
`uses DUnitX.TestFramework` is enough, except where a table says otherwise.

## 1. Discovery: how a fixture is found

A class is a fixture when it carries `[TestFixture]`. A method is a test when it carries `[Test]` or
`[TestCase]` / `[TestCaseProvider]`. A method with no attribute is not a test, and a class without
`[TestFixture]` is not found, even if its methods carry `[Test]`.

| What you do | Result (verified) |
|-------------|-------------------|
| `runner.UseRTTI := True` + `{$STRONGLINKTYPES ON}` + unit in the `.dpr` `uses` | fixtures found |
| `UseRTTI := True`, no `{$STRONGLINKTYPES ON}` | `ENoTestsRegistered: No Test Fixtures found` (the linker dropped the classes) |
| `UseRTTI := False`, no registration | the same exception |
| `UseRTTI := False` + `TDUnitX.RegisterTestFixture(TStringListTests)` in the unit `initialization` | fixture found |
| both `UseRTTI := True` and `RegisterTestFixture` | found once, not twice |

`RegisterTestFixture(const AClass: TClass; const AName: string = '')` is a `class procedure` of `TDUnitX`.

A base class with `[Test]` methods but no `[TestFixture]` is not run itself; each descendant that carries
`[TestFixture]` runs the inherited tests. Use it for a contract test run against several implementations:

```delphi
IGreeter = interface
  ['{0B1F2C58-3B0E-4C57-9A41-5D2E7B8A1C77}']
  function Hello: string;
end;

TGreeterContract = class                    // no [TestFixture]: not run by itself
protected
  function Make: IGreeter; virtual; abstract;
public
  [Test] procedure NotEmpty;
end;

[TestFixture] TEnglishTests = class(TGreeterContract) protected function Make: IGreeter; override; end;
[TestFixture] TItalianTests = class(TGreeterContract) protected function Make: IGreeter; override; end;
```

Verified: both descendants ran `NotEmpty` (2 tests).

## 2. Attribute table

| Attribute | Arguments | Semantics (verified) |
|-----------|-----------|----------------------|
| `[TestFixture]` | none; `(Name)`; `(Name, Description)` | `Name` replaces the class name in the fixture path (`Unit.Name.Method`) |
| `[Test]` | none; `(Enabled: Boolean)` | `[Test(False)]` is not run and not counted |
| `[Setup]` / `[TearDown]` | none | run around **every** test. If several methods carry it, the first found wins (source comment, not run) |
| `[SetupFixture]` / `[TearDownFixture]` | none | run once per fixture, see section 3 |
| `[Ignore]` | `(Reason: string = '')` | reported as Ignored, does not fail the run. Valid on a method and on the class |
| `[Category]` | `(Category: string)` | on the class or the method. A method's category **replaces** the fixture's |
| `[RepeatTest]` | `(Count: Cardinal)` | `3` creates `Name-1-of-3` ... `Name-3-of-3`; `0` ignores the test ("Repeat set to 0") |
| `[MaxTime]` | `(Milliseconds: Cardinal)` | fails the test if still running. **Unreliable on Win64**, see section 6 |
| `[WillRaise]` | `(EClass; Inheritance = exExact)` | passes only if that exception is raised. `exDescendant` accepts subclasses |
| `[IgnoreMemoryLeaks]` | `(Ignore: Boolean = True)` | suppresses the leak check for that test. Class name has **no** `Attribute` suffix |
| `[TestCase]` | `(Name, Values, Separator = ',', TrimValues = False)` | one test per attribute; see section 4 |
| `[AutoNameTestCase]` | `(Values, Separator = ',', TrimValues = False)` | like `[TestCase]`, name generated from the values. **13 only**: not declared in 12 |
| `[TestCaseProvider]` | `('Name')` or `(TRowsProvider)` | rows from a provider class, section 5 |
| `[TestInOwnThread]` | none | declared; the source says "planned but not implemented". Do not use |

`[WillRaise]` is read for plain `[Test]` methods. It is **not** applied to `[TestCase]` methods: for those
use `Assert.WillRaise` inside the method.

## 3. Lifecycle

Verified with a logging fixture. For one fixture with tests `One` and `Two`:

```
constructor            (once per fixture instance)
[SetupFixture]         (once; SKIPPED if the class declares a parameterless constructor)
  [Setup] One [TearDown]
  [Setup] Two [TearDown]
[TearDownFixture]      (once)  -- or the destructor, if there is no [TearDownFixture]
destructor
```

- **One instance for all the tests of a fixture.** A field set in `One` is still set in `Two` (verified: a
  counter incremented in both reached 2). Reset fields in `[Setup]`. Never rely on test order.
- **A parameterless constructor is the fixture setup.** DUnitX treats it so and, when the class declares one,
  **silently ignores** `[SetupFixture]` (verified: the logging method never ran; same on 12 and 13). Pick one.
- **The destructor is the fixture teardown**, unless a `[TearDownFixture]` method exists, which then wins.
- A fixture using `[RepeatTest]` can run its constructor more than once (seen: twice). Keep constructors
  cheap and free of side effects.
- `[Setup]` raising: that test is an Error. `[SetupFixture]` raising, **13**: the fixture's tests are skipped
  and `[TearDownFixture]` does not run. **12**: the tests still run (one passed in the probe) and
  `[TearDownFixture]` runs. The run fails in both.
- Output from tests: inside a fixture, `Log('msg')` and `WriteLn('msg')` (one string argument) go to the
  runner's loggers, because `DUnitX.TestFramework` declares a class helper on `TObject`
  (`TTestFixtureHelper`). `WriteLn('a', 1)` therefore fails to compile in a method (`E2034 Too many actual
  parameters`). For direct console output write `System.Writeln(...)`.

## 4. `[TestCase]`

```delphi
[Test]
[TestCase('Plain', 'abc,abc')]
[TestCase('Padded', '  abc  ,abc')]
procedure Trim_RemovesBlanks(const AInput, AExpected: string);
```

- The test name is `Method.CaseName` (`Trim_RemovesBlanks.Plain`). `[Test]` is optional with `[TestCase]` (verified).
- Values are one string split on the separator and converted to the parameter types. Verified: `Integer`,
  `Currency`, `Double`, `Boolean`, `string`. A value containing a comma needs another separator:
  `[TestCase('Semi', 'x;y z;w', ';')]`.
- Spaces are kept unless the fourth argument is `True`: `[TestCase('Trim', ' x , y ', ',', True)]` passes
  `'x'` and `'y'`.
- `-r:` takes the full name, e.g. `-r:Acme.Basics.Tests.TStringListTests.Trim_RemovesBlanks.Plain`.

## 5. `[TestCaseProvider]`: data built in code

There is **no `TestCaseSource` attribute**. `[TestCaseSource('X')]` compiles with warning
`W1074 Unknown custom attribute` and is ignored. The attribute is `[TestCaseProvider]`.

Three things must all be present, or cases silently vanish or the run dies:

1. a provider class descending from `TTestDataProvider` (`DUnitX.InternalDataProvider`) that overrides the
   **abstract** `constructor Create` and `GetCaseCount`, `GetCaseName`, `GetCaseParams`;
2. `TestDataProviderManager.RegisterProvider(Name, TRowsProvider)` (`DUnitX.TestDataProvider`), normally in the
   `initialization` section;
3. `[TestCaseProvider('Name')]` (or `[TestCaseProvider(TRowsProvider)]`) on the test method.

```delphi
unit Acme.Rows.Provider;

interface

uses
  System.Rtti,
  DUnitX.Types,                  // TValueArray
  DUnitX.InternalDataProvider;   // TTestDataProvider

type
  TRowsProvider = class(TTestDataProvider)
  public
    constructor Create; override;                    // abstract in the base: must be overridden
    function GetCaseCount(const methodName: string): Integer; override;
    function GetCaseName(const methodName: string; const caseNumber: Integer): string; override;
    function GetCaseParams(const methodName: string; const caseNumber: Integer): TValueArray; override;
  end;

implementation

uses
  DUnitX.TestDataProvider;       // TestDataProviderManager

constructor TRowsProvider.Create;
begin
  // No "inherited Create": it is abstract and raises EAbstractError.
end;

function TRowsProvider.GetCaseCount(const methodName: string): Integer;
begin
  Result := 2;
end;

function TRowsProvider.GetCaseName(const methodName: string; const caseNumber: Integer): string;
begin
  Result := 'row';
end;

function TRowsProvider.GetCaseParams(const methodName: string; const caseNumber: Integer): TValueArray;
begin
  Result := [TValue.From<Integer>(caseNumber), TValue.From<Integer>(caseNumber * 2)];
end;

initialization
  TestDataProviderManager.RegisterProvider('Rows', TRowsProvider);

end.
```

```delphi
// in a fixture (the provider unit must be in the .dpr uses; it is linked because of initialization)
[Test]
[TestCaseProvider('Rows')]
procedure Doubles(const A, B: Integer);
```

Verified outcome: tests `Doubles.row (00)` and `Doubles.row (01)`, both run and pass.

| Mistake | What happens (verified) |
|---------|-------------------------|
| provider not registered | the cases are silently dropped |
| `constructor Create` not overridden | `EAbstractError: Abstract Error` while the run starts |
| `inherited Create` inside the override | the same `EAbstractError` |
| `[TestCaseSource('X')]` | warning W1074, no cases from it |

`CustomTestCaseSourceAttribute` (abstract, with `GetCaseInfoArray`) is the other extension point, for an
attribute of your own. Do not invent a name for it.

## 6. `[MaxTime]`

Windows only. It starts a watchdog thread that, after the time, injects an exception into the test thread
by setting the instruction pointer. The source writes the address as `Cardinal(@RaiseTimeOutException)`
(`DUnitX.Timeout.pas`, identical in 12 and 13), which truncates a 64-bit address.

| Target | Result of `[MaxTime(50)]` on a test that sleeps 200 ms |
|--------|---------------------------------------------------------|
| Win32, 12 and 13 | Failure, message `Operation Timed Out` |
| Win64, 12 | Failure, `Operation Timed Out` (the source has the same truncation, so this depends on the load address: inference) |
| Win64, 13 | **Error: Access violation** at a truncated address |

Do not trust it on Win64. For slow-code detection measure with `TStopwatch` inside the test and assert on
the elapsed time, or run the suite under a CI job timeout.

## 7. `[Category]` and filters

`[Category('slow')]` on a class or a method. On the command line (the project must call
`TDUnitX.CheckCommandLine`): `-i:` includes, `-e:` excludes. Verified grammar:

| Expression | Meaning | Tests selected in the probe |
|------------|---------|----------------------------|
| `-i:a` | category `a` | 1 |
| `-i:slow,a` | `slow` **or** `a` | 2 |
| `-i:a+b` | `a` **and** `b` (a method declared `[Category('a,b')]` has both) | 1 |
| `-i:slow+a` | both | 0 |
| `-e:fixcat` | everything except the class category | the tests that set their own category stay |

A category name must not contain `,` `;` `-` `|` `+` `(` `)`: they are operators. `slow-tests` is not a
usable name. A matching expression with no tests is not an error: see `reference/runner-ci.md` on empty runs.
`-r:` selects by name (`-r:Acme.Basics.Tests.TStringListTests.Add_IncreasesCount`, several names with commas).
