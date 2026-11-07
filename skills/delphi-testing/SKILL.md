---
name: delphi-testing
description: Use when writing, running or fixing unit tests in plain Delphi with DUnitX as shipped with RAD Studio - a console test project, fixtures, assertions, test data, per-test leak detection, CI exit codes, and tests that pin down legacy code. Triggers on "DUnitX", "unit test", "TestFixture", "[Test]", "TestCase", "Assert", "test project", "CI exit code", "memory leak in a test", "characterization test", "golden master", "test double".
---

# Delphi unit testing with DUnitX

DUnitX ships with RAD Studio (`...\Studio\<n>.0\source\DUnitX`, precompiled units in `lib\win32\release` and
`lib\win64\release`). No web framework is assumed. For DelphiMVCFramework integration tests (in-process
server, REST client) use the `dmvcframework-testing` skill instead. For leak diagnosis outside tests see
`delphi-code-smells`; for ownership rules see `delphi` `reference/memory.md`.

Everything below was compiled and run with `dcc32` / `dcc64` 37.0 (13 Florence) and cross-checked with
23.0 (12 Athens). Differences are labelled. Not checked on 11 Alexandria (no 22.0 tree here). **Do not recall DUnitX names: open the unit.** The usual
mistake is a plausible attribute that does not exist (`TestCaseSource` is one).

## Critical rules

1. **The exit code is yours.** `ITestRunner.Execute` never sets `System.ExitCode`. After it:
   `if not results.AllPassed then System.ExitCode := EXIT_ERRORS;`. Without it three failing tests exit 0 and
   CI stays green. `-exit:Pause` only waits for Enter (and blocks a CI job); it is unrelated to the code.
2. **Zero tests is green.** A filter that matches nothing (`-r:Typo`) gives `Tests Found: 0`, `AllPassed` True,
   exit 0. No `{$STRONGLINKTYPES ON}` gives `ENoTestsRegistered`; a handler that only prints it exits 0.
   Set `ExitCode` in the `except` branch and fail when `results.TestCount = 0`.
3. **String asserts ignore case by default.** `Assert.AreEqual('ABC','abc')` passes; so does `Contains`.
   Pass `False` as `ignoreCase`, use `Assert.NoDiff`, or set `Assert.IgnoreCaseDefault := False`.
4. **`StartsWith`/`EndsWith` take the substring first**: `Assert.StartsWith('Hel', 'Hello')`. `Contains`
   takes the whole string first. A swapped call fails with a confusing message.
5. **`[WillRaise(EConvertError)]` matches the exact class.** A descendant fails the test. Add `exDescendant`.
6. **Leak detection is off by default.** The default monitor reports 0 bytes. A leaking test passes. See
   `reference/runner-ci.md` for the unit, the define and the search path it needs. With it on, never end a
   test with `Assert.Pass`: the test is then reported as leaking (measured).
7. **One fixture instance serves all its tests.** Fields survive from one test to the next: reset them in
   `[Setup]`. A parameterless constructor is the fixture setup and **silently disables `[SetupFixture]`**;
   the destructor is the fixture teardown.
8. **Generic `Assert.AreEqual<T>` on objects compares references**: two instances of your class with equal
   fields fail. Assert the fields. Arguments typed `TStrings`/`TStringList` compare line by line instead.
9. **`-xml:` needs an absolute path.** A relative one raises `EInOutError: Unable to create directory`.
10. **Inside a test class `WriteLn(msg)` and `Log(msg)` go to the loggers** (a class helper on `TObject`).
    `WriteLn('a', n)` does not compile there; write `System.Writeln` for raw console output.
11. **`[MaxTime]` is unreliable on Win64**: on 13 it ends in an access violation instead of a timeout.
12. **`Assert.AreEqual(1, lDict.Count)` does not compile on Win64** (`E2532`; `Count` is `NativeInt` in 12 and 13).
    Write `Integer(lDict.Count)`. It compiles on Win32, so the error shows up late.

## Which unit declares what

| Identifier | Unit |
|------------|------|
| `[TestFixture]` `[Test]` `[TestCase]` `[Setup]` `[TearDown]` `[SetupFixture]` `[TearDownFixture]` `[Ignore]` `[Category]` `[MaxTime]` `[RepeatTest]` `[WillRaise]` `[IgnoreMemoryLeaks]` `[TestCaseProvider]` `exExact` `exDescendant` `Assert` `TDUnitX` `ITestRunner` `IRunResults` `EXIT_OK` `EXIT_ERRORS` `EXIT_OPTIONS_ERROR` | `DUnitX.TestFramework` |
| `[AutoNameTestCase]` (13 only) | `DUnitX.TestFramework` |
| `TDUnitXConsoleLogger` | `DUnitX.Loggers.Console` |
| `TDUnitXXMLNUnitFileLogger`, `TDUnitXXMLJUnitFileLogger` | `DUnitX.Loggers.XML.NUnit`, `DUnitX.Loggers.XML.JUnit` |
| `TTestDataProvider` | `DUnitX.InternalDataProvider` |
| `TestDataProviderManager` | `DUnitX.TestDataProvider` |
| `TValueArray` | `DUnitX.Types` |
| `ETestFailure`, `ETimedOut`, `ENoTestsRegistered` | `DUnitX.Exceptions` |
| `DUnitX.MemoryLeakMonitor.FastMM4` | unit you add to the project, see `reference/runner-ci.md` |

An attribute argument is compiled in the interface section, so a test unit that writes
`[WillRaise(EArgumentException)]` needs `System.SysUtils` in its **interface** `uses`.

## Skeleton: console project, one fixture (compiled and run)

