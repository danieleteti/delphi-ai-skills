---
name: delphi-firedac
description: Use when writing or fixing plain Delphi code that talks to a database through FireDAC (VCL, FMX, console, service), with no web framework. Covers TFDConnection, connection definitions and pooling, transactions, TFDQuery/TFDCommand/TFDStoredProc, parameters and macros, fetching and RecordCount, array DML, cached updates and ApplyUpdates, EFDDBEngineException, threading, the uses clause per driver, and porting a BDE/ADO/dbExpress app. Triggers on "FireDAC", "TFDConnection", "TFDQuery", "ExecSQL", "ApplyUpdates", "connection pooling", "RecordCount", "array DML", "BDE migration", "Object factory for class".
---

# FireDAC in plain Delphi

For Delphi code that uses FireDAC directly: VCL, FMX, console, service, library. Not for
DelphiMVCFramework `TMVCActiveRecord` code: that has its own skills, start at `dmvcframework`.
Language and RTL questions (ownership, `try/finally`, threads): `delphi`.

Everything here was run on Delphi 13 (`dcc32` 37.0) and, unless a line says otherwise, gave the same
result on Delphi 12 (36.0). **Every run used the SQLite driver** (in-memory or file). Lines marked
"SQLite only" may differ on other servers; "not verified" means exactly that.

## Critical rules

1. **A missing FireDAC unit is a run-time error, not a compile error.** The program builds, then the first
   `Open` raises `Object factory for class {...} is missing ... include unit [FireDAC.X]`. The message names
   the unit. A code-only program needs `FireDAC.Stan.Def`, `FireDAC.Stan.Async`, `FireDAC.DApt`, a driver
   unit, `FireDAC.Comp.Client`. Table below, details in `reference/uses-and-drivers.md`.
2. **`Close`, `Free` or a pooled `Close` with an open transaction COMMITS.** `TxOptions.DisconnectAction`
   defaults to `xdCommit`; `Isolation` defaults to `xiUnspecified`. An exception does not end the
   transaction. Use `try ... Commit except Rollback; raise end`. For the opposite default set
   `DisconnectAction := xdRollback`.
3. **Pooling needs a named connection definition**, with `Pooled=True` inside the definition and nothing else
   on the component. `Params.Pooled := True` on a private connection raises `-507`. When the pool is full
   the next `Open` raises `-708` at once; it does not wait. Defaults: `POOL_MaximumItems=50`,
   `POOL_CleanupTimeout=30000`, `POOL_ExpireTimeout=90000`. Add `FireDAC.Stan.Pool` to `uses`.
4. **`RecordCount` right after `Open` is 50, not the row count.** Default `RecordCountMode = cmVisible`,
   `Mode = fmOnDemand`, `RowsetSize = 50`. Count with `select count(*)`; never size a loop with it.
5. **`ApplyUpdates` returns the number of FAILED rows and does not raise.** It is not atomic. With the default
   `AutoCommitUpdates = False` a second `ApplyUpdates` sends the inserts again (duplicate rows). Call
   `CommitUpdates` after success. `Connection.ApplyUpdates([...])` is deprecated.
6. **Array DML is `Q.Execute(ATimes, AOffset)`.** `Q.ExecSQL(5, 0)` does not compile; `Execute` with no
   arguments inserts ONE row and says nothing.
7. **Ownership.** `Param.AsStream := S` hands `S` to the parameter (freeing it yourself is a double free).
   `LoadFromStream` copies, you free. `C.ExecSQL(sql, RS)` returns an **open `TFDQuery` you must free**.
8. **Macros eat text.** `&` and `!` inside SQL start a macro even in a quoted literal: `select 'R&B'` returns
   `R`. `!name` is pasted raw: injection. Values go in parameters; macros only for identifiers you control.
   Turn it off with `ResourceOptions.MacroCreate := False; MacroExpand := False` before assigning the SQL.
9. **`Open` is for SELECT, `ExecSQL` for everything else.** The wrong one raises (`-308` / `-310`), and
   `Open` on an INSERT runs the INSERT first.
10. **NULL needs a type.** `ParamByName('x').Clear` on a fresh parameter raises `-335`; set `DataType` first.
11. **One `TFDConnection` per thread.** Share the connection definition (pooled), not the connection object.
12. **The `OnExecuteError` event is `procedure of object`.** No anonymous method.
13. **Non-console, non-VCL programs** (services) must call `FDManager.SilentMode := True`, or include a wait
    unit, or the first `Open` fails with the `TFDGUIxWaitCursor` factory error.

## Skeleton: console program, compiled and run

