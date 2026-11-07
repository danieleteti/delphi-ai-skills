# Delphi — which unit declares what

A missing `uses` is the most common compile error, and the message is no help: `E2003 Undeclared
identifier: 'TStringList'`. Find the unit here, add it, move on.

How this table was made: each identifier was looked up by name in the declaring unit's source, in **both**
the `Studio\37.0\source` tree (13 Florence) and the `Studio\23.0\source` tree (12 Athens). Every row is the
same unit in both trees. The 22.0 tree (11 Alexandria) was **not installed** when this was written, so
nothing below is confirmed for 11 — for a symbol that matters, open its unit in the tree you build with
(see `SKILL.md`, *When in doubt about an API*). Version-gated types (`THashSet<T>`, `TOrderedDictionary<K,V>`,
and the 13-only language features) are listed in `SKILL.md`, not here.

---

## Traps — same name, two units, or a helper you cannot see

| Trap | What happens |
|------|--------------|
| `TStringList` is in `System.Classes`, not `System.SysUtils` | `E2003 Undeclared identifier` |
| A **helper** is invisible until its unit is in `uses`. `c.IsLetter` on a `Char` needs `System.Character`; without it the compiler says `E2671 Record, object, class type, or type helper required` | add `System.Character`. (`s.Trim`, `s.Split` on a `string` come from `System.SysUtils`, which nearly every unit already uses) |
| `TObjectList`, `TQueue`, `TStack` exist **twice**: generic in `System.Generics.Collections`, pre-generics in `System.Contnrs`. `TList` too: generic in `System.Generics.Collections`, plain pointer list in `System.Classes` | `TObjectList<TFoo>` needs the generics unit; a stray `System.Contnrs` in `uses` gives you the other one |
| `IfThen` exists in `System.StrUtils` (strings) **and** `System.Math` (numbers) | with both in `uses`, the overload is chosen by argument type (compiled: `IfThen(True, 'a', 'b')` and `IfThen(False, 1, 2)`) |
| `CreateOleObject` exists in `System.Win.ComObj` (returns `IDispatch`) **and** `Vcl.OleAuto` (returns `Variant`). `Vcl.OleAuto` is declared `unit Vcl.OleAuto deprecated;` | listing it gives `W1006 Unit 'Vcl.OleAuto' is deprecated` (seen on 12 and 13). Use `System.Win.ComObj` |
| `TMessage` in `Winapi.Messages` is the Windows message record (`Msg`, `WParam`, `LParam`, `Result`). `System.Messaging` declares an unrelated `TMessage` for publish/subscribe | wrong unit: a message handler that "has no field WParam" |
| `StrLen`, `StrPas`, `StrPCopy`, `StrComp` for `PAnsiChar` live in `System.AnsiStrings`; the `System.SysUtils` copies are `deprecated 'Moved to the AnsiStrings unit'` | `W1000`. Same names exist for `PWideChar` in `System.SysUtils`, which is what `PChar` code wants |
| `TCriticalSection` is in `System.SyncObjs`, not `System.Classes` | `E2003` |
| `TJson` (`ObjectToJsonString`, `JsonToObject`) is in `REST.Json`, **not** `System.JSON`. Its source is under `source\data\rest`, not `source\rtl` | `System.JSON` has the DOM: `TJSONObject`, `TJSONArray`, `TJSONValue` |
| `Sleep` is declared in `System.SysUtils` and in `Winapi.Windows` | a console program that uses only `System.SysUtils` can call it (compiled) |

---

## Core language, strings, numbers

