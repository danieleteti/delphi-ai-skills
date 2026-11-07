---
name: delphi-security
description: Use when writing or reviewing the security of plain Delphi code that is not a web server - desktop apps, services, console tools, clients. Covers password hashing, random tokens and keys, THTTPClient/TNetHTTPClient TLS and certificate validation, SQL injection in FireDAC macros, path traversal, secrets and passwords in memory, ShellExecute/CreateProcess command injection, DLL search order, untrusted sizes, and what a log or crash report must not contain. Server endpoints belong to dmvcframework-security. Triggers on "security review", "password hash", "random token", "certificate validation", "path traversal", "SQL injection", "secrets", "secure coding".
---

# Delphi security - desktop, service and client code

For DMVCFramework server endpoints use the `dmvcframework-security` skill instead. This one is for code
that runs on the user's machine or talks to a server as a client.

Checked on Delphi 13 (`dcc32`/`dcc64` 37.0, Windows 11): every code skeleton was compiled and run, and the
claims below were seen running unless marked otherwise. The declarations were also read in the 12 Athens
(23.0) source: same. Windows only; nothing here was tried on macOS, Linux or mobile.

## Critical rules

1. **The RTL has no password KDF.** `System.Hash` has MD5, SHA1, SHA2 (HMAC included), BobJenkins and FNV
   only: no PBKDF2, bcrypt, scrypt, Argon2, SHA3, HKDF or constant-time compare. `THashSHA2.GetHashString(Salt + Password)`
   is a fast hash: billions of guesses per second. Use `Pbkdf2Sha256` (`reference/crypto-code.md`).
2. **`Random`, `Randomize` and `THash.GetRandomString` are predictable.** `RandSeed` is a 32-bit `Integer`; the same
   seed gives the same "random" string. Never for tokens, salts, keys or session ids. Use `RandomBytes` (`BCryptGenRandom`).
3. **`Winapi.Windows` declares none of** `BCryptGenRandom`, `CryptGenRandom`, `SecureZeroMemory`,
   `SetDefaultDllDirectories`, `CryptProtectData`: `E2003` when compiled for the first three, absent from the RTL source for the
   others. Declare the import yourself, as the reference units do.
4. **`Accepted := True` in `OnValidateServerCertificate` switches off** the unknown-CA, wrong-usage, wrong-name
   and expired-date checks for that connection. Narrow the verdict, never widen it.
5. **FireDAC `!name` macros and `AsRaw` paste text verbatim.** Only values bound as `:param` are safe.
6. **`TPath.Combine` does not confine.** A rooted second argument replaces the first, `..` stays. `GetFullPath`
   does not see junctions or symlinks.
7. **A bare `LoadLibrary('x.dll')` finds a DLL planted in the current directory.** So does a static `external 'x.dll'`.
8. **Wiping a string wipes one buffer.** Every earlier copy, concatenation or `Edit.Text` copy survives.
9. **`{$Q+}{$R+}` do not catch** `Integer(Int64Value)` hard casts or `shl`.

## Which unit declares what

| Identifier | Where | Note |
|---|---|---|
| `THash`, `THashMD5`, `THashSHA1`, `THashSHA2`, `THashBobJenkins`, `THashFNV1a32` | `System.Hash` | `GetHMAC`, `GetHMACAsBytes` only on MD5, SHA1, SHA2 |
| `TSHA2Version` (`SHA256`, `SHA512`, ...) | `System.Hash` | |
| `TNetEncoding.Base64`, `.Base64String`, `.Base64URL` | `System.NetEncoding` | see 3 |
| `THTTPClient`, `IHTTPResponse` | `System.Net.HttpClient` | |
| `TCertificate`, `TURLRequest`, `TValidateCertificateEvent` | `System.Net.URLClient` | |
| `TPath.Combine`, `TPath.GetFullPath`, `TFile`, `TDirectory` | `System.IOUtils` | |
| `StartsWith(Value, IgnoreCase)` on `string` | `System.SysUtils` | `TStringHelper` |
| `LoadLibraryEx`, `SetDllDirectory`, `GetFinalPathNameByHandle`, `ZeroMemory`, `CreateProcess` | `Winapi.Windows` | |
| `ShellExecute`, `CommandLineToArgvW` | `Winapi.ShellAPI` | |
| `TFDMacro`, `mdRaw`, `mdIdentifier` | `FireDAC.Stan.Param` | |

Each item: bad code, why, fix, how to find it (PowerShell `Select-String`; `rg -n -e '<pattern>'` takes the same patterns).

## 1. Password hashing

