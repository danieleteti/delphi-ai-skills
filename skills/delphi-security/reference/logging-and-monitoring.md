# Logging and monitoring without leaking

Open this when code writes a log, a crash report or telemetry, or sends either off the machine. Everything
below was compiled and run on Delphi 13 (`dcc32` 37.0, Windows 11) unless marked "not verified".

## What ends up in exception text

| Source | What was seen | Consequence |
|---|---|---|
| `EFDDBEngineException` (FireDAC) | `E.Message` was clean (`no such table: nope`), but the exception object also carries `E.SQL` (the statement) and `E.Params` (the bound values). A card number bound as a parameter was in `E.Params`. | Never log the exception object or `E.Params` as is. Log `E.Message` and a statement id. |
| File errors (`TFile`, `TDirectory`) | `EDirectoryNotFoundException` text contains the full path, user name and customer folder included. | A path in a log is personal data when it contains a user or customer name. |
| `THTTPClient` | The text of a refused connection was the localized Windows message, without the URL. Other failures were not tried. | Do not rely on the URL being absent. A token in a query string is a secret: keep tokens in a header. |

Not verified: other exception classes. Treat any `E.Message` that embeds user input as sensitive.

## Stack traces

`E.StackTrace` is an empty string in a plain program (seen: length 0). Unit, function and line numbers in a
production build need a stack-trace provider linked into the exe and a detailed map file (`-GD`, see the
`delphi-build` skill). Without both, a crash report holds the message and nothing else.

## Where a log file may live

Seen on this machine: `TPath.GetHomePath` is `...\AppData\Roaming` (travels with a roaming profile),
`TPath.GetCachePath` is `...\AppData\Local`, `TPath.GetPublicPath` is `C:\ProgramData` (readable by every user
of the machine). Use `GetCachePath` or `GetHomePath` for logs that may hold personal data; never the public
folder. Not verified here: that a standard user cannot write beside the exe under `Program Files`, which is the
usual reason not to log there.

## Keep one record on one line, keep secrets out

Text from a user, a file or a socket that is written into a log can contain line breaks and forge a record.
Escape control characters; mask known secret markers. Both helpers below compiled and ran (unit `SecLog`).

```pascal
unit SecLog;

interface

/// Masks the value after password/pwd/token/secret/api key markers written as name=value or name: value.
function RedactSecrets(const AText: string): string;
/// One log record must stay one line: control characters in user text are shown as escapes.
function SafeLogText(const AText: string): string;

implementation

uses
  System.SysUtils, System.RegularExpressions;

function RedactSecrets(const AText: string): string;
begin
  Result := TRegEx.Replace(AText,
    '(?i)\b(password|pwd|token|secret|api[_-]?key)\s*[=:]\s*\S+', '$1=***');
end;

function SafeLogText(const AText: string): string;
var
  C: Char;
begin
  Result := '';
  for C in AText do
    if Ord(C) < 32 then
      Result := Result + '\x' + IntToHex(Ord(C), 2)
    else
      Result := Result + C;
end;

end.
```

What the run showed, so you know the limits:

| Input | Output |
|---|---|
| `Server=db1;Password=Hunter2;Database=sales` | `Server=db1;Password=***` (masks to the end of the token, so it also hides `Database=sales`: safe, lossy) |
| `GET /api?token=abc123&x=1` | `GET /api?token=***` |
| `password = Hunter2 user=bob` | `password=*** user=bob` |
| `{"password":"abc","user":"bob"}` | **unchanged**: JSON form is not caught |
| `Authorization: Bearer eyJ...` | **unchanged**: bearer values are not caught |
| `bob` + CR LF + `2026-11-07 INFO admin logged in` | `bob\x0D\x0A2026-11-07 INFO admin logged in` |

Redaction by pattern is a safety net, not a control: the rule is to not put the secret in the message in the
first place. Add a pattern for each secret format your application really has.

## Sending logs or crash reports off the machine

These are design rules, not API facts (not verified by running anything):

- A monitoring service receives whatever you log. List what leaves the machine and keep personal data out by
  default; retention and consent rules depend on the law that applies to your users, so get that checked by someone
  qualified.
- Check how the client validates TLS before trusting it with logs: section 4 of the main skill.
- A client that buffers logs while offline writes them to disk: protect that folder as you would the log folder.
- An API key compiled into an executable can be extracted from it. Treat it as an identifier that the server can
  limit and revoke, not as a secret.
- Sample or cap what you send: an error loop must not turn into a flood.

If the project already uses ExeWatch, the `exewatch-delphi` skill documents its API.