| Unit | Declares |
|------|----------|
| `System` (implicit) | `TObject`, `IInterface`, `TInterfacedObject`, `TNoRefCountObject`, `TCustomAttribute`, `TMonitor`, `TGUID`, `TMarshal`, `TVarRec`, `THandle`, `Move`, `UTF8Encode`, `UTF8ToString`, `WideCharToString`, `StringToWideChar`, `ParamStr`, `Randomize` |
| `System.SysUtils` | `Exception`, `EConvertError`, `FreeAndNil`, `Format`, `Supports`, `TEncoding`, `TStringBuilder`, `TStringHelper`, `TFormatSettings`, `TBytes`, `TProc`, `TFunc`, `TPredicate`, `TOSVersion`, `TStringSplitOptions`, `TReplaceFlag`, `CharInSet`, `ByteLength`, `CreateGUID`, `IntToHex`, `TryStrToInt`, `StrToIntDef`, `StrToFloat`, `StringReplace`, `SameText`, `CompareText`, `UpperCase`, `LowerCase`, `FormatDateTime`, `IncMonth`, `Now`, `Sleep`, `FileExists`, `DirectoryExists`, `ForceDirectories`, `ExtractFilePath`, `ExtractFileName`, `ChangeFileExt`, `IncludeTrailingPathDelimiter`, `GetEnvironmentVariable`, `Win32Check`, `RaiseLastOSError` |
| `System.AnsiStrings` | the `AnsiString` / `PAnsiChar` overloads of `StrLen`, `StrPas`, `StrPCopy`, `StrComp`, `SameText`, `ContainsText`, `StringReplace`, `ExtractFilePath` |
| `System.StrUtils` | `SplitString`, `ContainsText`, `StartsText`, `MatchStr`, `IndexStr`, `IfThen` (string overload) |
| `System.Character` | `TCharacter`, `TCharHelper` (`IsLetter`, `IsDigit`, …) |
| `System.Math` | `InRange`, `EnsureRange`, `SameValue`, `RandomRange`, `IfThen` (numeric overloads) |
| `System.Variants` | `VarToStr`, `VarIsNull`, `VarIsEmpty` |
| `System.Types` | `TRect`, `TPoint`, `TStringDynArray`, `TBitConverter` |
| `System.UITypes` | `TAlphaColor`, `TMsgDlgType`, `TMsgDlgBtn`, `mrOk` |

## Time, files, text, hashing, JSON, regex, network

| Unit | Declares |
|------|----------|
| `System.DateUtils` | `TTimeZone`, `TDateTimeHelper`, `IncYear`, `DaysBetween`, `DateToISO8601`, `ISO8601ToDate` |
| `System.Diagnostics` | `TStopwatch` |
| `System.TimeSpan` | `TTimeSpan` |
| `System.IOUtils` | `TFile`, `TPath`, `TDirectory` |
| `System.IniFiles` | `TIniFile`, `TMemIniFile` |
| `System.Zip` | `TZipFile` |
| `System.ZLib` | `TZCompressionStream`, `TZDecompressionStream` |
| `System.Hash` | `THashSHA2`, `THashSHA1`, `THashMD5`, `THashBobJenkins` |
| `System.NetEncoding` | `TNetEncoding`, `TBase64Encoding` |
| `System.RegularExpressions` | `TRegEx`, `TMatch`, `TMatchCollection`, `TGroup` |
| `System.JSON` | `TJSONValue`, `TJSONObject`, `TJSONArray`, `TJSONString` |
| `System.JSON.Serializers` | `TJsonSerializer` |
| `System.JSON.Readers` | `TJsonTextReader` |
| `REST.Json` | `TJson` |
| `System.Net.HttpClient` | `THTTPClient` |
| `System.Net.URLClient` | `TURI` |

## Classes, collections, threads, RTTI