```delphi
unit Acme.Basics.Tests;

interface

uses
  System.SysUtils, System.Classes,   // interface section: EConvertError is used in an attribute
  DUnitX.TestFramework;

type
  [TestFixture]
  TStringListTests = class
  private
    fList: TStringList;
  public
    [Setup]
    procedure Setup;
    [TearDown]
    procedure TearDown;

    [Test]
    procedure Add_IncreasesCount;

    [Test]
    [TestCase('Plain', 'abc,abc')]
    [TestCase('Padded', '  abc  ,abc')]
    procedure Trim_RemovesBlanks(const AInput, AExpected: string);

    [Test]
    [WillRaise(EConvertError)]
    procedure StrToInt_NotANumber_Raises;
  end;

implementation

procedure TStringListTests.Setup;
begin
  fList := TStringList.Create;      // a fresh object for every test
end;

procedure TStringListTests.TearDown;
begin
  fList.Free;
end;

procedure TStringListTests.Add_IncreasesCount;
begin
  fList.Add('x');
  Assert.AreEqual(1, fList.Count);
end;

procedure TStringListTests.Trim_RemovesBlanks(const AInput, AExpected: string);
begin
  Assert.AreEqual(AExpected, Trim(AInput), False);   // False: case-sensitive
end;

procedure TStringListTests.StrToInt_NotANumber_Raises;
begin
  StrToInt('x');
end;

end.
```

```delphi
program BasicsTests;

{$APPTYPE CONSOLE}
{$STRONGLINKTYPES ON}   // without it the linker drops the fixture classes: "No Test Fixtures found"

uses
  System.SysUtils,
  DUnitX.Loggers.Console,
  DUnitX.Loggers.XML.NUnit,
  DUnitX.TestFramework,
  Acme.Basics.Tests in 'Acme.Basics.Tests.pas';

var
  runner: ITestRunner;
  results: IRunResults;
begin
  try
    TDUnitX.CheckCommandLine;       // parses -r -i -e -xml -cm -exit; without it filters are ignored
    runner := TDUnitX.CreateRunner;
    runner.UseRTTI := True;         // find [TestFixture] classes by RTTI
    runner.FailsOnNoAsserts := True;
    runner.AddLogger(TDUnitXConsoleLogger.Create(TDUnitX.Options.ConsoleMode = TDunitXConsoleMode.Quiet));
    runner.AddLogger(TDUnitXXMLNUnitFileLogger.Create(TDUnitX.Options.XMLOutputFile));
    results := runner.Execute;
    if (not results.AllPassed) or (results.TestCount = 0) then
      System.ExitCode := EXIT_ERRORS;
    if TDUnitX.Options.ExitBehavior = TDUnitXExitBehavior.Pause then
    begin
      System.Write('Done. Press <Enter> to quit.');
      System.Readln;
    end;
  except
    on E: Exception do
    begin
      System.Writeln(E.ClassName, ': ', E.Message);
      if System.ExitCode = EXIT_OK then      // CheckCommandLine already set 100 for a bad option
        System.ExitCode := EXIT_ERRORS;
    end;
  end;
end.
```

Run: `BasicsTests.exe -cm:Quiet -xml:C:\build\results.xml`, then test `%ERRORLEVEL%`. Without `-xml:` the
NUnit file is `dunitx-results.xml` next to the exe. Exit codes: 0 all passed, 1 failure / error / leak,
100 bad command line.

## Writing tests: working rules

- Name `Unit_Scenario_Expectation` (`StrToInt_NotANumber_Raises`). One behaviour per test.
- Create in `[Setup]`, free in `[TearDown]`; or `try/finally` inside the test. A test must leave nothing
  behind (see `reference/testable-code.md`, *Who frees what*).
- Put fixture classes in the **interface** section of a unit listed in the `.dpr` `uses`.
- A test with no assertion passes silently unless `runner.FailsOnNoAsserts := True` (then it fails with
  "No assertions were made during the test"). Turn it on.
- Prefer the typed overloads (`Integer`, `Currency`, `string`, `Boolean`). For `Double` always give a
  tolerance: `Assert.AreEqual(expected, actual, 0.001)`.
- Test the behaviour, not the call sequence. If a class cannot be tested without a database, a clock or the
  file system, pass that dependency in as an interface.
- Legacy code with no tests: pin its current output first, then refactor (`reference/characterization.md`).

## Shipped documentation that is stale

`...\source\DUnitX\TestCaseProvider.md` (same text in 12 and 13) names the provider base class with a
`Base` suffix and its count method `GetCaseAmount`. Neither exists. The class is `TTestDataProvider`
(`DUnitX.InternalDataProvider`) and the method is `GetCaseCount`. The constructor is **abstract**: override
it, and do not call `inherited` in it (that raises `EAbstractError`). Follow `reference/attributes.md`.

## Reference files

| File | Read it when |
|------|--------------|
| `reference/attributes.md` | Any attribute beyond `[Test]` / `[TestCase]`: lifecycle, `[TestCaseProvider]` with a working provider, `[Category]` filters, `[RepeatTest]`, `[MaxTime]` (broken on Win64), `[Ignore]`, fixture inheritance, discovery |
| `reference/assertions.md` | Choosing or reading an `Assert.*` call: string, float, `TStrings`, exceptions, null, collections, failure messages |
| `reference/runner-ci.md` | Command line options, exit codes, loggers, per-test leak detection setup, CI wiring, 12 vs 13 differences |
| `reference/testable-code.md` | Making code testable, hand-written doubles, who frees what in a test, double free in a test |
| `reference/characterization.md` | Golden-master tests for legacy code, volatile lines (timestamps), recording and reviewing the master |
