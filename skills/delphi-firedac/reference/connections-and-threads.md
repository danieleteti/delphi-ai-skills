# Connections, pooling and threads

Read this when: you configure a connection, turn on pooling, or touch FireDAC from more than one thread.
Everything below ran on SQLite (file database for pools, since each `:memory:` connection is its own
database). Delphi 13 and Delphi 12 gave the same results unless stated.

## Private connection vs connection definition

```pascal
// private: parameters live on the component
C := TFDConnection.Create(nil);
C.DriverName := 'SQLite';
C.Params.Database := 'C:\data\app.db';
C.Open;

// named definition: parameters live in FDManager, components refer to the name
Defs := TStringList.Create;
try
  Defs.Add('Database=C:\data\app.db');
  FDManager.AddConnectionDef('AppDb', 'SQLite', Defs);   // (Name, DriverId, Params: TStrings, Persistent: Boolean = False)
finally
  Defs.Free;
end;
C.ConnectionDefName := 'AppDb';
C.Open;
```

`FDManager.AddConnectionDef` copies the strings, so freeing `Defs` is correct (the run above does exactly
this). The fourth argument `APersistent` defaults to `False`: the definition lives for the process only
and is not written to the connection-definition file. `FDManager.IsConnectionDef('AppDb')` tells whether it
exists. `FDManager` is `FireDAC.Comp.Client`.

A `TFDQuery` with `Connection := C` connects lazily: `C.Connected` was `False` before the first `ExecSQL`
and `True` after. A query with no `Connection` raises `-512. Connection is not defined`.
`C.Close` closes every dataset that uses it (`Q.Active` became `False`).

## Pooling

Pooling is a property of a **named definition**, not of a component.

```pascal
Defs := TStringList.Create;
try
  Defs.Add('Database=C:\data\app.db');
  Defs.Add('Pooled=True');
  Defs.Add('POOL_MaximumItems=20');
  FDManager.AddConnectionDef('PoolDb', 'SQLite', Defs);
finally
  Defs.Free;
end;
// per use (in a request, a thread, a method):
C := TFDConnection.Create(nil);
try
  C.ConnectionDefName := 'PoolDb';   // nothing else on this component
  C.Open;                            // takes a physical connection from the pool
  ...
finally
  C.Free;                            // Close or Free: both give it back
end;
```

Needs `FireDAC.Stan.Pool` in `uses` (without it: `Object factory ... include unit [FireDAC.Stan.Pool]`).

| Parameter            | Default (source constant)   | Meaning                                                       |
|----------------------|-----------------------------|---------------------------------------------------------------|
| `Pooled`             | `False`                     | Turns pooling on for the definition.                          |
| `POOL_MaximumItems`  | `50` (`C_FD_PoolMaximumItems`) | Max simultaneous physical connections.                     |
| `POOL_CleanupTimeout`| `30000` ms                  | How often the pool's cleanup thread wakes.                    |
| `POOL_ExpireTimeout` | `90000` ms                  | An idle connection unused this long is closed at a cleanup.   |

Verified facts:

- `C.Params.Pooled := True` on a private connection, or `ConnectionDefName` plus an extra entry in `C.Params`
  (tried `LockingMode=Normal`): `Open` raises `EFDException` `[FireDAC][Comp][Clnt]-507. Connection ... cannot
  be pooled`. A pooled connection takes nothing but the definition name.
- **Exhaustion does not wait.** With `POOL_MaximumItems=2`, the third `Open` raised at once:
  `EFDException [FireDAC][Stan]-708. Cannot acquire item (connection) from pool. Maximal number [2] of
  simultaneous items (connections) reached.` `FireDAC.Stan.Pool` raises when the list is full and the
  source has no wait loop there. Size the pool for the real concurrency, or serialise the
  callers yourself.
- 8 threads, pool of 4, each holding its connection 5 ms: 95-101 of 160 acquisitions failed with `-708`.
  4 threads, pool of 4: no error.
- `Close` returns the physical connection; a following `Open` on another `TFDConnection` with the same
  definition succeeded.
- **Close on a pooled connection with an active transaction commits it** (default `DisconnectAction`,
  see `transactions.md`). Row count after `StartTransaction; INSERT; Close` and a reopen: 1.
- `FDManager.CloseConnectionDef('PoolDb')` ran without error after all connections were freed. What it
  does to the pool's physical connections was not checked.
- Use a file database in pool tests: every plain `:memory:` connection is its own empty database (not
  tested with a pooled definition).

## Threads

Rules, in the order of how much they cost:

1. **One `TFDConnection` per thread**, created and used in that thread. Create it inside `Execute`, not in
   the main thread. Source basis: I found no lock around `TFDConnection`/dataset state in
   `FireDAC.Comp.Client`; only `FDManager` has one (a `TMultiReadExclusiveWriteSynchronizer`). I did not
   run two threads on one connection on purpose. Treat sharing as unsupported.
2. For many short tasks, use a **pooled definition** and make a short-lived `TFDConnection` per task
   (the pattern above). Register the definition once, at start-up, from the main thread, before any
   worker starts.
3. A dataset and its connection stay in the same thread. Do not hand a `TFDQuery` to the UI thread;
   copy values out, or use a `TFDMemTable` filled on the worker and handed over whole.
4. In a worker thread FireDAC is silent automatically (`FDGUIxSilent` compares the thread with
   `MainThreadID`), so no UI unit is needed for the thread itself. The program still needs one if it is a
   non-console exe and the main thread calls FireDAC (see `uses-and-drivers.md`).
5. Pool size >= number of threads that can hold a connection at the same moment, or catch `-708`.

Worker skeleton (compiled and run: 4 threads x 20 acquire/query/release, no errors):

```pascal
procedure TWorker.Execute;
var
  C: TFDConnection;
  i: Integer;
begin
  for i := 1 to 20 do
  begin
    C := TFDConnection.Create(nil);
    try
      C.ConnectionDefName := 'PoolDb';
      C.Open;
      Inc(FSum, Integer(C.ExecSQLScalar('select count(*) from t')));
    finally
      C.Free;
    end;
  end;
end;
```

SQLite specific, may differ elsewhere: a second connection reading a table that another connection is
writing inside an open transaction raised `database table is locked` immediately.
