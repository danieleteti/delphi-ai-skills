# Fetching, RecordCount, array DML, result sets

Read this when: you read `RecordCount`, tune fetching, insert many rows in one call, or call
`Connection.ExecSQL` with a result set.

SQLite, Delphi 13 and 12: same output unless stated. A table `t` of 1000 rows, `select * from t`.

## FetchOptions defaults

`TFDFetchMode = (fmManual, fmOnDemand, fmAll, fmExactRecsMax)`,
`TFDRecordCountMode = (cmVisible, cmFetched, cmTotal)`; both in `FireDAC.Stan.Option`.

| Option                         | Default      |
|--------------------------------|--------------|
| `Mode`                         | `fmOnDemand` |
| `RowsetSize`                   | `50`         |
| `RecordCountMode`              | `cmVisible`  |
| `RecsMax`                      | `-1` (no limit) |
| `AutoClose`                    | `True`       |
| `Unidirectional`               | `False`      |

## The RecordCount trap

`Q.Open; Q.RecordCount` returned **50**, not 1000. With `cmVisible` it counts the rows fetched so far, and
`fmOnDemand` fetches `RowsetSize` rows per round trip.

| What you do                                   | `RecordCount` right after |
|-----------------------------------------------|---------------------------|
| default `Open`                                | 50                        |
| `Open; Last` (fetches all)                    | 1000                      |
| `FetchOptions.RecordCountMode := cmTotal`     | 1000 (FireDAC asks the server for the total, costs a count query) |
| `FetchOptions.Mode := fmAll`                  | 1000 (fetches everything on `Open`) |
| `FetchOptions.RowsetSize := 200`              | 200                       |
| `Mode := fmManual`                            | 0, `Eof` True; `FetchNext` returned 50; `FetchAll` -> 1000 |
| loop `while not Eof do Next`, then read       | 1000                      |
| closed dataset                                | 0                         |

Rules: do not use `RecordCount` to decide "is there data" or to size a loop in the default mode. For a
real count use `select count(*)` (`ExecSQLScalar`). For "is there a row" use `not Q.IsEmpty` or `Eof`.
`cmTotal` re-runs the query as a count on the server; avoid on expensive queries.

`RecsMax := 10` with the default mode: 10 rows, also after `Last`. `Mode := fmExactRecsMax` with
`RecsMax := 10` on a query that has more rows **raised** `-312. Exact fetch returned [11] rows, while [10]
was requested`. It is for single-row lookups, not for "limit to N": use `RecsMax` or `limit` in SQL.

`FetchOptions.Unidirectional := True`: `Q.Last` raised `EDatabaseError: Operation not allowed on a
unidirectional dataset`.

## Array DML

One round trip, many rows. The method is `TFDQuery.Execute(ATimes, AOffset)`, declared in `TFDDataSet`
(`procedure Execute(ATimes: Integer = 0; AOffset: Integer = 0)`). There is **no** `ExecSQL(ATimes, AOffset)`:
`Q.ExecSQL(3, 0)` fails to compile (`E2250 no overloaded version`).

```pascal
Q.SQL.Text := 'insert into t(n) values(:n)';
Q.Params.ArraySize := 5;
for i := 0 to 4 do
  Q.Params[0].AsStrings[i] := 'v' + IntToStr(i);
Q.Execute(5, 0);                 // ATimes = 5 (exclusive end), AOffset = 0 (first element)
n := Q.RowsAffected;             // 5
```

| Call               | Rows inserted (`ArraySize = 5`) |
|--------------------|---------------------------------|
| `Execute(5, 0)`    | 5                               |
| `Execute(3, 0)`    | 3                               |
| `Execute(5, 2)`    | 3 (elements 2..4)               |
| `Execute` / `ExecSQL` (no arguments) | **1**: only the first element, no error |

`ATimes` is the exclusive end index, `AOffset` the first element. Forgetting the arguments silently
inserts one row.

### A bad row in the batch

Without a handler the driver exception (`ESQLiteNativeException`, a descendant of `EFDDBEngineException`)
is raised; rows before the failing one stay inserted. To skip bad rows, assign `OnExecuteError`:

```pascal
type
  TBatchHandler = class
    procedure OnExecuteError(ASender: TObject; ATimes, AOffset: LongInt;
      AError: EFDDBEngineException; var AAction: TFDErrorAction);
  end;

procedure TBatchHandler.OnExecuteError(ASender: TObject; ATimes, AOffset: LongInt;
  AError: EFDDBEngineException; var AAction: TFDErrorAction);
begin
  if AError.Kind = ekUKViolated then
    AAction := eaSkip              // skip row AOffset, continue with the next
  else
    AAction := eaFail;
end;
```

`TFDExecuteErrorEvent` is `procedure of object` (`FireDAC.Comp.Client`): a method of a class, not an
anonymous method (`E2010 incompatible types`). Wire it with `Q.OnExecuteError := Handler.OnExecuteError`.

Run: `ArraySize = 4`, duplicate at index 1: handler called once with `AOffset = 1`, `Kind = ekUKViolated`,
and 3 rows inserted (`RowsAffected = 3`). `AAction` is `TFDErrorAction` (`FireDAC.Stan.Intf`); `eaSkip`
continues, `eaFail` and the default re-raise (source `FireDAC.Phys` array loop).

Version difference seen: the `ATimes` argument passed to the handler was **4 on Delphi 13 and 2 on
Delphi 12** for the same batch; `AOffset` was 1 on both. Identify the bad row with `AOffset`, ignore
`ATimes`.

After `eaSkip`, `RowsAffected` counts only the rows that went in. Without a handler the rows before the
failing one stayed inserted (ran): wrap the batch in `StartTransaction` / `Rollback` if you need
all-or-nothing. Native array execution versus row-by-row emulation per driver: not checked (SQLite only).

## Result sets from Connection.ExecSQL

```pascal
var
  RS: TDataSet;
begin
  C.ExecSQL('select * from t where id < 4', RS);
  try
    while not RS.Eof do ... ;
  finally
    RS.Free;                       // you own it
  end;
end;
```

`TFDCustomConnection.ExecSQL(ASQL, var AResultSet: TDataSet)` (and the overload with `AParams`) creates
`TFDQuery.Create(nil)` (no owner), assigns it to `AResultSet` and **opens it**. The returned value is that
query's `RecordCount`, not rows affected. Run: class `TFDQuery`, `Owner = nil`, `Active = True`,
`RecordCount = 3`; `RS.Free` left no leak report. Because the dataset has no owner, nothing frees it for
you. Passing a non-SELECT with this overload: not tested.
