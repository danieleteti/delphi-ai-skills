# Transactions

Read this when: you write `StartTransaction` / `Commit` / `Rollback`, wonder what happens on `Close`,
`Free` or an exception, or use cached updates inside a transaction.

Verified on SQLite (file database), Delphi 13 and 12, identical output. Items marked **SQLite only** may
differ on other servers.

## Defaults that matter

| Option (`TFDConnection.TxOptions`) | Default           | Consequence                                              |
|------------------------------------|-------------------|----------------------------------------------------------|
| `DisconnectAction`                 | `xdCommit`        | `Close`, `Free`, or a pooled `Close` with an open transaction **commits**. |
| `Isolation`                        | `xiUnspecified`   | The server default applies. Not `xiReadCommitted`.        |
| `AutoCommit`                       | `True`            | Each statement outside a transaction is committed.       |
| `EnableNested`                     | `True`            | A second `StartTransaction` nests.                       |
| `ReadOnly`                         | `False`           |                                                          |

`TFDTxAction = (xdNone, xdCommit, xdRollback)` and `TFDTxIsolation` are in `FireDAC.Stan.Option`.

Run: `StartTransaction; INSERT; Close; Open` -> the row is there. With `TxOptions.DisconnectAction :=
xdRollback` before `Close`, the row was gone. `Free` with an open transaction committed too.

An exception does not end the transaction. After a failing `ExecSQL` inside a transaction,
`C.InTransaction` was still `True`, and `Close` committed the rows that had succeeded before it. Always:

```pascal
C.StartTransaction;
try
  C.ExecSQL('insert into t(n) values(:n)', ['a']);
  C.ExecSQL('insert into t(n) values(:n)', ['b']);
  C.Commit;
except
  C.Rollback;
  raise;
end;
```

(Compiled and run.) Set `C.TxOptions.DisconnectAction := xdRollback` as a safety net if "forgot to
commit" must lose data rather than save it.

## What each call does (SQLite)

- `C.InTransaction` is `False` after a plain `ExecSQL`, `True` after `StartTransaction`.
- `Commit` or `Rollback` with **no** active transaction raised nothing. Do not rely on it to detect a
  mistake. **SQLite only.**
- **`TxOptions.AutoCommit := False` changed nothing on SQLite**: after `ExecSQL` `InTransaction` was
  `False`, another connection saw the row, and a following `Commit` failed with `cannot commit - no
  transaction is active`. In the source (`TFDPhysTransaction`) the behaviour depends on the driver's
  metadata (`TxAutoCommit`): drivers that start transactions implicitly use `AutoStart`/`AutoStop`. Test it
  on your DBMS, or use explicit `StartTransaction` and `Commit`, which behave the same everywhere.
- `Connection.ExecSQL` and every dataset on that connection share the connection's transaction.

## Nested transactions (SQLite)

`EnableNested` is `True`, so a second `StartTransaction` nests:

| Sequence                                                            | Rows left |
|---------------------------------------------------------------------|-----------|
| Start, INSERT o, Start, INSERT i, **Rollback**, Commit              | o only    |
| Start, INSERT o, Start, INSERT i, Commit, **Rollback**              | none      |

So inner `Rollback` undoes only the inner work; an outer `Rollback` undoes everything, even an inner
`Commit`. With `EnableNested := False` the second `StartTransaction` raised `EFDException`
`-318. Transaction ... must be inactive. Nested transactions are disabled`.
How nesting is done (savepoints) and whether every driver supports it: not checked.

## Several transactions on one connection

`TFDTransaction` (`FireDAC.Comp.Client`) and the `Transaction` property of datasets and of `TFDConnection`
exist in the source and compile. Not run: SQLite has one transaction per connection, so it proves nothing.
Do not promise parallel independent transactions on one connection without testing the target server.

## Cached updates and transactions

`Q.ApplyUpdates` does not wrap the batch in a transaction (see `cached-updates.md`). Wrap it:

```pascal
C.StartTransaction;
try
  if Q.ApplyUpdates(0) <> 0 then
    raise Exception.Create('apply failed');
  C.Commit;
  Q.CommitUpdates;
except
  C.Rollback;
  raise;
end;
```

`TFDConnection.ApplyUpdates([Q1, Q2])` does this for several datasets (transaction, apply, commit,
`CommitUpdates`) but is marked `deprecated` in the source: it compiles with warning W1000.