```pascal
Hash := THashSHA2.GetHashString(Salt + Password);      // bad: one SHA-256, no work factor
```
Why: speed is the attack. Even salted, an offline guess costs nanoseconds.
Fix: `HashPassword` / `VerifyPassword` from `reference/crypto-code.md`: PBKDF2-HMAC-SHA256, 16 random bytes of
salt, iteration count stored in the record (`pbkdf2-sha256$600000$salt$hash`) so it can be raised later, compare with
`ConstTimeEquals`. `BCryptDeriveKeyPBKDF2` from `bcrypt.dll` is about 4x faster than the same loop on
`THashSHA2.GetHMACAsBytes` (also given, for non-Windows targets); both match the RFC 7914 vector. Pick the iteration count
from a time budget measured on the weakest target. PBKDF2 is CPU-only: it is a floor, not the best available.
`THashSHA2.GetHMAC` is a message authentication code, not a password hash.
Find: `Get-ChildItem -Recurse *.pas | Select-String '(?i)THash(MD5|SHA1|SHA2)\.GetHash(String|Bytes|AsString)?\(.*(pass|pwd)'`

## 2. Random numbers

```pascal
Token := THash.GetRandomString(32);       // bad: PV[Random(L)] over 64 characters, 32-bit seed
Randomize; Key[I] := Random(256);         // bad
```
Why: `Randomize` folds a 64-bit `QueryPerformanceCounter` value into the 32-bit `RandSeed`: at most 2^32 sequences, and
the generator is a plain linear congruential one. After `RandSeed := 777`, two `THash.GetRandomString(16)` calls both
returned `PjFv5SRjxQIQdya8`.
Fix: `RandomBytes(Count)` (imports `BCryptGenRandom` with `BCRYPT_USE_SYSTEM_PREFERRED_RNG`, 2). Encode with
`THash.DigestAsString` (hex) or `TNetEncoding.Base64URL`. The RTL has no CSPRNG class or wrapper.
Find: `Select-String '\bRandomize\b|\bRandom\(|THash\.GetRandomString'` and read each hit: `Random` is fine for shuffling a UI.

## 3. Base64 and tokens

- `TNetEncoding.Base64` wraps at 76 characters with `#13#10` (a 100-byte input gave 138 characters with CRLF),
  keeps `=` and uses `+` `/`. `Base64String` is one line, still padded. Only `Base64URL` gives `-` `_` and no padding
  (bytes `FB FF FE 01`: `+//+AQ==` against `-__-AQ`). JWT segments and URLs need `Base64URL`.
- Decoding is lenient: `TNetEncoding.Base64.Decode('QUJD!!!!REVG')` returns `ABCDEF`. Garbage is skipped, not rejected.
  Validate the alphabet and length yourself when the string is a credential.
- `TNetEncoding.URL.Encode` turns a space into `+` (form style), not `%20`.
Find: `Select-String 'TNetEncoding\.Base64\.(Encode|EncodeBytesToString)'`

## 4. TLS in THTTPClient / TNetHTTPClient

- Validation is on by default (WinHTTP, Windows store). A bad certificate raises `ENetHTTPCertificateException`
  (seen with an expired certificate). `SecureProtocols` defaults to `[]`, which means "the OS default protocols", not
  "TLS 1.2 only"; set it explicitly if policy requires a minimum. Windows source: it acts only when the set is not empty.
- The handler runs for **valid certificates too** on Windows, with `Accepted` preset to `True`; for an invalid one it is
  preset to `False` (both seen). Setting `Accepted := True` on an expired certificate completed the request.
- `TCertificate` has `CertName`, `SerialNum`, `Expiry`, `Start`, `Subject`, `Issuer`, `ProtocolName`, `AlgSignature`,
  `AlgEncryption`, `KeySize`, `PublicKey`. **No thumbprint, no DER.** `PublicKey` is filled **only for RSA keys**: for an
  EC certificate it was an empty string, and `SHA256('')` is the same for every EC server, so a pin on its hash accepts any of them.
- Pin by narrowing the OS verdict. Compiled and run against a real HTTPS site: right pin accepted, wrong issuer rejected.

```pascal
type
  TPinCheck = class
    Serial, Issuer: string;
    procedure Validate(const Sender: TObject; const ARequest: TURLRequest;
      const Certificate: TCertificate; var Accepted: Boolean);
  end;

procedure TPinCheck.Validate(const Sender: TObject; const ARequest: TURLRequest;
  const Certificate: TCertificate; var Accepted: Boolean);
begin
  Accepted := Accepted and SameText(Certificate.SerialNum, Serial) and (Certificate.Issuer = Issuer);
end;
// Client.OnValidateServerCertificate := Pin.Validate;
```
Limit: serial plus issuer identifies a certificate but is not a hash of it; pins break at renewal, so ship a second one.
To trust a private CA, install it in the Windows store instead of accepting in code.
Find: `Select-String 'OnValidateServerCertificate|Accepted\s*:=\s*True'`