| Unit | Declares |
|------|----------|
| `System.Classes` | `TStringList`, `TStrings`, `TStream`, `TMemoryStream`, `TFileStream`, `TStringStream`, `TBytesStream`, `TResourceStream`, `TStreamReader`, `TStreamWriter`, `TBinaryReader`, `TBinaryWriter`, `TTextReader`, `TTextWriter`, `TComponent`, `TPersistent`, `TCollection`, `TCollectionItem`, `TNotifyEvent`, `TThread`, `TThreadList`, `TList` (non-generic), `TBits` |
| `System.Generics.Collections` | `TList<T>`, `TObjectList<T>`, `TDictionary<K,V>`, `TObjectDictionary<K,V>`, `TQueue<T>`, `TStack<T>`, `THashSet<T>`, `TObjectHashSet<T>`, `TOrderedDictionary<K,V>`, `TThreadedQueue<T>`, `TPair<K,V>`, `TEnumerable<T>`, `TArray` (the static helpers: `Sort`, `BinarySearch`, …) |
| `System.Generics.Defaults` | `IComparer<T>`, `IEqualityComparer<T>`, `TComparer<T>`, `TDelegatedComparer<T>`, `TStringComparer` |
| `System.Contnrs` | the pre-generics `TObjectList`, `TQueue`, `TStack` |
| `System.SyncObjs` | `TCriticalSection`, `TEvent`, `TMutex`, `TSemaphore`, `TInterlocked`, `TSpinLock`, `TCountdownEvent`, `TLightweightMREW` |
| `System.Threading` | `TTask`, `ITask`, `IFuture<T>`, `TParallel`, `TThreadPool` |
| `System.Rtti` | `TRttiContext`, `TValue`, `TVirtualMethodInterceptor` |

## VCL, Windows API, COM

| Unit | Declares |
|------|----------|
| `Vcl.Forms` | `Application`, `TForm` |
| `Vcl.Dialogs` | `ShowMessage`, `MessageDlg` |
| `Vcl.ExtCtrls` | `TTimer` |
| `Vcl.Graphics` | `TColor` |
| `Winapi.Windows` | `HWND`, `WPARAM`, `LPARAM`, `LRESULT`, `LONG_PTR`, `DWORD_PTR`, `SetWindowLong`, `GetWindowLong`, `SetWindowLongPtr`, `GetWindowLongPtr`, `GWL_USERDATA`, `GWLP_USERDATA`, `GWL_WNDPROC`, `OutputDebugString` |
| `Winapi.Messages` | `TMessage`, `TWMKey` |
| `Winapi.ShellAPI` | `ShellExecute` |
| `Winapi.ActiveX` | `CoInitialize` |
| `System.Win.ComObj` | `CreateOleObject` (returns `IDispatch`) |
| `Vcl.OleAuto` | `CreateOleObject` (returns `Variant`) |
| `System.Win.Registry` | `TRegistry`, `TRegistryIniFile` |

## Data access

| Unit | Declares |
|------|----------|
| `Data.DB` | `TDataSet`, `TField`, `TDataSource` |
| `Datasnap.DBClient` | `TClientDataSet` |
| `Datasnap.Provider` | `TDataSetProvider` |
| `SimpleDS` | `TSimpleDataSet` |
| `Data.Win.ADODB` | `TADOConnection`, `TADOQuery`, `TADOTable`, `TADOCommand`, `TADODataSet`, `TADOStoredProc` |
| `Data.SqlExpr` | `TSQLConnection`, `TSQLQuery`, `TSQLDataSet`, `TSQLStoredProc`, `TSQLTable` |
| `FireDAC.Comp.Client` | `TFDConnection`, `TFDQuery`, `TFDTable`, `TFDStoredProc`, `TFDCommand`, `TFDUpdateSQL`, `TFDMemTable`, `TFDTransaction`, `TFDManager`, `TFDMetaInfoQuery` |
| `FireDAC.Comp.BatchMove` | `TFDBatchMove` |
| `FireDAC.Comp.Script` | `TFDScript` |
| `FireDAC.Comp.UI` | `TFDGUIxWaitCursor` |

A FireDAC program also needs the driver and wait-cursor units in `uses`; the compiling example in
`reference/legacy-migration.md` (§ *From BDE, ADO and dbExpress to FireDAC*) lists a set that builds.
