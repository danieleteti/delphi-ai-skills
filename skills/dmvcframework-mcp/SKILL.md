---
name: dmvcframework-mcp
description: Use when adding or changing MCP (Model Context Protocol) tools, resources or prompts in a DelphiMVCFramework project generated with the wizard's "MCP Server" preset or MCP options - the mcp-server-delphi library (MVCFramework.MCP.* units), TMCPToolProvider, TMCPResourceProvider, TMCPPromptProvider, TMCPToolResult, the /mcp endpoint, the stdio transport, or the REST bridge (RegisterFromEngine). Triggers on "MCP", "MCP server", "MCP tool", "Model Context Protocol", "tool provider", "Tools.SampleU", "MCPTool", "MCPParam", "MCPResource", "MCPPrompt", "TMCPServer", "expose to an AI agent", ".mcp.json", "--transport stdio".
---

# DMVCFramework — MCP tools, resources and prompts

The MCP API is **not** in DelphiMVCFramework. It comes from the external library
[mcp-server-delphi](https://github.com/danieleteti/mcp-server-delphi) (units `MVCFramework.MCP.*`), which the
wizard requires in the library path. Every name below is copied from its `sources/` and from the units the
wizard generates (`Tools.SampleU.pas`, `Resources.SampleU.pas`, `Prompts.SampleU.pas`).

**Verified against mcp-server-delphi 0.10.0** (`MCP_SERVER_LIBRARY_VERSION` in `MVCFramework.MCP.Types.pas`,
commit `7b6a4c7`). The DMVCFramework 3.5 wizard accepts 0.9.0 or later, and the API grew in between:

| Feature | Needs |
|---|---|
| Everything not listed below | 0.9.0 |
| `[MCPReadOnly]`, `[MCPNonDestructive]`, `[MCPIdempotent]`, `[MCPClosedWorld]`, `[MCPToolTitle]` | 0.10.0 |
| `Context`, `HasContext`, `Transport` on a provider | a 0.10.0 copy whose `MVCFramework.MCP.Types.pas` declares `HasContext` (added after the 0.10.0 tag, same version string) |

Before using a feature of the table, check the project's copy of the library (the folder in the library path:
`grep -n "MCP_SERVER_LIBRARY_VERSION\|HasContext" <library>\sources\MVCFramework.MCP.Types.pas`). If it is
older, tell the user to update the library; do not work around it.

## When in doubt about an API — verify it, never guess

