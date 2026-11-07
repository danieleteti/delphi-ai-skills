# Paths, processes, DLL loading, untrusted lengths

Compiled with `dcc32` and `dcc64` 37.0 (Delphi 13) and run on Windows 11. Unit `SecOs`, used by the
rules in `SKILL.md`.

What was checked by running (32-bit):

- `SafeResolve` accepts `ok.txt`, `new.txt` (not yet existing) and `..\BASE\ok.txt` (case differs), and raises for
  `..\outside\secret.txt`, `ok.txt:hidden`, and for a NTFS junction inside the base folder that points
  outside (`link\secret.txt`, `link\newfile`). The lexical check alone (`IsInside`) accepts the junction.
- `RunAndWait` with arguments `one two" three`, `trail\`, an empty string and `q\"x` gave a callee that
  parses with `CommandLineToArgvW` exactly those four arguments. A callee that reads `ParamStr` got them
  wrong: Delphi's `ParamStr` does not undo `\"`. Keep quotes out of arguments for Delphi callees.
- `HardenDllSearch` then a bare `LoadLibrary` of a DLL that exists only in the current directory fails
  (error 126). `LoadDllFromAppDir` loads a DLL next to the exe.
- `ReadBlock` raises for a length above the cap, for `$FFFFFFFF`, and for a length longer than the rest
  of the stream.

The 64-bit build compiles; the DLL used in the run was 32-bit, so the load tests ran on 32-bit only.
Not verified: how the dependencies of a DLL loaded with `LOAD_LIBRARY_SEARCH_DLL_LOAD_DIR` are searched.

