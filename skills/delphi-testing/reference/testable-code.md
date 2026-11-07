# Testable code in Delphi: seams, doubles, ownership

Code is testable when everything it talks to that is slow, random or external (clock, mail, database, file
system, network, `Application`) reaches it through a parameter. In Delphi the cheapest seam is an
**interface passed to the constructor**.

Compiled and run with the leak monitor on (`reference/runner-ci.md`, section 5): 13 and 12, Win32 and
Win64, 2 tests passed, 0 leaked.

## 1. What makes code untestable, and the move that fixes it

| Smell | Why it blocks a test | Move |
|-------|----------------------|------|
| `Now`, `Date`, `TDateTime` read inside the logic | result changes every run | take an `IClock` |
| `TFDConnection.Create` / `TRESTClient.Create` inside a method | needs the real service | take an interface (an order store, an HTTP client) |
| business rule inside a form's `OnClick` | needs a form and a message loop | move it to a plain class, leave the handler one line long |
| global singleton (`GConfig`, a `class var` instance) | state leaks between tests | pass it in |
| a method that does the work **and** writes the report | cannot check one without the other | return a value, print elsewhere |

Do not refactor for its own sake. Introduce the seam where a test needs it. For code you cannot change
yet, use a characterization test first (`reference/characterization.md`).

## 2. Constructor injection

Production code (unit `Acme.Reminders`):

```delphi
unit Acme.Reminders;

interface

uses
  System.SysUtils;

type
  IClock = interface
    ['{8B7A41E0-52C3-4D7E-9F10-2A6C5D3E7B01}']
    function Now: TDateTime;
  end;

  IMailer = interface
    ['{8B7A41E0-52C3-4D7E-9F10-2A6C5D3E7B02}']
    procedure Send(const ATo, ASubject: string);
  end;

  TReminderService = class
  private
    fClock: IClock;
    fMailer: IMailer;
  public
    constructor Create(const AClock: IClock; const AMailer: IMailer);
    // Returns how many reminders were sent.
    function SendDue(const ADueDates: TArray<TDateTime>; const ARecipient: string): Integer;
  end;

implementation

constructor TReminderService.Create(const AClock: IClock; const AMailer: IMailer);
begin
  inherited Create;
  fClock := AClock;
  fMailer := AMailer;
end;

function TReminderService.SendDue(const ADueDates: TArray<TDateTime>; const ARecipient: string): Integer;
var
  lDue: TDateTime;
begin
  Result := 0;
  for lDue in ADueDates do
    if lDue <= fClock.Now then
    begin
      fMailer.Send(ARecipient, 'Payment due ' + DateToStr(lDue, TFormatSettings.Invariant));
      Inc(Result);
    end;
end;

end.
```

- Interfaces need a GUID (`Ctrl+Shift+G`), or `Supports` and `as` do not work.
- The interface parameters are `const`: no reference-count traffic on the call.
- The real implementations of `IClock` and `IMailer` (system clock, SMTP) live in a separate unit that wires
  them up. Tests never `uses` it.

## 3. Hand-written doubles

A framework is not needed. Three kinds cover almost everything:

| Kind | Does | Use for |
|------|------|---------|
| stub | returns a fixed answer | clock, rate table, configuration |
| spy | records calls, the test inspects them afterwards | "was an email sent, with what subject" |
| failing double | raises | the error path |

No mocking library is used here. None ships with RAD Studio: no mock unit exists in the 37.0 tree. DUnitX's
own tests use Delphi-Mocks, a separate GitHub project that `CONTRIBUTING.md` in the DUnitX folder names
as a prerequisite. A hand-written double is about ten lines and fully visible in the debugger.

```delphi
uses
  System.SysUtils, System.Classes, DUnitX.TestFramework, Acme.Reminders;

type
  TFixedClock = class(TInterfacedObject, IClock)            // stub
  private
    fNow: TDateTime;
  public
    constructor Create(const ANow: TDateTime);
    function Now: TDateTime;
  end;

  IMailSpy = interface                                       // what the test is allowed to read
    ['{8B7A41E0-52C3-4D7E-9F10-2A6C5D3E7B03}']
    function Subjects: TStrings;
  end;

  TSpyMailer = class(TInterfacedObject, IMailer, IMailSpy)  // spy
  private
    fSubjects: TStringList;
  public
    constructor Create;
    destructor Destroy; override;
    procedure Send(const ATo, ASubject: string);
    function Subjects: TStrings;
  end;

  TBrokenMailer = class(TInterfacedObject, IMailer)         // failing double
  public
    procedure Send(const ATo, ASubject: string);
  end;
```

Test bodies (the double's method bodies are the obvious ones: `TBrokenMailer.Send` raises
`EInvalidOperation.Create('smtp down')`, `TSpyMailer.Send` adds `ASubject` to `fSubjects`):