Never invent an identifier. If you need something this skill does not cover, read the library's `sources/`
(ask the user where it is if it is not in the library path) or the
[repository](https://github.com/danieleteti/mcp-server-delphi/tree/main/sources). If you still cannot verify
it, **say so**. This library does not follow the spellings of the MCP SDKs of other languages: there is no
`[MCPDestructive]`, no `[MCPResourceTemplate]` (a template is an `[MCPResource]` whose URI has `{name}`), no
`TMCPTool`, no `AddTool`, no `structuredContent`/`outputSchema`, no `TMCPContent`, no `Context.User` or
`Context.AuthenticatedUser`, no `ToFree`.

## Delphi Language Target

Delphi 11 Alexandria or later. For the language and the RTL — lifetime, strings, generics — load the
**`delphi`** skill. For everything around the endpoint that is plain DMVCFramework (`EngineConfigU.pas`,
filters, JWT, `dotEnv`, services) load **`dmvcframework`**.

---

**REQUIRED REFERENCE — `dmvcframework-security`.** An MCP tool is a function that a language model decides to
call with arguments it made up, possibly steered by text it read somewhere else (prompt injection). Treat
every tool argument as untrusted input: parameterized SQL, no path built from an argument, no shell command.
Follow that skill before shipping a tool that writes, deletes or reads anything sensitive.

---

## 0. STOP — start from a wizard project

**Never create the project, the `.dpr` bootstrap or the `/mcp` endpoint by hand.**

**Step 1 — detect it.** A wizard project with MCP has:

```
*.dpr                    uses MVCFramework.MCP.Server (+ MVCFramework.MCP.Stdio and
                         MVCFramework.MCP.TransportConf when stdio is on); RunMCPStdio / RunServer
EngineConfigU.pas        the guards on /mcp, then AEngine.PublishObject(... CreatePublishedEndpoint ..., '/mcp')
Tools.SampleU.pas        TSampleTools = class(TMCPToolProvider)  - the sample tool "hello"
Resources.SampleU.pas    TSampleResources (when "resources and prompts" was ticked)
Prompts.SampleU.pas      TSamplePrompts
bin/.env                 mcp.auth.token, mcp.allowed_origins, mcp.http.host
.mcp.json, opencode.json the stdio launch line for MCP clients (MCP Server preset)
```

Read the three sample units and `EngineConfigU.pas` before writing anything, and follow them.

**Step 2 — if there is no MCP in the project, stop.** Do not add the endpoint by hand. Tell the user:

> This skill works on a DMVCFramework project generated with MCP, and I do not see one here. Please create it
> with **File → New → Other → Delphi Projects → DelphiMVCFramework → New DMVCFramework Application**: pick the
> **MCP Server** preset (or tick the MCP options on another preset). The wizard needs
> [mcp-server-delphi](https://github.com/danieleteti/mcp-server-delphi) in the library path and warns if it
> is missing or too old. Compile and run it once, then start me in the project folder.

If the project does not compile because `MVCFramework.MCP.*` units are not found, the library is not in the
library path: that is the fix, not rewriting the units.

## 1. Where the code goes

One unit per area, named like the sample: `Tools.<Area>U.pas` with `T<Area>Tools`,
`Resources.<Area>U.pas`, `Prompts.<Area>U.pas`. In the IDE the Project Manager context menu has
**New MCP Tool Provider...**, which writes that unit. Without the IDE, copy the shape of `Tools.SampleU.pas`.

- The unit **registers itself** in its `initialization` section:
  `TMCPServer.Instance.RegisterToolProvider(T<Area>Tools)` (`RegisterResourceProvider`,
  `RegisterPromptProvider`). There is no other registration step.
- Add the unit to the `.dpr` `uses` **next to `Tools.SampleU`**, i.e. after `MVCFramework.MCP.TransportConf`
  (that unit must come before every provider unit). A unit that is not in the `uses` clause is never
  linked, so its tools silently do not exist.
- Delete or replace the sample providers when the real ones exist: `hello` is visible to every client.

### Which unit declares what

| Identifier | Unit |
|---|---|
| `MCPTool`, `MCPParam`, `MCPReadOnly`, `MCPNonDestructive`, `MCPIdempotent`, `MCPClosedWorld`, `MCPToolTitle`, `MCPResource`, `MCPPrompt`, `MCPPromptArg`, `TMCPParamPresence` | `MVCFramework.MCP.Attributes` |
| `TMCPToolProvider`, `TMCPToolResult`, `TMCPDataSetFormat`, `MCPDataSetToTable` | `MVCFramework.MCP.ToolProvider` |
| `TMCPResourceProvider`, `TMCPResourceResult` | `MVCFramework.MCP.ResourceProvider` |
| `TMCPPromptProvider`, `TMCPPromptResult`, `PromptMessage`, `PromptImageMessage`, `PromptResourceMessage` | `MVCFramework.MCP.PromptProvider` |
| `TMCPTransportKind`, `EMCPContextNotAvailable`, `MCP_ENDPOINT` | `MVCFramework.MCP.Types` — add it when you compare `Transport` (`E2003 Undeclared identifier: 'TMCPTransportKind'` otherwise) |
| `TMCPServer` (registration) | `MVCFramework.MCP.Server`, in the `implementation` `uses` |
| `TMCPBridgeOptions`, `RegisterFromEngine` | `MVCFramework.MCP.Bridge` |
| `TJDOJsonObject` | `JsonDataObjects` |
| `LogI`, `LogW`, `LogE` | `MVCFramework.Logger` |

## 2. Tools

```pascal
unit Tools.OrdersU;

interface

uses
  MVCFramework.MCP.ToolProvider,
  MVCFramework.MCP.Attributes;

type
  TOrdersTools = class(TMCPToolProvider)
  public
    [MCPTool('find_orders', 'Finds orders by customer name. Returns id, customer, total and status.')]
    [MCPReadOnly]
    function FindOrders(
      [MCPParam('Part of the customer name; empty for every customer', TMCPParamPresence.Optional)] const customer: string;
      [MCPParam('Maximum number of rows; 0 or missing means 50', TMCPParamPresence.Optional)] const limit: Integer): TMCPToolResult;

    [MCPTool('cancel_order', 'Cancels an open order. A shipped order cannot be cancelled.')]
    [MCPIdempotent]
    function CancelOrder(
      [MCPParam('Order id, for example 1042')] const order_id: Integer): TMCPToolResult;
  end;

implementation

uses
  System.SysUtils,
  MVCFramework.MCP.Server;

function TOrdersTools.FindOrders(const customer: string; const limit: Integer): TMCPToolResult;
var
  lLimit: Integer;
begin
  lLimit := limit;
  if lLimit <= 0 then
    lLimit := 50;                     // a missing optional Integer arrives as 0
  // ... open a dataset with a parameterized query, then:
  // Result := TMCPToolResult.FromDataSet(lDataSet, TMCPDataSetFormat.Table);   // you still free lDataSet
  Result := TMCPToolResult.Text(Format('No orders for "%s" (limit %d)', [customer, lLimit]));
end;

function TOrdersTools.CancelOrder(const order_id: Integer): TMCPToolResult;
begin
  if order_id <= 0 then
    Exit(TMCPToolResult.Error(Format('Order %d does not exist. Use find_orders to get a valid id.', [order_id])));
  // ... cancel it
  Result := TMCPToolResult.Text(Format('Order %d cancelled', [order_id]));
end;

initialization
  TMCPServer.Instance.RegisterToolProvider(TOrdersTools);

end.
```

### The rules the compiler will not tell you

- **The method must be `public`** (a `private` one compiles and is silently missing from `tools/list`) and
  return `TMCPToolResult`. `[MCPTool(name, description)]`: the name is
  what the model calls, the description is the only thing it reads to decide *when* to call it — say what it
  does, what it returns, and when not to use it.
- **Tool name: `^[a-zA-Z0-9_-]{1,128}$`** (letters, digits, `_`, `-`; no dot, no space). The MCP spec allows
  more, but OpenAI/Anthropic-compatible clients reject the *whole* tool list when one name breaks it. The
  server only logs a warning at start-up. Names are unique case-insensitively across all providers (a
  duplicate raises at registration).
- **Every parameter needs `[MCPParam(description)]`** — a parameter without it raises at registration and
  the server does not start. The JSON property name is the **Delphi parameter name** (matched
  case-insensitively), so name parameters the way the model should write them (`order_id`, `customer`).
- **`MCPParam` defaults to `TMCPParamPresence.Required`; `MCPPromptArg` defaults to `Optional`.** Write the
  presence explicitly when it matters.
- **Supported parameter types: `string`, `Integer`, `Int64`, `Double`, `Boolean`.** The call converts every
  float as `Double` and every enumeration as `Boolean`, and rejects records, objects and arrays at call time
  ("Unsupported parameter type"). Take a date as an ISO 8601 `string`, an enum as a `string` you map, a list as
  a comma-separated `string`.
- **A missing optional argument arrives as `''`, `0`, `0.0` or `False`.** There is no "not given" flag: design
  the value so that the default means "not given" (as `limit` above), or make it a `string`.
- **A missing required argument is a protocol error** (`Missing required parameter: <name>`), raised before
  your method runs. The check is presence only: validate ranges and formats yourself.
- **A new provider instance is created for every call and freed after it.** Do not keep state in fields; use
  a database, a service, or a thread-safe singleton. Calls on HTTP run concurrently.
- **Never write to stdout** (`Writeln`, `Write`) in a provider: on stdio stdout *is* the protocol and one stray
  line breaks the client. Log with `LogI` / `LogW` / `LogE` (`MVCFramework.Logger`): in stdio mode
  `MVCFramework.MCP.TransportConf` turns the console logger off, so logs go to the log file only.

### Results — `TMCPToolResult` (record, `MVCFramework.MCP.ToolProvider`)

| Call | Sends |
|---|---|
| `TMCPToolResult.Text(s)` | one text item |
| `TMCPToolResult.Error(s)` | one text item with `isError: true` |
| `TMCPToolResult.JSON(lJsonObject)` | the object serialized as **text** — you still own and free `lJsonObject` |
| `TMCPToolResult.FromObject(lObj)` / `FromCollection(lList)` | DMVC serializer, as text — you free the object/list |
| `TMCPToolResult.FromRecord(@lRec, TypeInfo(TMyRecord))` | a record as JSON text (it is **not** generic: no `FromRecord<T>`) |
| `TMCPToolResult.FromDataSet(lDataSet)` | one JSON object per row; `FromDataSet(lDataSet, TMCPDataSetFormat.Table)` writes a pipe table with the header once — far fewer tokens. You free the dataset |
| `TMCPToolResult.FromValue(x)` | an `Integer`, `Int64`, `Double` or `Boolean` as text |
| `TMCPToolResult.Image(base64, mime)`, `Audio(...)`, `Resource(uri, text, mime)`, `ResourceBlob(...)`, `FromStream(stream, mime)` | other content types; `FromStream` does not free the stream |
| `.AddText(s)`, `.AddImage(...)`, `.AddResource(...)` | append items: `Result := TMCPToolResult.Text('Done').AddText(lDetails);` |

**Every helper copies what you pass and the caller keeps ownership.** The result record frees its own JSON:
never `Free` a `TMCPToolResult`, never call `ToJSON` on it yourself. There is no structured output: JSON
always travels as text, which models read fine.

### Errors — return `Error`, do not raise, for anything the model can fix

| In the tool | What the client gets |
|---|---|
| `Exit(TMCPToolResult.Error('Order 7 is shipped: it cannot be cancelled'))` | a normal result with `isError: true` and your text. The model reads it and can retry or explain. Same on stdio and HTTP, Debug and Release |
| an exception escapes (`raise EOrderNotFound.Create(...)`) | a **JSON-RPC error**, not a tool result. stdio: `{"code":-32603,"message":"Internal error: <E.Message>"}`. HTTP: code `0`, message `E.Message` in a DEBUG build but `Internal server error` in RELEASE (unless the exception descends from `EMVCException`) |
| unknown tool name | a JSON-RPC error raised the same way (stdio: `-32603 Internal error: Tool not found: <name>`); clients on protocol 2026-07-28 get `-32602 Unknown tool: <name>` |

So: catch the exceptions you expect (not found, rule broken, validation) and turn them into
`TMCPToolResult.Error` with a message that tells the model what to do next. Let only bugs escape.

### Annotations are hints, not security

`[MCPReadOnly]`, `[MCPNonDestructive]`, `[MCPIdempotent]`, `[MCPClosedWorld]` and `[MCPToolTitle('...')]` go
on the tool method and become `annotations` in `tools/list` (`readOnlyHint`, `destructiveHint: false`,
`idempotentHint`, `openWorldHint: false`, `title`). A host may use them to auto-approve a read-only tool or ask
before a destructive one. **They restrict nothing**: any client that can reach the server can call any tool.
Without `[MCPNonDestructive]` a tool is assumed destructive, which is the safe default. Who may call is decided
in section 5.

### Who is calling — `Context` (HTTP only)

```pascal
function TOrdersTools.CancelOrder(const order_id: Integer): TMCPToolResult;
begin
  if HasContext and not Context.LoggedUser.Roles.Contains('admin') then
    Exit(TMCPToolResult.Error('Only an admin can cancel orders'));
  if HasContext then
    LogI('cancel_order ' + order_id.ToString + ' by ' + Context.LoggedUser.UserName);
  // ...
end;
```

- `Context` is the `TWebContext` of the `/mcp` request: `LoggedUser`, headers, as in a controller.
- With the wizard's bearer token, `Context.LoggedUser.UserName` is the name paired with the token in
  `EngineConfigU.pas` (the project name) — one shared identity, no roles. With the wizard's JWT option it is
  the user of the token, with its roles.
- **On stdio there is no context**: `HasContext` is `False` and reading `Context` raises
  `EMCPContextNotAvailable`. `Transport` (`TMCPTransportKind.Http` / `TMCPTransportKind.Stdio`) tells which.
  Always test `HasContext` first, and decide what the tool does on stdio, where it runs with the rights of the
  local user who started the executable.

## 3. Resources

Read-only data the client can list and fetch by URI. The method signature is checked at registration (a
mismatch stops the server):

```pascal
uses
  MVCFramework.MCP.ResourceProvider,
  MVCFramework.MCP.Attributes;

type
  TOrdersResources = class(TMCPResourceProvider)
  public
    // static: exactly one parameter, the URI
    [MCPResource('orders://statuses', 'Order statuses', 'The statuses an order can have', 'application/json')]
    function GetStatuses(const URI: string): TMCPResourceResult;
    // template: the URI, then one string per {placeholder}, same names, same order
    [MCPResource('orders://{id}', 'Order', 'One order by id', 'application/json')]
    function GetOrder(const URI, id: string): TMCPResourceResult;
  end;

function TOrdersResources.GetOrder(const URI, id: string): TMCPResourceResult;
begin
  Result := TMCPResourceResult.Text(URI, '{"id":' + id.ToInteger.ToString + '}', 'application/json');
end;
```

- `MCPResource(URI, Name, Description, MimeType)`; `MimeType` defaults to `'text/plain'`. Static resources go to
  `resources/list`, templates to `resources/templates/list`.
- Templates are RFC 6570 level 1 only: plain `{name}`, each matching one path segment (no `/`). `{+x}`, `{?x}`
  raise at registration. Every variable arrives as `string`: convert and validate it (`id.ToInteger` raises on
  garbage — the model can send anything).
- Results: `TMCPResourceResult.Text(URI, Text, MimeType)` or `TMCPResourceResult.Blob(URI, Base64, MimeType)`;
  pass the `URI` you received.
- A URI that matches nothing gets `Resource not found: <uri>` from the library; for an id that does not exist,
  raise (a resource has no `isError` result).
- Register with `TMCPServer.Instance.RegisterResourceProvider(TOrdersResources)`.

## 4. Prompts

Reusable prompt templates the user picks in the client (not called by the model on its own):

```pascal
uses
  JsonDataObjects,
  MVCFramework.MCP.PromptProvider,
  MVCFramework.MCP.Attributes;

type
  TOrdersPrompts = class(TMCPPromptProvider)
  public
    [MCPPrompt('explain_order', 'Explains the state of an order to a customer')]
    [MCPPromptArg('order_id', 'The order id', TMCPParamPresence.Required)]
    [MCPPromptArg('tone', 'formal or friendly; default formal', TMCPParamPresence.Optional)]
    function ExplainOrder(const Arguments: TJDOJsonObject): TMCPPromptResult;
  end;

function TOrdersPrompts.ExplainOrder(const Arguments: TJDOJsonObject): TMCPPromptResult;
var
  lTone: string;
begin
  if Arguments.S['order_id'].Trim.IsEmpty then
    raise Exception.Create('order_id is required');
  lTone := Arguments.S['tone'];
  if lTone.IsEmpty then
    lTone := 'formal';
  Result := TMCPPromptResult.Create('Order explanation', [
    PromptMessage('user', 'Explain the state of order ' + Arguments.S['order_id'] + ' in a ' + lTone + ' tone.'),
    PromptMessage('assistant', 'I will look the order up with find_orders first.')]);
end;
```

- One parameter, `const Arguments: TJDOJsonObject` (from `JsonDataObjects`); it is not yours to free. A missing
  argument reads as `''` (`Arguments.S[...]`).
- **`TMCPParamPresence.Required` on a prompt argument is only advertised** in `prompts/list`; the library does
  not enforce it. Check it in the method.
- Messages: `PromptMessage(Role, Text)`, `PromptImageMessage(Role, Base64, MimeType)`,
  `PromptResourceMessage(Role, URI, Text, MimeType)`; roles are `'user'` and `'assistant'`.
  `TMCPPromptResult.Create(Description, [messages])`.
- Register with `TMCPServer.Instance.RegisterPromptProvider(TOrdersPrompts)`.

## 5. Security — who may call the server

The library has **no per-tool permission**. Access is decided in three places, all generated by the wizard:

1. **HTTP `/mcp`** is guarded in `EngineConfigU.pas`, before `PublishObject`: `BearerAuthHTTPFilter` with the
   token `mcp.auth.token` from `bin/.env` (or the JWT filters with the JWT option), `AllowedMethodsHTTPFilter`
   (POST, DELETE), `TMCPServer.Instance.AllowedOrigins` from `mcp.allowed_origins`, and `mcp.http.host`
   (`localhost` by default). Keep the guards first; never move `PublishObject` above them. The token travels
   in clear over plain HTTP: expose it beyond localhost only behind TLS. Keep `.env` out of version control.
2. **Inside a tool**, for a finer rule (roles, ownership of a record): check `Context.LoggedUser` as in
   section 2 and return `TMCPToolResult.Error`. This needs an identity per user, i.e. the JWT option; the
   static bearer token is one shared identity.
3. **stdio** has no network surface: whoever can start the executable can call every tool. Do not put a tool
   on a server that runs over stdio if the local user must not run it.

`dmvcframework-security` covers the filters, JWT and secrets in detail.

## 6. Running and testing

- **stdio** (the MCP Server preset's default): MCP clients start `bin\<Project>.exe --transport stdio`; the
  wizard writes `.mcp.json` (Claude Code) and `opencode.json` with that line. With `MCPDefaultTransportStdio`
  in the `.dpr` (MCP Server preset), no `--transport` means stdio too, and the program says so on stderr. In
  stdio mode `ConfigureEngine` does not run: nothing set
  up in `EngineConfigU.pas` (filters, `PublishObject`, the bridge) exists there; services registered in
  `ServicesU.pas` do.
- **HTTP**: `bin\<Project>.exe --transport http` serves `POST /mcp` on `dmvc.server.port`, with
  `Authorization: Bearer <mcp.auth.token>`. The HTTP server refuses to start when the token is empty.
- After adding a tool, build, then check it is listed. A quick stdio session (one JSON object per line on
  stdin; protocol `2025-03-26` needs `initialize` first):

```json
{"jsonrpc":"2.0","id":1,"method":"initialize","params":{"protocolVersion":"2025-03-26","capabilities":{},"clientInfo":{"name":"smoke","version":"1"}}}
{"jsonrpc":"2.0","method":"notifications/initialized"}
{"jsonrpc":"2.0","id":2,"method":"tools/list"}
{"jsonrpc":"2.0","id":3,"method":"tools/call","params":{"name":"cancel_order","arguments":{"order_id":0}}}
```

  On the first request the log gets a summary (`MCP: 3 tool(s): ...`, resources, prompts) plus a warning for
  every tool name clients would reject.

## 7. The REST bridge — prototyping only

With the wizard's REST bridge option, `EngineConfigU.pas` ends with
`TMCPServer.Instance.RegisterFromEngine(AEngine, '<base URL>', TMCPBridgeOptions.Create.ExcludeMethods([httpDELETE]))`
(unit `MVCFramework.MCP.Bridge`): every REST action becomes a tool that calls the server itself over HTTP.

- HTTP transport only (it is set up in `ConfigureEngine`). Tool names and descriptions are derived from routes,
  so they are poor tool descriptions; the wizard's comment says it plainly: replace them with hand-written
  tools before production.
- `TMCPBridgeOptions` (fluent): `OnlyControllers([...])`, `ExcludeMethods([...])`, `ExcludePath(regex)` (matched
  against the `MVCPath` of controller + action, **without** the engine prefix), `Header(name, value)` — a fixed
  header on every call, e.g. `Header('Authorization', 'Bearer ' + lServiceToken)` so the REST filters see a
  service identity.
- A REST answer of HTTP 400 or more becomes a tool result with `isError` and text `HTTP <status>: <body>`; the
  REST route's own role checks still apply.

## Common mistakes

| Wrong | Right |
|---|---|
| `[MCPDestructive]` | does not exist: without `[MCPNonDestructive]` a tool is already treated as destructive |
| `[MCPTool(...)]` on a `private` / `protected` method | `public`: a private tool compiles (hint H2219) and is silently missing from `tools/list` |
| `[MCPResourceTemplate('x://{id}')]`, `GetOrder(const URI: string)` | `[MCPResource('x://{id}', ...)]` + `GetOrder(const URI, id: string)`; a wrong signature stops the server at start-up |
| `TMCPParamPresence.Required` on an `MCPPromptArg` taken as enforced | check the argument in the method |
| a parameter without `[MCPParam]` | every parameter needs it, or the server does not start |
| `TDateTime`, `Currency`, an enum, a record as a tool parameter | `string` / `Integer` / `Int64` / `Double` / `Boolean` only |
| `raise` for "not found" | `Exit(TMCPToolResult.Error('...what to do instead...'))` |
| `lJson := TJDOJsonObject.Create; Result := TMCPToolResult.JSON(lJson);` and no `Free` | a leak: `JSON` copies; free `lJson` in `finally` |
| `FromRecord<TMyRecord>(r)` | `FromRecord(@r, TypeInfo(TMyRecord))` |
| state in provider fields | one instance per call |
| `Context.LoggedUser` with no check | `if HasContext then ...` — it raises on stdio |
| `Writeln` for debugging | `LogI`; stdout is the stdio protocol |
| relying on `[MCPReadOnly]` to stop a client | guards on `/mcp` + checks in the tool |
| a new unit not in the `.dpr` `uses` | add it after `MVCFramework.MCP.TransportConf`, next to `Tools.SampleU` |