```pascal
unit SecOs;

interface

uses
  System.SysUtils, System.Classes, Winapi.Windows;

function IsInside(const BaseDir, Candidate: string): Boolean;
function FinalPath(const Path: string): string;
function SafeResolve(const BaseDir, UserName: string): string;
function QuoteArg(const Arg: string): string;
function RunAndWait(const ExePath: string; const Args: array of string; TimeoutMs: DWORD = INFINITE): DWORD;
procedure HardenDllSearch;
function LoadDllFromAppDir(const FileName: string): HMODULE;
function ReadBlock(Stream: TStream; Len: UInt32; MaxLen: Integer): TBytes;

implementation

uses
  System.IOUtils;

const
  LOAD_LIBRARY_SEARCH_DLL_LOAD_DIR = $00000100;
  LOAD_LIBRARY_SEARCH_DEFAULT_DIRS = $00001000;

function SetDefaultDllDirectories(DirectoryFlags: DWORD): BOOL; stdcall; external kernel32;

// Lexical test. It does not see junctions or symlinks: see SafeResolve.
function IsInside(const BaseDir, Candidate: string): Boolean;
var
  Base: string;
begin
  Base := IncludeTrailingPathDelimiter(TPath.GetFullPath(BaseDir));
  Result := TPath.GetFullPath(Candidate).StartsWith(Base, True);   // True: NTFS is case-insensitive
end;

// The path the OS really opens: follows junctions and symlinks. The target must exist.
function FinalPath(const Path: string): string;
var
  H: THandle;
  Buf: array[0..1023] of Char;
  N: DWORD;
begin
  H := CreateFile(PChar(Path), 0, FILE_SHARE_READ or FILE_SHARE_WRITE or FILE_SHARE_DELETE,
    nil, OPEN_EXISTING, FILE_FLAG_BACKUP_SEMANTICS, 0);
  if H = INVALID_HANDLE_VALUE then
    RaiseLastOSError;
  try
    N := GetFinalPathNameByHandle(H, Buf, Length(Buf), 0);
    if (N = 0) or (N >= DWORD(Length(Buf))) then
      RaiseLastOSError;
    SetString(Result, Buf, N);
  finally
    CloseHandle(H);
  end;
  if Result.StartsWith('\\?\UNC\') then
    Result := '\\' + Result.Substring(8)
  else if Result.StartsWith('\\?\') then
    Result := Result.Substring(4);
end;

// UserName is one untrusted name or relative path. Returns a full path inside BaseDir or raises.
function SafeResolve(const BaseDir, UserName: string): string;
var
  RealBase, Target: string;
begin
  if UserName.Contains(':') then              // drive letters and NTFS alternate streams
    raise EInOutError.Create('bad name');
  Result := TPath.GetFullPath(TPath.Combine(BaseDir, UserName));
  if not IsInside(BaseDir, Result) then
    raise EInOutError.Create('path escapes the base directory');
  // Second look, on what exists: the folder (or the file itself) may be a junction.
  RealBase := IncludeTrailingPathDelimiter(FinalPath(BaseDir));
  if TFile.Exists(Result) or TDirectory.Exists(Result) then
    Target := FinalPath(Result)
  else
    Target := IncludeTrailingPathDelimiter(FinalPath(ExtractFileDir(Result)));
  if not Target.StartsWith(RealBase, True) then
    raise EInOutError.Create('path escapes the base directory (link)');
end;

// CommandLineToArgvW rules: a backslash is literal unless it precedes a quote.
// A callee that parses with Delphi ParamStr does NOT undo \" (checked): keep quotes out of arguments.
function QuoteArg(const Arg: string): string;
var
  I, Backslashes: Integer;
  C: Char;
begin
  if (Arg <> '') and (Arg.IndexOfAny([' ', #9, '"']) < 0) then
    Exit(Arg);
  Result := '"';
  Backslashes := 0;
  for I := 1 to Length(Arg) do
  begin
    C := Arg[I];
    if C = '\' then
      Inc(Backslashes)
    else if C = '"' then
    begin
      Result := Result + StringOfChar('\', Backslashes * 2 + 1) + '"';
      Backslashes := 0;
    end
    else
    begin
      Result := Result + StringOfChar('\', Backslashes) + C;
      Backslashes := 0;
    end;
  end;
  Result := Result + StringOfChar('\', Backslashes * 2) + '"';
end;

// No shell, no search: ExePath is passed as lpApplicationName, so spaces in it cannot
// make Windows try "C:\Program.exe". Returns the exit code.
function RunAndWait(const ExePath: string; const Args: array of string; TimeoutMs: DWORD): DWORD;
var
  SI: TStartupInfo;
  PI: TProcessInformation;
  CmdLine: string;
  A: string;
begin
  CmdLine := QuoteArg(ExePath);
  for A in Args do
    CmdLine := CmdLine + ' ' + QuoteArg(A);
  UniqueString(CmdLine);                  // CreateProcessW may write into this buffer
  FillChar(SI, SizeOf(SI), 0);
  SI.cb := SizeOf(SI);
  if not CreateProcess(PChar(ExePath), PChar(CmdLine), nil, nil, False, 0, nil, nil, SI, PI) then
    RaiseLastOSError;
  try
    if WaitForSingleObject(PI.hProcess, TimeoutMs) = WAIT_TIMEOUT then
      raise Exception.Create('process timed out');
    GetExitCodeProcess(PI.hProcess, Result);
  finally
    CloseHandle(PI.hProcess);
    CloseHandle(PI.hThread);
  end;
end;

// Call once, first thing in the .dpr: later bare-name LoadLibrary calls no longer
// search the current directory.
procedure HardenDllSearch;
begin
  if not SetDefaultDllDirectories(LOAD_LIBRARY_SEARCH_DEFAULT_DIRS) then
    RaiseLastOSError;
end;

function LoadDllFromAppDir(const FileName: string): HMODULE;
begin
  Result := LoadLibraryEx(PChar(TPath.Combine(ExtractFilePath(ParamStr(0)), FileName)), 0,
    LOAD_LIBRARY_SEARCH_DEFAULT_DIRS or LOAD_LIBRARY_SEARCH_DLL_LOAD_DIR);
  if Result = 0 then
    RaiseLastOSError;
end;

// Len comes from the file or the wire. Check it against what is really left before allocating.
function ReadBlock(Stream: TStream; Len: UInt32; MaxLen: Integer): TBytes;
begin
  if (Len > UInt32(MaxLen)) or (Int64(Len) > Stream.Size - Stream.Position) then
    raise EReadError.Create('block length out of range');
  SetLength(Result, Len);
  if Len > 0 then
    Stream.ReadBuffer(Result, Len);
end;

end.
```