```delphi
[TestFixture]
TReminderServiceTests = class
public
  [Test] procedure SendDue_SendsOnlyPastDueDates;
  [Test][WillRaise(EInvalidOperation)] procedure SendDue_MailerFails_PropagatesError;
end;

procedure TReminderServiceTests.SendDue_SendsOnlyPastDueDates;
var
  lMailer: IMailer;
  lSpy: IMailSpy;
  lService: TReminderService;
begin
  lMailer := TSpyMailer.Create;     // the interface variables own the double
  lSpy := lMailer as IMailSpy;
  lService := TReminderService.Create(TFixedClock.Create(EncodeDate(2026, 3, 10)), lMailer);
  try
    Assert.AreEqual(2, lService.SendDue([EncodeDate(2026, 3, 1), EncodeDate(2026, 3, 10), EncodeDate(2026, 4, 1)], 'a@b.c'));
    Assert.AreEqual(2, lSpy.Subjects.Count);
    Assert.AreEqual('Payment due 03/01/2026', lSpy.Subjects[0]);
  finally
    lService.Free;                  // the service is a class: the test owns it
  end;
end;

procedure TReminderServiceTests.SendDue_MailerFails_PropagatesError;   // has [WillRaise(EInvalidOperation)]
var
  lService: TReminderService;
begin
  lService := TReminderService.Create(TFixedClock.Create(EncodeDate(2026, 3, 10)), TBrokenMailer.Create);
  try
    lService.SendDue([EncodeDate(2026, 3, 1)], 'a@b.c');
  finally
    lService.Free;
  end;
end;
```

Assert on **observable results** (return values, what the spy recorded, what was raised), not on how many
internal calls were made.

## 4. Who frees what in a test

A test is ordinary code: every object it creates is freed by someone. DUnitX frees only the fixture
instance. For the lifetime rules themselves see `delphi` `reference/memory.md`; the test-specific parts:

| Object | Freed by | Rule in a test |
|--------|----------|----------------|
| the **system under test** (a class) | the test | `Create` before the `try`, `Free` in `finally`; or create in `[Setup]` and free in `[TearDown]` |
| a double reached only through an interface (`TFixedClock.Create` passed straight to the constructor) | reference counting | do not keep an object reference, do not `Free` |
| a double you need to inspect | reference counting, **through an interface variable you hold** | `lMailer: IMailer := TSpyMailer.Create`; read it through a test-only interface (`IMailSpy`) |
| an object the SUT takes ownership of (`OwnsX = True`) | the SUT, in its destructor | the test does **not** free it |
| an object the SUT only borrows | the test | free it after the SUT, in `finally` |
| a fixture field created in `[Setup]` | `[TearDown]` | free it there, not in the test body |

Verified results with the leak monitor on:

- `[Setup]` creates `fList`, `[TearDown]` frees it: clean.
- A test assigns a fixture field with a new object and never frees it: reported **in that test**,
  `160 bytes were leaked in the test method` (Win64).
- SUT owns an object (`OwnsList = True`), test frees the SUT and does not free the list: clean.
- SUT borrows (`OwnsList = False`), test frees the list in `finally`: clean.
- SUT owns the list **and** the test frees it too: **Test Error `Invalid pointer operation`** (a double free).

**Do not keep an object reference to a reference-counted double.** Probe types (compiled, run):

```delphi
IThing = interface
  ['{1B1F2C58-3B0E-4C57-9A41-5D2E7B8A1C99}']
  function Value: Integer;
end;

TThing = class(TInterfacedObject, IThing)    // its destructor counts calls in a global
public
  function Value: Integer;
end;

TKeeper = class                              // stores the interface, like a real SUT
private
  fThing: IThing;
public
  constructor Create(const AThing: IThing);
end;
```

What happens with an object variable depends on the call:

- `lThing: TThing`, then `TKeeper.Create(lThing)`, then `lKeeper.Free`: the object was **destroyed** while
  `lThing` still pointed at it (destructor counter = 1). A later use of `lThing` is a use after free.
- `lThing: TThing` passed to a plain method that does not store it: the object stayed alive until the test
  called `lThing.Free`, and the compiler's hidden interface reference was released afterwards against a freed
  object. Undefined behaviour; it happened not to fail in the run.

Both are wrong. Keep an interface variable instead, `lThing: IThing := TThing.Create`. Then neither the SUT
nor the end of the test frees it early (verified: counter 0 after `lKeeper.Free`, `lThing.Value` still
answers) and nothing calls `Free`.

A fixture-level object created in the constructor and freed in the destructor is outside the per-test leak
measurement; run the console project with `ReportMemoryLeaksOnShutdown := True` to see those
(`delphi-code-smells`).

## 5. Time, files, randomness

| Dependency | Seam |
|------------|------|
| `Now` | `IClock` as above; the stub returns a fixed `TDateTime` |
| file system | take the path or a `TStream`/`TStrings` as a parameter; in the test use a `TStringStream` or a path under `TPath.GetTempPath` removed in `[TearDown]` |
| random values | take the generator, or a seed |
| `Sleep` / waiting | take a delay callback, or test the decision logic without the wait |

A test that touches the real file system must clean up after itself in `[TearDown]`, with `try/finally`
inside if the setup can fail halfway.
