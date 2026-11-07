# `uses` clause: which FireDAC unit for what

Read this when: a FireDAC program compiles but dies at run time with `Object factory for class {...} is
missing`, or a compile error says an identifier is undeclared.

Verified on Delphi 13 (`dcc32` 37.0) and Delphi 12 (`dcc32` 36.0): SQLite, in-memory and file databases.
Other drivers: the unit names compile, nothing was run against those servers.

## The trap: a missing unit is a RUN-TIME error

FireDAC creates its services by interface GUID through a factory table. Each `FireDAC.*` unit registers its
factory in its `initialization`. If nothing in the program names the unit, the code still compiles. The
failure appears on the first `Open`. The exception text names the unit to add, so the message is the fix:

| Run-time message (class `Exception`)                                          | Add to `uses`          |
|-------------------------------------------------------------------------------|------------------------|
| `Object factory for class {...A2015} is missing ... include unit [FireDAC.Stan.Def]`   | `FireDAC.Stan.Def`     |
| `... {...A2101} is missing ... drop component [TFDPhysXXXDriverLink]`         | the driver unit, e.g. `FireDAC.Phys.SQLite` |
| `... {...A2304} is missing ... include unit [FireDAC.DApt]`                   | `FireDAC.DApt`         |
| `... {...A2023} is missing ... include unit [FireDAC.Stan.Async]`             | `FireDAC.Stan.Async`   |
| `... {...A2003} is missing ... include unit [FireDAC.Stan.Pool]`              | `FireDAC.Stan.Pool` (only when a definition has `Pooled=True`) |
| `... {...A2201} is missing ... drop component [TFDGUIxWaitCursor]`            | a wait-cursor unit, see below |
| `[FireDAC][Stan]-716. Unknown storage format [BIN]`                           | `FireDAC.Stan.StorageBin` (for `SaveToStream/SaveToFile` with `sfBinary`) |

In the IDE, dropping a component on a form adds these units for you. Code-only programs (console,
service, a unit that creates components in code) do not get them. This is the usual reason a snippet
"works in the form but not in the console".

## Minimum for a non-visual program (SQLite)

```pascal
uses
  System.SysUtils, Data.DB,
  FireDAC.Stan.Def,        // connection definitions
  FireDAC.Stan.Async,      // command execution
  FireDAC.DApt,            // data adapter (SELECT/INSERT/UPDATE generation)
  FireDAC.Phys.SQLite,     // the driver
  FireDAC.Comp.Client;     // TFDConnection, TFDQuery, TFDCommand, TFDStoredProc, TFDMemTable, FDManager
```

Run: console program, `TFDConnection` with `DriverName := 'SQLite'`, `Params.Database := ':memory:'`, then
`Open`, `TFDQuery.Open('select 1')`. It printed `1`. Without `FireDAC.Stan.Pool` and without any `*UI*`
unit it works. Add `FireDAC.Stan.Pool` the moment you define a pooled connection definition.

## Which unit declares what (compile-time `uses`)

| You write                                                              | Unit                     |
|------------------------------------------------------------------------|--------------------------|
| `TFDConnection`, `TFDQuery`, `TFDCommand`, `TFDStoredProc`, `TFDTransaction`, `TFDMemTable`, `TFDTable`, `TFDUpdateSQL`, `TFDSchemaAdapter`, `FDManager`, `TFDExecuteErrorEvent` | `FireDAC.Comp.Client` |
| `TFDDataSet`, `TFDUpdateRecordType` (`rtInserted`...), `TFDUpdateRecordTypes` | `FireDAC.Comp.DataSet` |
| `TFDParams`, `TFDParam`, `TFDMacro`, `TFDMacroDataType` (`mdRaw`...)   | `FireDAC.Stan.Param`     |
| `TFDFetchMode` (`fmAll`...), `TFDRecordCountMode` (`cmTotal`...), `TFDTxAction` (`xdCommit`...), `TFDTxIsolation` (`xiReadCommitted`...), `TFDTxOptions`, `TFDFetchOptions`, `TFDUpdateOptions` | `FireDAC.Stan.Option` |
| `TFDErrorAction` (`eaSkip`...), `TFDStanAsyncMode`, `TFDRDBMSKind`     | `FireDAC.Stan.Intf`      |
| `EFDException`, `EFDDBEngineException`, `EFDDBArrayExecuteError`, `TFDCommandExceptionKind` (`ekUKViolated`...) | `FireDAC.Stan.Error` |
| `TFDScript`                                                            | `FireDAC.Comp.Script`    |
| `TFDBatchMove`                                                         | `FireDAC.Comp.BatchMove` |
| `TFDGUIxWaitCursor`, `TFDGUIxErrorDialog`, `TFDGUIxLoginDialog`        | `FireDAC.Comp.UI`        |
| `ftInteger`, `ftBlob`, `TDataSet`                                      | `Data.DB`                |
| `Null`                                                                 | `System.Variants`        |

