# Error handling

Read this when: you catch FireDAC exceptions, branch on "duplicate key" / "table not found", or decode a
`[FireDAC]...-NNN` message.

Classes and enums are in `FireDAC.Stan.Error`. Runs on SQLite, Delphi 13 and 12; native error codes below
are SQLite's and differ on other servers.

## The classes

```
Exception
  EDatabaseError              (Data.DB)
    EFDException              FDCode: Integer, FDObjName
      EFDDBEngineException    the DBMS (or the driver library) rejected a statement
        ESQLiteNativeException   one per driver (SQLite here)
      EFDDBArrayExecuteError  carries ATimes / AOffset for array DML
```

- **FireDAC's own errors** are plain `EFDException`: `-308`, `-310`, `-312`, `-318`, `-335`, `-338`, `-507`,
  `-512`, `-708`, `-716`, `-218`. The number is in the message (`[FireDAC][Phys][SQLite]-308. ...`) and in
  `E.FDCode` as a **positive** value (`308`). These are programming or configuration errors; fix the code.
- **DBMS errors** are `EFDDBEngineException` (driver subclass). Catch this one to react to the data.
- `on E: EDatabaseError` catches both families.

```pascal
type
  EDuplicate = class(Exception);   // your own classes
  EInUse = class(Exception);

try
  C.ExecSQL('insert into t(n) values(:n)', [Name]);
except
  on E: EFDDBEngineException do
    case E.Kind of
      ekUKViolated:  raise EDuplicate.Create('already exists');
      ekFKViolated:  raise EInUse.Create('referenced elsewhere');
      ekObjNotExists: raise;
    else
      raise;
    end;
end;
```

The snippet compiled and ran (duplicate branch). The `Kind` values were checked as in the table below.

## EFDDBEngineException members

| Member                  | Meaning (run on a unique-key violation)                       |
|-------------------------|---------------------------------------------------------------|
| `E.Kind`                | `TFDCommandExceptionKind` of the first error: `ekUKViolated`  |
| `E.ErrorCode`           | native DBMS code: `2067` (SQLite constraint-unique)           |
| `E.ErrorCount`, `E.Errors[i]` | the list; `Errors[i].Message`, `.ErrorCode`, `.Kind`, `.ObjName` (`t.n`), `.RowIndex`, `.CommandTextOffset` (`-1` when unknown), `.Level` |
| `E.SQL`                 | the command text, with `:v` markers                           |
| `E.Params`              | `TStrings`, `V=zz`: the bound values. **They can contain secrets: do not log them blindly.** |
| `E.Message`             | `[FireDAC][Phys][SQLite] ERROR: UNIQUE constraint failed: t.n` |

## Kind values

`TFDCommandExceptionKind = (ekOther, ekNoDataFound, ekTooManyRows, ekRecordLocked, ekUKViolated,
ekFKViolated, ekObjNotExists, ekUserPwdInvalid, ekUserPwdExpired, ekUserPwdWillExpire, ekCmdAborted,
ekServerGone, ekServerOutput, ekArrExecMalfunc, ekInvalidParams)`.

What SQLite returned (the only server tested):

| Situation                               | `Kind`            | native `ErrorCode` |
|-----------------------------------------|-------------------|--------------------|
| duplicate in a `unique` column          | `ekUKViolated`    | 2067               |
| insert violating a foreign key        | `ekFKViolated`    | 787                |
| `select * from nosuch`                  | `ekObjNotExists`  | 1                  |
| syntax error (`selec 1`)                | `ekOther`         | 1                  |
| `NOT NULL` violation                    | **`ekOther`**     | 1299               |

Do not assume `Kind` covers every constraint: `NOT NULL` and syntax errors both came back as `ekOther`.
For those, test `E.ErrorCode` (driver specific) or the message. The other members (`ekRecordLocked`,
`ekServerGone`, ...) need a server that produces them; not exercised.

FireDAC's SQLite driver enforced foreign keys with no pragma set (ran); it has a `ForeignKeys`
connection parameter.

## Errors that are really your code

| Message                                                            | Cause                                    |
|--------------------------------------------------------------------|------------------------------------------|
| `-308 Cannot open / define command, which does not return result sets` | `Open` on INSERT/UPDATE (it ran first!) |
| `-310 Cannot execute command returning result sets`                | `ExecSQL` on SELECT                       |
| `-335 Parameter [X] data type is unknown`                          | `Clear`/NULL on an untyped parameter     |
| `-338 Param [X] type changed from [A] to [B]`                      | same SQL, different type; re-prepare or keep types |
| `-507 Connection ... cannot be pooled`                             | `Pooled` on a private connection or extra `Params` |
| `-708 Cannot acquire item (connection) from pool`                  | pool exhausted, no waiting               |
| `-312 Exact fetch returned [N] rows, while [M] was requested`      | `fmExactRecsMax` with more rows          |
| `-318 Transaction ... must be inactive. Nested transactions are disabled` | `EnableNested := False` and second `StartTransaction` |
| `-218 Cannot turn off cached updates mode`                         | `CachedUpdates := False` with pending changes |
| `-512 Connection is not defined`                                   | dataset without `Connection`             |
| `-716 Unknown storage format [BIN]`                                | missing `FireDAC.Stan.StorageBin`        |

## Handling in a thread or a service

Exceptions are ordinary Delphi exceptions: catch them inside `TThread.Execute` (see the `delphi` skill,
threading). In a service, set `FDManager.SilentMode := True` (see `uses-and-drivers.md`).
