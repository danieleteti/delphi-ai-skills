# Commands, parameters, macros

Read this when: you run SQL with `TFDQuery` / `TFDCommand` / `TFDStoredProc` / `Connection.ExecSQL`, bind
values, pass NULL, load BLOBs, or build SQL text with `&` or `!`.

Everything here ran on SQLite (Delphi 13 and 12, same output) except where marked.

## Open or ExecSQL

| You call            | On a statement that...      | Result                                                                 |
|---------------------|-----------------------------|------------------------------------------------------------------------|
| `Q.Open`            | returns no rows (INSERT...) | `EFDException -308. Cannot open / define command, which does not return result sets. Hint: use Execute / ExecSQL` |
| `Q.ExecSQL`         | returns rows (SELECT)       | `EFDException -310. Cannot execute command returning result sets. Hint: use Open` |

Both raise, **but the statement had already run**: after `Q.Open('insert ...')` raised `-308`, the row was in the table (count 2 -> 3). Do not retry the "failed" Open after fixing it. `Q.ExecSQL(sql)` and `Q.Open(sql)` set `SQL` and run
in one call. `ExecSQL` is a function: it returns the affected-row count (`C.ExecSQL(...)` printed `10` for an
UPDATE of 10 rows), also in `Q.RowsAffected`.

`Q.Execute` is the same as `ExecSQL` for a `TFDQuery` and also has `Execute(ATimes, AOffset)` for array DML
(see `fetching-and-bulk.md`). `TFDCommand` has `Execute` and `Open` (both compile).

Changing `Q.SQL.Text` on an open query closes it (`Q.Active` was `False` right after, no error).

`TFDConnection` shortcuts, no component needed:

```pascal
n   := C.ExecSQL('update t set n = :n where id = :id', ['x', 7]);   // array of Variant
v   := C.ExecSQLScalar('select max(id) from t');                    // Variant, first column of first row
```

`ExecSQLScalar` on zero rows returned a `Variant` of type `varEmpty` (`VarType = 0`): test with
`VarIsNull(v) or VarIsEmpty(v)`, and `VarToStr` gives `''`.

## Parameters

`:name` creates a parameter; `?` creates positional parameters (`Params[0]`, `Params[1]`; ran fine, 2
parameters). A `:` inside a string literal is not a parameter (`'12:30'`, `'a:b'`: `ParamCount = 0`).

```pascal
Q.SQL.Text := 'insert into t(n, k) values(:n, :k)';
Q.ParamByName('n').AsString  := 'a';
Q.ParamByName('k').AsInteger := 5;
Q.ExecSQL;
```

Types: a parameter created from SQL text has `DataType = ftUnknown`. Assigning `AsInteger`, `AsString`, ...
or `Value := 5` fixes the type. Reusing a prepared query with a different type needs re-preparing:
`C.ExecSQL('...', ['r', Null], [ftString, ftInteger])` after an earlier call on the same SQL text that bound
`9` raised `-338. Param [B] type changed from [ftByte] to [ftInteger]`. Keep the types stable per SQL text,
or use `AsInteger` etc. explicitly.

### NULL

- `Q.ParamByName('n').Clear` or `.Value := Null` on a parameter whose type is still `ftUnknown` raises
  `-335. Parameter [N] data type is unknown`. Set `DataType` first, then `Clear`:

```pascal
Q.ParamByName('n').DataType := ftString;
Q.ParamByName('n').Clear;           // binds NULL
Q.ExecSQL;
```

  `Value := Null` after the type is set also binds NULL (ran).
- `C.ExecSQL(sql, ['r', Null])` without the type array bound NULL fine (ran).
- `AsString := ''` is an empty string, not NULL.

### Streams and BLOBs: who frees what

| Call                                       | Owner of the stream afterwards                        |
|--------------------------------------------|-------------------------------------------------------|
| `Param.AsStream := S`                      | **The parameter.** It destroys `S` when the value is cleared or replaced, or when the parameter is destroyed. Do not free `S`. |
| `Param.SetStream(S, ftBlob, False)`        | You. (`AOwner = False`.) Free after the parameter no longer needs it. |
| `Param.LoadFromStream(S, ftBlob)`          | You. FireDAC copies the bytes and keeps no reference. |