A missing unit here is a normal `E2003 Undeclared identifier`. Copy the name, add the unit.

## Drivers

Driver id is the string for `TFDConnection.DriverName` / `FDManager.AddConnectionDef`. Source:
`S_FD_*Id` in `FireDAC.Stan.Consts`. The unit must be in `uses` (table above, row `A2101`).

| Driver id | Unit                | Driver id | Unit                |
|-----------|---------------------|-----------|---------------------|
| `SQLite`  | `FireDAC.Phys.SQLite` | `MSSQL` | `FireDAC.Phys.MSSQL` |
| `MySQL`   | `FireDAC.Phys.MySQL`  | `Ora`   | `FireDAC.Phys.Oracle` |
| `PG`      | `FireDAC.Phys.PG`     | `FB`    | `FireDAC.Phys.FB`    |
| `IB`      | `FireDAC.Phys.IB`     | `MSAcc` | `FireDAC.Phys.MSAcc` |
| `ODBC`    | `FireDAC.Phys.ODBC`   |         |                      |

All of these compiled together in one program. Not verified: the vendor client library each driver loads
(`libpq`, `libmysql`, `fbclient`, OCI, an ODBC driver). A missing client library is a different, run-time
connect error. Set it with the driver link component's `VendorLib` or the connection definition.

## Wait cursor and UI units

`Open`, `ExecSQL` and error paths ask for the "wait cursor" service unless FireDAC is in silent mode.
Rule from `FireDAC.UI.Intf`: silent when `IsConsole`, or when the call runs on a thread other than the main
thread. So:

| Program                                      | What to do                                                        |
|----------------------------------------------|-------------------------------------------------------------------|
| Console (`{$APPTYPE CONSOLE}`)               | Nothing. Verified: no UI unit needed.                              |
| Worker thread of any program                 | Nothing. Silent by thread check (source; the thread test ran in a console program). |
| VCL application                              | `FireDAC.VCLUI.Wait` in `uses`. Verified in a non-console exe.    |
| FMX application                              | `FireDAC.FMXUI.Wait`. Compiled only; not run in an FMX app. The provider is chosen by `GetClass('TFmxObject')`. |
| Windows service / GUI-subsystem exe with no forms | `IsConsole` is False, so not silent. Either `FDManager.SilentMode := True` before the first use (verified: works with no UI unit), or include `FireDAC.VCLUI.Wait`. Without both: `A2201` error on the first `Open`. |

`FireDAC.Comp.UI` is not needed for the wait cursor to work. It declares the components
`TFDGUIxWaitCursor`, `TFDGUIxErrorDialog`, `TFDGUIxLoginDialog`. `FireDAC.ConsoleUI.Wait` exists too (a
console wait cursor); not needed in a console program because it is silent.

`TFDConnection.LoginPrompt := True` asks for `IFDGUIxLoginDialog` (`FireDAC.VCLUI.Login` /
`FireDAC.FMXUI.Login`). Not verified at run time: SQLite never asked for credentials in my test.

## Storage formats

`FireDAC.Stan.StorageBin`, `FireDAC.Stan.StorageXML`, `FireDAC.Stan.StorageJSON` register the formats used by
`SaveToStream` / `LoadFromStream` / `SaveToFile`. Only `StorageBin` was run (error `-716` without it).
