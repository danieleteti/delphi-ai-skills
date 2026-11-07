# Crypto helpers: random bytes, password hash, DPAPI, wiping

Compiled with `dcc32` and `dcc64` 37.0 (Delphi 13) and run on Windows 11. Unit `SecCrypto`, used by the
rules in `SKILL.md`. The Windows imports (`bcrypt.dll`, `crypt32.dll`) are declared here because
`Winapi.Windows` declares none of them (`E2003` when tried).

What was checked by running:

- `Pbkdf2Sha256` (OS call) and `Pbkdf2Sha256Portable` (RTL only) both give the RFC 7914 section 11
  vector for `passwd` / `salt` / 1 iteration (`55ac046e56e3089f...`), and equal outputs at 2000 iterations.
- Time for 600000 iterations on the test machine: OS call 247 ms (32-bit) and 115 ms (64-bit); portable
  version 952 ms (32-bit). Measure on the target hardware and pick the count from a time budget.
- `HashPassword` output differs on every call (random salt); `VerifyPassword` accepts the right
  password, rejects a wrong one and a malformed record.
- DPAPI round trip works; the ciphertext does not contain the plaintext; a blob with one flipped byte
  fails with `Dati non validi` (error 13).

Not verified: the minimum Windows version for `BCryptDeriveKeyPBKDF2`; that `ConstTimeEquals` takes
constant time (it has no early exit, but it was not timed); that the compiler never drops a `FillChar`
whose buffer is not read afterwards (the buffers here are heap buffers, a call the RTL makes).

Limits of PBKDF2: it needs only CPU, so attackers' GPUs do well against it. It is acceptable with a high
iteration count; where you can choose and ship a library, bcrypt, scrypt or Argon2 resist hardware better.
None of those was tested here.