Run with a `TMemoryStream` descendant that prints in its destructor and `ReportMemoryLeaksOnShutdown`:
after `AsStream := S` and `ExecSQL` the destructor ran at `Q.Params.Clear`, not at `ExecSQL`;
`LoadFromStream` left `S` alive until my own `Free`; `SetStream(..., False)` followed by my `Free`: one
destruction, no leak report. `AsStream` is declared in `FireDAC.Stan.Param`; the source line is
`SetStream(AValue, eType, AValue <> nil, AIndex)`.

### Array parameters

`Q.Params.ArraySize := n` and `Q.Params[0].AsStrings[i]` fill rows; see `fetching-and-bulk.md`.

## Macros: `&` and `!`

A macro is text substitution done by FireDAC **before** the SQL reaches the server. It is not a bound value.

| In SQL   | Created as                  | Use for                                       |
|----------|-----------------------------|-----------------------------------------------|
| `&name`  | `mdIdentifier` (default)    | table or column names                         |
| `!name`  | `mdRaw` (default)           | raw SQL fragments: `order by x`, `where ...`  |

The prefix sets only the initial `DataType`. The setter you call can change it (source `TFDMacro.SetData`;
`TFDMacroDataType = (mdUnknown, mdString, mdIdentifier, mdInteger, mdBoolean, mdFloat, mdDate, mdTime,
mdDateTime, mdRaw)`, in `FireDAC.Stan.Param`):

| Setter                | Result in the SQL text (`Macro.SQL`)                 |
|-----------------------|-------------------------------------------------------|
| `AsRaw := x`          | `x`, verbatim                                         |
| `AsIdentifier := x`   | `{id 'x'}`, expanded by the driver to a quoted identifier |
| `AsString := x`       | `{s 'x'}`, a string literal with quotes doubled       |
| `AsInteger := 7`      | `7`                                                   |
| `Value := x`          | keeps the current type: raw for `!`, identifier for `&` |

Quirk: `SetData` changes the type only when the new value differs from the current one, so assigning
the same text again with another setter does nothing.

Run, with `select * from t where n = !val and k = &w`:

- `AsString := 'x'' or ''1''=''1'` -> `... n = 'x'' or ''1''=''1' ...` (escaped, harmless);
- `AsRaw := '1 or 1=1'` -> `... n = 1 or 1=1 ...`: **SQL injection**. 8 of 8 rows came back.
- `&` with `AsString := 't; drop table t'`: the text became a quoted object name; SQLite answered
  `no such table`, the table survived.

Rules:

1. **Values go in parameters.** Macros are for names and fixed fragments you control.
2. Never put user input into `AsRaw`, or into a `!` macro with `Value :=`. Validate against a whitelist of
   column names, then assign.
3. An unassigned macro expands to nothing: `... where k = &k` raised a syntax error.

### The literal trap: `&` and `!` inside quoted text

FireDAC scans string literals for macros. `select 'R&B'` returned **`R`**: `&B` was taken as a macro
named `B`, empty, and silently dropped. `'R!B'` also returned `R`. Verified for `C.ExecSQL`,
`C.ExecSQLScalar` and `TFDQuery`.

| Text                | Result                                 |
|---------------------|----------------------------------------|
| `'R&B'`, `'R!B'`    | `R` (data loss, no error)              |
| `'R&&B'`            | `R&&B` (doubling does not escape in a literal) |
| `'Rock & Roll'`     | unchanged (`&` followed by a space is skipped) |
| `1 != 2`, `3 & 1`   | unchanged; `3 &1` creates a macro      |
| `'a:b'`, `'12:30'`  | unchanged (colon in a literal is not a parameter) |

Fixes: pass the text as a parameter, or switch macro processing off **before** assigning the SQL:

```pascal
Q.ResourceOptions.MacroCreate := False;
Q.ResourceOptions.MacroExpand := False;
Q.SQL.Text := 'select ''R&B''';       // returns R&B
```

Set the same two options on `C.ResourceOptions` to cover `C.ExecSQL`, `C.ExecSQLScalar` and every query on
that connection (ran: `R&B` returned). Setting them after assigning the SQL did not help.
`ParamCreate := False` the same way turns off `:` parsing.

## Stored procedures

`TFDStoredProc` has `StoredProcName`, `Prepare`, `ExecProc`, `ParamByName`, `Params[i].ParamType`; these
compile. Not run: SQLite has no stored procedures, and I tested no other server. Do not claim output
parameter or result-set behaviour from this skill.
