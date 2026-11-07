# Characterization (golden-master) tests for legacy code

A characterization test does not say the code is right. It records what the code does **today**, so a
refactoring that changes the behaviour turns red. Use it when the code has no tests and you must touch it.
It is the first step; the seams in `reference/testable-code.md` come after.

Compiled and run on 13 and 12, Win32 and Win64: 3 tests passed; a corrupted master failed with the
message shown in section 4.

## 1. The method

1. Pick inputs that exercise the code (real data from a bug report is better than invented data).
2. Call the legacy code and turn its output into text. Return value, a report, a file it wrote, a log: one
   `TStringList`, one line per fact.
3. Save that text as a **golden file** in the repository. **Read it.** If it contains something obviously
   wrong, that is a bug you now know about; the master still records the bug, on purpose.
4. The test runs the code again and compares with the golden file.
5. Refactor. Red means the behaviour changed. Decide: regression (fix the code) or intended change (replace
   the golden file in the same commit, with a reviewer looking at the diff).

Never regenerate masters automatically on a failure: that turns the test into a recorder that cannot fail.

## 2. Code (compiled and run)

The legacy function (stand-in for code you do not dare to change). Its second line changes on every run:

```delphi
unit Acme.Report;

// Stand-in for legacy code we do not dare to touch.
interface

function BuildReport(const ACustomer: string; const ATotal: Currency): string;

implementation

uses
  System.SysUtils;

function BuildReport(const ACustomer: string; const ATotal: Currency): string;
begin
  Result := 'ORDER REPORT' + sLineBreak +
    'Generated: ' + FormatDateTime('yyyy-mm-dd hh:nn:ss', Now) + sLineBreak +
    'Customer: ' + ACustomer + sLineBreak +
    'Total: ' + CurrToStrF(ATotal, ffFixed, 2, TFormatSettings.Invariant);
end;

end.
```

The test unit. Folder layout: `golden\` holds `report.ACME.txt`, `report.GLOBEX.txt`; the first run creates
them (and fails), the second compares. `golden\` must exist before the first run.

```delphi
unit Acme.Report.Tests;

interface

uses
  DUnitX.TestFramework;

type
  [TestFixture]
  TReportCharacterization = class
  public
    [Test]
    [TestCase('Acme', 'ACME')]
    [TestCase('Globex', 'GLOBEX')]
    procedure BuildReport_MatchesGoldenMaster(const ACustomer: string);

    [Test]
    procedure BuildReport_TimestampMovedButMasterStillMatches;
  end;

implementation

uses
  System.SysUtils, System.Classes, System.IOUtils, System.RegularExpressions,
  Acme.Report;

const
  // 1-based, as Assert.AreEqual(TStrings, TStrings, ignoreLines) wants them.
  TIMESTAMP_LINE = 2;

// The folder named "golden" is searched upward from the exe, so the output
// directory (Win32\Debug, Win64\Release, a CI folder) does not matter.
function GoldenFile(const AName: string): string;
var
  lDir, lParent: string;
begin
  lDir := ExcludeTrailingPathDelimiter(ExtractFilePath(ParamStr(0)));
  while not TDirectory.Exists(TPath.Combine(lDir, 'golden')) do
  begin
    lParent := ExcludeTrailingPathDelimiter(ExtractFilePath(lDir));
    if (lParent = '') or (lParent = lDir) then
      raise EFileNotFoundException.Create('No "golden" folder above ' + ParamStr(0));
    lDir := lParent;
  end;
  Result := TPath.Combine(TPath.Combine(lDir, 'golden'), AName);
end;

function Normalize(const AText: string): string;
begin
  Result := TRegEx.Replace(AText, '\d{4}-\d\d-\d\d \d\d:\d\d:\d\d', '<timestamp>');
end;

procedure TReportCharacterization.BuildReport_MatchesGoldenMaster(const ACustomer: string);
var
  lExpected, lActual: TStringList;
  lFile: string;