```pascal
program FdDemo;
{$APPTYPE CONSOLE}
uses
  System.SysUtils, Data.DB,
  FireDAC.Stan.Def, FireDAC.Stan.Async, FireDAC.DApt, FireDAC.Phys.SQLite,
  FireDAC.Comp.Client;

var
  C: TFDConnection;
  Q: TFDQuery;
begin
  C := TFDConnection.Create(nil);
  try
    C.DriverName := 'SQLite';
    C.Params.Database := ':memory:';
    C.Open;
    C.ExecSQL('create table t(id integer primary key, n text)');
    C.ExecSQL('insert into t(n) values(:n)', ['alpha']);     // array of Variant
    Q := TFDQuery.Create(nil);
    try
      Q.Connection := C;
      Q.SQL.Text := 'select * from t where n = :n';
      Q.ParamByName('n').AsString := 'alpha';
      Q.Open;
      while not Q.Eof do
      begin
        Writeln(Q.FieldByName('id').AsInteger, ' ', Q.FieldByName('n').AsString);
        Q.Next;
      end;
    finally
      Q.Free;
    end;
  finally
    C.Free;
  end;
end.
```

For a VCL form add `FireDAC.VCLUI.Wait` (FMX: `FireDAC.FMXUI.Wait`, compiled only). In the IDE, dropping the
components adds the units for you; that is why the same code "works on the form" and fails in a console.

## Which unit declares what

| Identifier                                                        | Unit                     |
|-------------------------------------------------------------------|--------------------------|
| `TFDConnection`, `TFDQuery`, `TFDCommand`, `TFDStoredProc`, `TFDTransaction`, `TFDMemTable`, `TFDTable`, `TFDUpdateSQL`, `FDManager` | `FireDAC.Comp.Client` |
| `TFDDataSet`, `rtInserted` / `rtModified` / `rtDeleted` / `rtUnmodified` | `FireDAC.Comp.DataSet` |
| `TFDParam`, `TFDParams`, `TFDMacro`, `mdRaw`, `mdIdentifier`      | `FireDAC.Stan.Param`     |
| `fmAll`, `cmTotal`, `xdCommit`, `xdRollback`, `xiReadCommitted`   | `FireDAC.Stan.Option`    |
| `TFDErrorAction`, `eaSkip`, `eaFail`                              | `FireDAC.Stan.Intf`      |
| `EFDException`, `EFDDBEngineException`, `ekUKViolated`            | `FireDAC.Stan.Error`     |
| `TFDGUIxWaitCursor` (component only)                              | `FireDAC.Comp.UI`        |
| driver: `SQLite`, `MySQL`, `PG`, `MSSQL`, `Ora`, `FB`, `IB`, `MSAcc`, `ODBC` | `FireDAC.Phys.<Name>` (`Ora` is `FireDAC.Phys.Oracle`) |

## Reference index

| Open this                                | When                                                                                   |
|------------------------------------------|----------------------------------------------------------------------------------------|
| `reference/uses-and-drivers.md`          | `Object factory ... is missing`; `uses` for a driver, console, service, VCL, FMX; wait cursor; storage units |
| `reference/connections-and-threads.md`   | connection definitions, pooling parameters and exhaustion, threads                      |
| `reference/transactions.md`              | `StartTransaction`/`Commit`/`Rollback`, defaults, nested, `AutoCommit`                  |
| `reference/commands-params-macros.md`    | `Open` vs `ExecSQL`, parameter types and NULL, streams, macros and the `&`/`!` rules    |
| `reference/fetching-and-bulk.md`         | `RecordCount`, `FetchOptions`, array DML, `Connection.ExecSQL` with a result set        |
| `reference/cached-updates.md`            | `CachedUpdates`, `ApplyUpdates`, `CommitUpdates`, duplicates after a second apply       |
| `reference/errors.md`                    | `EFDDBEngineException`, `Kind`, decoding `-NNN` messages                                |
| `reference/migration.md`                 | porting BDE / ADO / dbExpress code: what compiles, what changes silently, migrate units |

## Not verified

- Every driver except SQLite (client libraries, native array DML, nested transactions, `AutoCommit = False`,
  `Kind` values other than the five tested, stored procedures, `LoginPrompt`).
- `FireDAC.FMXUI.Wait` in a real FMX application; `TFDSchemaAdapter`; `TFDScript`; async execution modes.
- Several independent transactions on one connection (`TFDTransaction`).
- Sharing one connection across threads: treated as unsupported on source evidence only.

When something here is silent, read the unit under `C:\Program Files (x86)\Embarcadero\Studio\<n>.0\source\data\firedac\`
(37 = Delphi 13, 23 = Delphi 12) and write a 20-line console program on SQLite before answering.