## 5. SQL injection in FireDAC

Safe: `:name` with `ParamByName`, and `Open`/`ExecSQL(sql, [values])`. Run against in-memory SQLite with the value
`x' OR '1'='1`: concatenation matched 2 rows, both parameter forms 0.
```pascal
Q.Open('select * from u where name = ''' + Edit1.Text + '''');         // bad
Q.SQL.Text := 'select * from !tbl'; Q.MacroByName('tbl').Value := X;  // bad: !name is mdRaw
Q.MacroByName('tbl').AsRaw := X;                                       // bad: always verbatim
```
Macro rules, from `FireDAC.Phys.SQLPreprocessor` and seen running (value `u UNION SELECT 99`):

| Written | Created as | Result |
|---|---|---|
| `&tbl` + `.Value` / `.AsString` | `mdIdentifier` | emitted as `{id '...'}`: "no such table", not injected |
| `&tbl` + `.AsRaw` | `AsRaw` sets `mdRaw` | injected (3 rows) |
| `!tbl` + `.Value` | `mdRaw` | injected (3 rows) |

A macro is for an identifier or clause chosen from a whitelist, never for a user value:
`if IndexText(Col, ['name', 'created']) < 0 then raise EArgumentException.Create('column')` (`System.StrUtils`).
Observed once, not studied: changing `SQL.Text` on a query that already has a macro of that name kept the old `DataType`
(an `&t` macro stayed `mdIdentifier` under a later `!t`). Use a fresh query object, or set `DataType` explicitly.
Find: `Select-String '(?i)(\.SQL\.(Text|Add)\s*:?=|\.Open\(|\.ExecSQL\(|\.ExecSQLScalar\()[^;]*''\s*\+'`
and `Select-String '(?i)''[^'']*![A-Za-z_]\w*|\.AsRaw\b|\bmdRaw\b'`.

## 6. Path traversal

```pascal
Path := TPath.Combine(BaseDir, UserName);          // bad: not confined
if Path.StartsWith(BaseDir) then ...               // bad: also accepts C:\base2\x
```
Why (all run): `Combine('C:\base', '..\..\Windows')` returns it unchanged; `Combine('C:\base', 'C:\Windows\x')` and
`Combine('C:\base', '\Windows\x')` return the second argument alone; `ValidateParams` only rejects characters like `|`
(`a*b` passed). Forward slashes are separators too. `GetFullPath` resolves `..` but not links: a junction inside the base
folder pointing outside passed the lexical test, and `GetFinalPathNameByHandle` showed the real target outside.
Fix: `SafeResolve(BaseDir, UserName)` from `reference/os-code.md`: reject `:` (drive letters, NTFS alternate streams),
`GetFullPath`, compare with the base plus a trailing separator, case-insensitively (`StartsWith(Value, True)`: NTFS is
case-insensitive, `..\BASE\ok.txt` is the same file), then compare the real path of the folder or file. Opening and then
checking the handle's final path closes the check-then-use gap further; `SafeResolve` does not.
Find: `Select-String 'TPath\.Combine|TFileStream\.Create|TFile\.(ReadAll|Open|Delete|Copy|Move)\w*\('` and check each argument's origin.

## 7. Secrets

- A literal in the source ends up in the exe. `const Key = 'sk_live_...'` was found as UTF-16 in the compiled file with
  a byte search. No obfuscation changes the fact that the program must hold the key.
- `.ini` (`TIniFile`) and plain registry values are readable by anyone with the user's rights.
- For a per-user secret on Windows use DPAPI: `ProtectForCurrentUser` / `UnprotectForCurrentUser`
  (`reference/crypto-code.md`, round trip run, tampered blob rejected). Only that Windows user, on that machine, can decrypt.
- **In memory**: `string` is copy-on-write and reference counted. `S2 := S` shares one buffer, so wiping through one
  pointer blanks both (seen). `S + '!'` makes a separate buffer that stays (seen). `S := ''` frees without clearing: the
  bytes were still readable through a saved pointer (seen). So: `WipeString` calls `UniqueString`, `FillChar`, then
  clears; `WipeBytes` for `TBytes`. Hold secrets in `TBytes`, convert from the edit box once, wipe at once. Text that went
  through a `TEdit`, a `TStringBuilder` or a concatenation has copies you cannot reach. There is no `SecureZeroMemory`;
  `FillChar`/`ZeroMemory` are what is left.
Find: `Select-String '(?i)\b\w*(password|passwd|pwd|secret|apikey|api_key|token)\w*\s*(:=|=)\s*''[^'']{4,}'''` and
`Select-String 'TIniFile|TRegistry|WriteString\(.*(pass|secret|key)'`.

