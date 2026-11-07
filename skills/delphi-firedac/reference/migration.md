# Moving a BDE / ADO / dbExpress dataset app to FireDAC

Read this when: you port a project that uses `TQuery`/`TTable`, `TADOQuery`, or `TSQLQuery` and want to
know what recompiles and what silently changes behaviour. Concept level: it does not convert a project.

Method: each right-hand name below was compiled against a `TFDQuery` / `TFDConnection` / `TFDTable` /
`TFDStoredProc` on Delphi 13 (`dcc32` 37.0). The old BDE/ADO/dbExpress classes were not compiled; their
member names in the left column are the ones a ported app typically uses.

## What compiles unchanged

`TFDQuery`, `TFDTable`, `TFDStoredProc` are `TDataSet` descendants. Dataset-level code compiles as is:
`FieldByName`, `Fields`, `Locate`, `Lookup`, `Filter` / `Filtered`, `IndexFieldNames`, `MasterSource`,
`Refresh`, `Append/Edit/Post/Delete`, data-aware controls. Also compiled on `TFDQuery`: `ParamByName`,
`Params.ParamByName`, `Params[0].Value`, `Prepare`, `Prepared`, `CachedUpdates`, `ApplyUpdates`,
`CommitUpdates`, `CancelUpdates`, `UpdatesPending`, `UpdateObject` (a `TFDUpdateSQL`), `RowsAffected`,
`ExecSQL`, `Open(sql)`. On `TFDTable`: `TableName`, `IndexName`, `SetRange`, `FindKey`, `Locate`,
`CreateTable`, `Exists`. On `TFDStoredProc`: `StoredProcName`, `ExecProc`, `Prepare`, `Params[0].ParamType`.
On `TFDConnection`: `StartTransaction`, `Commit`, `Rollback`, `InTransaction`, `Connected`, `Close`,
`LoginPrompt`, `Ping`, `DriverName`, `Params.Values['Database']`, `ConnectionString`, `GetFieldNames`,
`GetTableNames(Catalog, Schema, Pattern, List)`.

## What does not compile, and the FireDAC name

| Old code                                   | Result on FireDAC                        | Use                                                  |
|--------------------------------------------|------------------------------------------|------------------------------------------------------|
| `Q.DatabaseName := 'alias'` (BDE)          | undeclared                               | `Q.Connection := C` (a `TFDConnection`)              |
| `Q.SessionName` (BDE)                      | undeclared                               | none; `FDManager` is global                          |
| `Q.RequestLive := True` (BDE)              | undeclared                               | `CachedUpdates` (see `cached-updates.md`); non-cached `Post` writes at once |
| `Q.UniDirectional := True` (BDE)           | undeclared                               | `Q.FetchOptions.Unidirectional := True`              |
| `Q.Parameters.ParamByName` (ADO)           | undeclared                               | `Q.Params.ParamByName` / `Q.ParamByName`             |
| `Q.CommandTimeout` (ADO)                   | undeclared                               | `Q.ResourceOptions.CmdExecTimeout` (unit not checked) |
| `Q.LockType`, `Q.CursorType` (ADO)         | undeclared                               | no equivalent checked; read `FetchOptions` / `UpdateOptions` |
| `Q.MaxRows` (dbExpress)                    | undeclared                               | `Q.FetchOptions.RecsMax`                             |
| `Q.SQLConnection` (dbExpress)              | undeclared                               | `Q.Connection`                                       |
| `C.KeepConnection` (BDE)                   | undeclared                               | pooling: `reference/connections-and-threads.md`      |
| `C.BeginTrans` / `C.CommitTrans` (ADO)     | undeclared                               | `StartTransaction` / `Commit`                        |
| `C.Execute(sql, n)` (ADO)                  | undeclared                               | `n := C.ExecSQL(sql)`                                |
| `C.StartTransaction(TD)` (dbExpress)       | `E2034 Too many actual parameters`       | `C.StartTransaction`; isolation via `C.TxOptions.Isolation` |
| `T.EmptyTable` (BDE)                       | undeclared                               | `ExecSQL('delete from ...')`                         |
| `Q.ExecSQL(Times, Offset)`                 | `E2250 no overloaded version`            | `Q.Execute(Times, Offset)` (array DML)               |