```pascal
unit SecCrypto;

interface

uses
  System.SysUtils;

function RandomBytes(Count: Integer): TBytes;
function Pbkdf2Sha256(const Password, Salt: TBytes; Iterations: Cardinal; KeyLen: Integer): TBytes;
function Pbkdf2Sha256Portable(const Password, Salt: TBytes; Iterations, KeyLen: Integer): TBytes;
function ConstTimeEquals(const A, B: TBytes): Boolean;
function HashPassword(const Password: string; Iterations: Cardinal = 600000): string;
function VerifyPassword(const Password, Stored: string): Boolean;
procedure WipeBytes(var B: TBytes);
procedure WipeString(var S: string);
function ProtectForCurrentUser(const Plain: TBytes): TBytes;
function UnprotectForCurrentUser(const Blob: TBytes): TBytes;

implementation

uses
  System.Hash, System.Classes, Winapi.Windows;

const
  BCRYPT_USE_SYSTEM_PREFERRED_RNG = $00000002;
  BCRYPT_ALG_HANDLE_HMAC_FLAG = $00000008;
  CRYPTPROTECT_UI_FORBIDDEN = $00000001;

type
  TDataBlob = record
    cbData: DWORD;
    pbData: PByte;
  end;
  PDataBlob = ^TDataBlob;

function BCryptGenRandom(hAlgorithm: Pointer; pbBuffer: PByte; cbBuffer: ULONG;
  dwFlags: ULONG): LongInt; stdcall; external 'bcrypt.dll';
function BCryptOpenAlgorithmProvider(out phAlgorithm: Pointer; pszAlgId: PWideChar;
  pszImplementation: PWideChar; dwFlags: ULONG): LongInt; stdcall; external 'bcrypt.dll';
function BCryptCloseAlgorithmProvider(hAlgorithm: Pointer;
  dwFlags: ULONG): LongInt; stdcall; external 'bcrypt.dll';
function BCryptDeriveKeyPBKDF2(hPrf: Pointer; pbPassword: PByte; cbPassword: ULONG;
  pbSalt: PByte; cbSalt: ULONG; cIterations: UInt64; pbDerivedKey: PByte;
  cbDerivedKey: ULONG; dwFlags: ULONG): LongInt; stdcall; external 'bcrypt.dll';

function CryptProtectData(pDataIn: PDataBlob; szDataDescr: PWideChar;
  pOptionalEntropy: PDataBlob; pvReserved: Pointer; pPrompt: Pointer;
  dwFlags: DWORD; pDataOut: PDataBlob): BOOL; stdcall; external 'crypt32.dll';
function CryptUnprotectData(pDataIn: PDataBlob; ppszDataDescr: PPWideChar;
  pOptionalEntropy: PDataBlob; pvReserved: Pointer; pPrompt: Pointer;
  dwFlags: DWORD; pDataOut: PDataBlob): BOOL; stdcall; external 'crypt32.dll';

function RandomBytes(Count: Integer): TBytes;
begin
  SetLength(Result, Count);
  if Count = 0 then
    Exit;
  if BCryptGenRandom(nil, @Result[0], Count, BCRYPT_USE_SYSTEM_PREFERRED_RNG) < 0 then
    raise Exception.Create('BCryptGenRandom failed');
end;

function Pbkdf2Sha256(const Password, Salt: TBytes; Iterations: Cardinal; KeyLen: Integer): TBytes;
var
  Alg: Pointer;
begin
  if BCryptOpenAlgorithmProvider(Alg, 'SHA256', nil, BCRYPT_ALG_HANDLE_HMAC_FLAG) < 0 then
    raise Exception.Create('BCryptOpenAlgorithmProvider failed');
  try
    SetLength(Result, KeyLen);
    if BCryptDeriveKeyPBKDF2(Alg, PByte(Password), Length(Password), PByte(Salt),
      Length(Salt), Iterations, PByte(Result), KeyLen, 0) < 0 then
      raise Exception.Create('BCryptDeriveKeyPBKDF2 failed');
  finally
    BCryptCloseAlgorithmProvider(Alg, 0);
  end;
end;

// RFC 8018 PBKDF2 on THashSHA2.GetHMACAsBytes. About 4x slower than the OS call (measured).
function Pbkdf2Sha256Portable(const Password, Salt: TBytes; Iterations, KeyLen: Integer): TBytes;
var
  Blk, U, T: TBytes;
  Block, I, J, N: Integer;
begin
  SetLength(Result, 0);
  Block := 0;
  while Length(Result) < KeyLen do
  begin
    Inc(Block);
    Blk := Salt;
    SetLength(Blk, Length(Salt) + 4);   // Copy(Salt, 0, n + 4) would NOT grow the array
    Blk[Length(Salt)] := Block shr 24;
    Blk[Length(Salt) + 1] := Block shr 16;
    Blk[Length(Salt) + 2] := Block shr 8;
    Blk[Length(Salt) + 3] := Block;
    U := THashSHA2.GetHMACAsBytes(Blk, Password, SHA256);
    T := Copy(U);
    for I := 2 to Iterations do
    begin
      U := THashSHA2.GetHMACAsBytes(U, Password, SHA256);
      for J := 0 to High(T) do
        T[J] := T[J] xor U[J];
    end;
    N := Length(Result);
    SetLength(Result, N + Length(T));
    Move(T[0], Result[N], Length(T));
  end;
  SetLength(Result, KeyLen);
end;

// Does not stop at the first difference. The length is not secret here.
function ConstTimeEquals(const A, B: TBytes): Boolean;
var
  I, Diff: Integer;
begin
  if Length(A) <> Length(B) then
    Exit(False);
  Diff := 0;
  for I := 0 to High(A) do
    Diff := Diff or (A[I] xor B[I]);
  Result := Diff = 0;
end;

function HexToBytes(const S: string): TBytes;
begin
  SetLength(Result, Length(S) div 2);
  if Length(Result) > 0 then
    HexToBin(PChar(S), Result, Length(Result));
end;

function HashPassword(const Password: string; Iterations: Cardinal): string;
var
  Pwd, Salt, Key: TBytes;
begin
  Pwd := TEncoding.UTF8.GetBytes(Password);
  try
    Salt := RandomBytes(16);
    Key := Pbkdf2Sha256(Pwd, Salt, Iterations, 32);
    Result := Format('pbkdf2-sha256$%d$%s$%s',
      [Iterations, THash.DigestAsString(Salt), THash.DigestAsString(Key)]);
  finally
    WipeBytes(Pwd);
  end;
end;

function VerifyPassword(const Password, Stored: string): Boolean;
var
  Parts: TArray<string>;
  Pwd, Salt, Expected, Actual: TBytes;
  Iter: Cardinal;
begin
  Parts := Stored.Split(['$']);
  if (Length(Parts) <> 4) or (Parts[0] <> 'pbkdf2-sha256') then
    Exit(False);
  Iter := StrToUIntDef(Parts[1], 0);
  if Iter = 0 then
    Exit(False);
  Salt := HexToBytes(Parts[2]);
  Expected := HexToBytes(Parts[3]);
  Pwd := TEncoding.UTF8.GetBytes(Password);
  try
    Actual := Pbkdf2Sha256(Pwd, Salt, Iter, Length(Expected));
    Result := ConstTimeEquals(Actual, Expected);
  finally
    WipeBytes(Pwd);
  end;
end;

procedure WipeBytes(var B: TBytes);
begin
  if Length(B) > 0 then
    FillChar(B[0], Length(B), 0);
end;

// Wipes the one buffer this variable points to. Copies made earlier are not touched.
procedure WipeString(var S: string);
begin
  if S = '' then
    Exit;
  UniqueString(S);
  FillChar(Pointer(S)^, Length(S) * SizeOf(Char), 0);
  S := '';
end;

function ProtectForCurrentUser(const Plain: TBytes): TBytes;
var
  InBlob, OutBlob: TDataBlob;
begin
  InBlob.cbData := Length(Plain);
  InBlob.pbData := PByte(Plain);
  if not CryptProtectData(@InBlob, nil, nil, nil, nil, CRYPTPROTECT_UI_FORBIDDEN, @OutBlob) then
    RaiseLastOSError;
  try
    SetLength(Result, OutBlob.cbData);
    Move(OutBlob.pbData^, Result[0], OutBlob.cbData);
  finally
    LocalFree(HLOCAL(OutBlob.pbData));
  end;
end;

function UnprotectForCurrentUser(const Blob: TBytes): TBytes;
var
  InBlob, OutBlob: TDataBlob;
begin
  InBlob.cbData := Length(Blob);
  InBlob.pbData := PByte(Blob);
  if not CryptUnprotectData(@InBlob, nil, nil, nil, nil, CRYPTPROTECT_UI_FORBIDDEN, @OutBlob) then
    RaiseLastOSError;
  try
    SetLength(Result, OutBlob.cbData);
    Move(OutBlob.pbData^, Result[0], OutBlob.cbData);
  finally
    ZeroMemory(OutBlob.pbData, OutBlob.cbData);
    LocalFree(HLOCAL(OutBlob.pbData));
  end;
end;

end.
```
