# Cached updates

Read this when: you set `CachedUpdates := True`, call `ApplyUpdates` / `CommitUpdates` / `CancelUpdates`,
or see duplicate rows after saving.

SQLite, Delphi 13 and 12: identical output. Table `t(id integer primary key autoincrement, n text unique)`,
query `select * from t`.

## The cycle

```pascal
Q.CachedUpdates := True;
Q.Open;
Q.Append; Q.FieldByName('n').AsString := 'a'; Q.Post;     // goes to the local cache only
// Q.UpdatesPending = True, Q.ChangeCount = 1

C.StartTransaction;
try
  if Q.ApplyUpdates(0) <> 0 then
    raise Exception.Create('some rows were not saved');
  C.Commit;
except
  C.Rollback;
  raise;
end;
Q.CommitUpdates;                 // clear the cache of applied rows
```

`TFDDataSet` (`FireDAC.Comp.DataSet`) declares `ApplyUpdates(AMaxErrors: Integer = -1): Integer`,
`CommitUpdates`, `CancelUpdates`, `UpdatesPending`, `ChangeCount`, `UpdateStatus`, `RowError`.

## ApplyUpdates

- **The return value is the number of rows that failed**, `0` = all applied. It does not raise for a row
  that the server rejects. Always compare it with 0.
- `AMaxErrors`: `0` stops at the first error, `-1` (default) keeps going. Run with rows `a, a, b` (the
  second `a` violates `unique`): `ApplyUpdates(0)` returned 1 and the database held 1 row (`a`);
  `ApplyUpdates(-1)` returned 1 and the database held 2 rows (`a`, `b`).
- **It is not atomic.** Rows applied before the failure stay in the database unless you wrap the call
  in a transaction. Inside `StartTransaction ... Rollback` the database ended with 0 rows after a
  rollback, and the cache still reported `UpdatesPending = True`.
- A failed row keeps its error: `Q.RowError` (an `EFDException`, nil when the row is fine) while
  `Q.UpdateStatus` is `usInserted` (`TUpdateStatus` from `Data.DB`). To walk changed rows set
  `Q.FilterChanges := [rtModified, rtInserted, rtDeleted, rtUnmodified]` (needs `FireDAC.Comp.DataSet`).

## AutoCommitUpdates and the duplicate-insert trap

`UpdateOptions.AutoCommitUpdates` defaults to **`False`** (BDE behaviour; `TClientDataSet` differs). So a
successful `ApplyUpdates` does not clear the cache:

| Step                              | Result                              |
|-----------------------------------|-------------------------------------|
| Append, Post                      | `UpdatesPending = True`, `id = -1`  |
| `ApplyUpdates(0)` returns 0       | `UpdatesPending` **still True**, `id = 1` (autoinc key refreshed), db has 1 row |
| `ApplyUpdates(0)` again           | returns 0, db has **2 rows**: the same insert sent again |
| `CommitUpdates`                   | `UpdatesPending = False`            |

Fix: call `CommitUpdates` after a successful apply, or set `Q.UpdateOptions.AutoCommitUpdates := True`
(ran: after `ApplyUpdates` `UpdatesPending = False`, a second `ApplyUpdates` returned 0 and added nothing).
With `AutoCommitUpdates := True`, call `ApplyUpdates` inside your transaction as above and `Rollback` on
error; the cache is cleared at apply time, so a later rollback leaves the cache saying "saved" while the
database rolled back (ran: 0 rows in the database, `UpdatesPending = False`: the row is lost). Prefer `False` plus an explicit `CommitUpdates` after `Commit`.

## CancelUpdates, edits, deletes

- `Q.Edit; ...; Post` on a cached query: `UpdatesPending = True`; `CancelUpdates` restored the old value
  and cleared the flag.
- `Q.Delete` then `ApplyUpdates(0)`: returned 0, row gone.
- Without `CachedUpdates`, `Post` writes to the database immediately (ran: count 1 right after `Post`).

## CachedUpdates cannot be turned off with pending changes

`Q.CachedUpdates := False` while `UpdatesPending` raised `EFDException -218. Cannot turn off cached updates
mode ...`. Apply and commit, or `CancelUpdates`, first. To change the SQL of a cached query, do:
`Close; CachedUpdates := False; SQL.Text := ...; CachedUpdates := True; Open` (the order used in the run).

## What FireDAC needs to build the INSERT/UPDATE/DELETE

For a plain `select * from table` FireDAC finds the table and key itself (ran). For joins and computed
columns set `Q.UpdateOptions.UpdateTableName` and the key fields (`ProviderFlags` on the field, or
`UpdateOptions.KeyFields`), or give a `TFDUpdateSQL` (`Q.UpdateObject := US`). All of these compile; not
run beyond the single-table case.

## Several datasets

`C.ApplyUpdates([Q1, Q2])` runs the transaction and `CommitUpdates` for you but is `deprecated` in the
source ("Use Centralized Cached Updates and TFDSchemaAdapter instead"): it compiles with warning W1000.
`TFDSchemaAdapter` is in `FireDAC.Comp.Client`; it was not exercised here.