begin
  lFile := GoldenFile('report.' + ACustomer + '.txt');
  lActual := TStringList.Create;
  try
    lActual.Text := BuildReport(ACustomer, 1234.5);
    if not TFile.Exists(lFile) then
    begin
      // First run: record what the code does today, then FAIL so an unreviewed master never goes green.
      lActual.SaveToFile(lFile, TEncoding.UTF8);
      Assert.Fail('Golden master created: ' + lFile + '. Review it, then run again.');
    end;
    lExpected := TStringList.Create;
    try
      lExpected.LoadFromFile(lFile, TEncoding.UTF8);
      Assert.AreEqual(lExpected, lActual, [TIMESTAMP_LINE]);
    finally
      lExpected.Free;
    end;
  finally
    lActual.Free;
  end;
end;

procedure TReportCharacterization.BuildReport_TimestampMovedButMasterStillMatches;
var
  lExpected, lActual: TStringList;
begin
  // Alternative when the volatile line is not at a fixed position: blank the value in both texts.
  lExpected := TStringList.Create;
  lActual := TStringList.Create;
  try
    lExpected.LoadFromFile(GoldenFile('report.ACME.txt'), TEncoding.UTF8);
    lActual.Text := BuildReport('ACME', 1234.5);
    Assert.NoDiff(Normalize(lExpected.Text), Normalize(lActual.Text));
  finally
    lActual.Free;
    lExpected.Free;
  end;
end;

end.
```

## 3. Volatile lines: three ways, best first

| Way | When | Notes |
|-----|------|-------|
| **Inject the source of the volatility** (an `IClock`, a seed) | you can change the code under test | exact, no special handling in the test (`reference/testable-code.md`) |
| `Assert.AreEqual(expected, actual, [LineNo])` | the volatile line is at a fixed position | `ignoreLines` is an `array of Integer` of **1-based** line numbers. The timestamp on the second line is `[2]`. `[1]` would compare line 2 and fail |
| normalise both texts, then `Assert.NoDiff` | the position varies, or the value sits inside a longer line | replace the value with a token (`TRegEx.Replace(..., '<timestamp>')`) in both golden and actual |

Several lines: `[2, 7, 9]`. A line you ignore is ignored in full, including a real change on that line: keep the
ignored set as small as possible.

What the comparison does (verified):

- the **line count is checked first**: `Number of strings is not equal: Expected [2] but got [1]`;
- each remaining line is compared with `NoDiff`: **case-sensitive**, a failure reads
  `Difference at position 13: ['1234.05'] does not match ['1234.50'] at line 4`;
- `Assert.AreEqual(expected, actual: string)` is the wrong tool for text: it is case-insensitive by default
  (`reference/assertions.md`). `Assert.NoDiff(expected, actual)` for one big string is case-sensitive;
- two `TStringList` compared with the generic `AreEqual<TObject>` are compared by reference and fail.

## 4. Failure output

```
Acme.Report.Tests.TReportCharacterization.BuildReport_MatchesGoldenMaster.Globex
Message: Difference at position 13: ['1234.05'] does not match ['1234.50'] at line 4
```

The window around the difference is 5 characters each side on 13; on 12 it is 10 characters forward from the
position (`reference/assertions.md`).

## 5. Pitfalls that make a master flaky

| Source of noise | Fix |
|-----------------|-----|
| `FormatDateTime`, `FloatToStr`, `CurrToStr`, `DateToStr` use the machine's locale | pass `TFormatSettings.Invariant` (the legacy sample does for the amount) or normalise |
| enumeration order of `TDictionary` / `THashSet` | sort the keys before writing them to the text |
| absolute paths, machine names, user names, process ids | normalise to a token |
| floating point output | format with a fixed number of decimals |
| GUIDs, random numbers | inject the generator or normalise |
| a golden file saved as ANSI on one machine, UTF-8 on another | always `LoadFromFile(file, TEncoding.UTF8)` / `SaveToFile(file, TEncoding.UTF8)`. `SaveToFile` with `TEncoding.UTF8` writes a BOM; `LoadFromFile` with the same encoding reads it back correctly |
| master created by one platform and compared on another | the master written by the Win64 build passed under Win32, 12 and 13 here; check your own outputs, especially floating point |

## 6. Big outputs

For a large document (XML, JSON, a text report) keep **one golden file per scenario** and name it after the
scenario (`[TestCase('Acme', 'ACME')]` above). When a scenario is large, assert it with `NoDiff` on the
whole string so the failure shows the first difference, and diff the golden file in your VCS to see the rest.