## Migration helper units (shipped, deprecated)

The source tree ships class helpers that re-add old names and mark each `deprecated` with the new call:

| Unit                  | Adds                                                                                 |
|-----------------------|--------------------------------------------------------------------------------------|
| `FireDAC.ADO.Migrate` | `TFDParams.AddParameter/CreateParameter`; on connection `Execute(CommandText, var RecordsAffected)`, `GetTableNames(List, SystemTables)`, `GetFieldNames(TableName, List)`, `ConnectionTimeout`; on datasets `UpdateBatch`, `CancelBatch`, `Seek`, `Sort`, `RecordStatus`, `Clone`, `DeleteRecords`, `EnableBCD`; `TFDCommand.Execute(Parameters)` |
| `FireDAC.DBX.Migrate` | `TFDDBXTransactionDesc`, `StartTransaction(TD)`, `BeginTransaction`, `CommitFreeAndNil`, `RollbackFreeAndNil`, `GetFieldNames(Table, Schema, List)`, `GetIndexNames`, dataset helpers |
| `FireDAC.IBX.Migrate` | exists in the source tree; not read here |

Verified by compile:

- With `FireDAC.ADO.Migrate` in `uses`: `C.Execute('x', n)` and `Q.UpdateBatch` compile, and
  `Q.Params.CreateParameter(...)` compiles.
- **`Q.Parameters` and `C.BeginTrans` still do not exist.** The helper does not cover them.
- **Only one class helper per class is active in a unit.** With both `FireDAC.ADO.Migrate` and
  `FireDAC.DBX.Migrate` in `uses`, the later one hid the other: `C.StartTransaction(TD)` compiled,
  `C.Execute(...)` did not. Port to the native calls instead of mixing the helpers.

`FireDAC.BDE.Import` (class `TFDBDEAliasImporter`) and `FireDAC.ADO.Import` (`TFDADOUDLImporter`) are
importers that turn BDE aliases / ADO connection strings and UDL files into FireDAC connection
definitions. They exist in the source; not run here.

## What compiles and then behaves differently

These are the dangerous ones: no compiler help.

| Old assumption                                          | FireDAC reality (see the named file)                                   |
|---------------------------------------------------------|------------------------------------------------------------------------|
| `RecordCount` is the total after `Open`                 | 50 in the default mode. `fetching-and-bulk.md`                         |
| Closing the connection discards an open transaction     | It commits by default (`DisconnectAction = xdCommit`). `transactions.md` |
| `ApplyUpdates` leaves nothing pending (ClientDataSet)   | `AutoCommitUpdates = False`: second apply duplicates inserts. `cached-updates.md` |
| `ApplyUpdates` raises on a rejected row                 | It returns the failure count. `cached-updates.md`                      |
| SQL text is sent as written                             | `&` and `!` start macros, even inside quoted text: `'R&B'` became `R`. `commands-params-macros.md` |
| `Open` on an INSERT just fails                          | The INSERT runs, then `Open` raises. `commands-params-macros.md`       |
| A NULL parameter needs no type                          | `Clear` on an untyped parameter raises `-335`                          |
| Pooling is a flag on the connection                     | Named definition only. `connections-and-threads.md`                    |
| Library units are linked by the units you use           | FireDAC units register services at start-up: missing ones fail at run time. `uses-and-drivers.md` |
| Connection string / alias carries over                  | Define a FireDAC connection definition (driver id plus parameters). A `ConnectionString` property compiles; its format with a non-FireDAC string was not tested. |