## 8. Command injection

```pascal
ShellExecute(0, 'open', PChar('cmd.exe'), PChar('/c type ' + FileName), nil, SW_HIDE);   // bad
CreateProcess(nil, PChar(ExePath + ' ' + UserArg), ...);                                // bad
```
Seen: `cmd.exe /c echo hi & echo INJECTED> file` created the file: `&` ends the command. Concatenating `one two" three` made
two arguments out of one. An unquoted path with a space and no `lpApplicationName` ran `...\sp.exe` instead of
`...\sp ace\echoargs.exe` (Windows tries the shorter name first). `ShellExecute(..., 'open', X)` on a user-supplied file
name runs it: a `.cmd` file executed.
Fix: no shell. `RunAndWait(ExePath, [Arg1, Arg2])` from `reference/os-code.md` passes `ExePath` as `lpApplicationName` and
quotes each argument with the `CommandLineToArgvW` rules (`QuoteArg`). A Delphi callee that reads `ParamStr` does not undo `\"`
(seen): refuse quotes in arguments for such callees. Never build a `cmd.exe /c` line from user text; if the user picks a
document to open, check its extension against a whitelist first.
Find: `Select-String '\b(ShellExecute[AW]?|ShellExecuteEx|CreateProcess[AW]?|WinExec)\s*\(|cmd(\.exe)?\s*/c'`

## 9. Loading DLLs

Seen with a DLL present only in the current directory: bare `LoadLibrary('x.dll')` loaded it; so did a static
`function F: Integer; external 'x.dll'`, from an exe located elsewhere. `LoadLibraryEx(..., LOAD_LIBRARY_SEARCH_SYSTEM32)`
and `LOAD_LIBRARY_SEARCH_DEFAULT_DIRS` failed with error 126. `SetDllDirectory('')` also removed the current directory, but
`SetDllDirectory(nil)` restored it. After `SetDefaultDllDirectories($1000)` a static import marked `delayed` failed at the call
(`EExternalException`, `C06D007E`), a plain static import cannot be saved this way: it is resolved before any of your code runs.
Fix: `HardenDllSearch` first in the `.dpr`, `delayed` for imports you control, `LoadDllFromAppDir` (full path) for plug-ins.
`LOAD_LIBRARY_SEARCH_*` constants and `SetDefaultDllDirectories` are not in `Winapi.Windows`; the unit declares them.
Find: `Select-String '\bLoadLibrary(Ex)?[AW]?\s*\(|external\s+''[^'']+\.dll'''`

## 10. Untrusted lengths and counts

Compiler switches (run, same program with `{$Q-}{$R-}` and `{$Q+}{$R+}`):

| Case | Off | `{$Q+}{$R+}` |
|---|---|---|
| `MaxInt + 1`, `Count * 16` wrapping, `Cardinal` `0 - 1` | silent | `EIntOverflow` |
| `Off + Cnt <= Length(Buf)` with `Cnt = MaxInt - 2` | check passes (wrapped negative) | `EIntOverflow` |
| `A := Int64Value`, `A := CardinalValue` | silent | `ERangeError` |
| `Buf[Length(Buf)]` write | silent | `ERangeError` |
| `Integer(Int64Value)` hard cast, `x shl n` | silent | **silent** |

`SetLength(Buf, -1)` raises `ERangeError` either way; `Stream.ReadBuffer` past the end raises `EReadError`.
Rules: read a length as `UInt32`/`Int64`, cap it, compare with `Stream.Size - Stream.Position`, then allocate: `ReadBlock`
(`reference/os-code.md`). Rewrite `Off + Cnt <= Len` as `Cnt <= Len - Off` after checking `Off <= Len`. Do the multiplication
in `Int64`. Keep `{$Q+}{$R+}` on in Debug, but a release build without them is only safe where the checks are explicit.
Find: `Select-String '\{\$[QR]-\}|\bInteger\(|\bSetLength\s*\(\s*\w+\s*,\s*\w+\s*\)|\.ReadBuffer\('`

## Reference index

| File | Open when |
|---|---|
| `reference/crypto-code.md` | hashing a password, making a token or salt, storing a secret with DPAPI, wiping buffers (unit `SecCrypto`) |
| `reference/os-code.md` | serving files from a folder, starting a program, loading a DLL, reading lengths from a file or socket (unit `SecOs`) |
| `reference/logging-and-monitoring.md` | writing a log or crash report, sending logs off the machine, deciding what goes into an exception message (unit `SecLog`) |

Related: `delphi` (strings, lifetime), `delphi-code-smells` (leak and warning review), `dmvcframework-security` (server endpoints).
