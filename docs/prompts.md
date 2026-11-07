# Prompts that activate each skill

You do not normally "call" a skill. You describe the task, and the agent matches it against each skill's
description. The strongest trigger is **naming the technology**: *"create a controller"* is ambiguous,
*"create a **DMVCFramework** controller"* is not; *"fix this leak"* is ambiguous, *"fix this leak in my
**Delphi** unit"* is not. Once a skill is loaded, the rest of the conversation keeps it.
When you want to be certain, name the skill outright — see [Forcing a skill](#forcing-a-skill).

**`delphi`** — the language and the RTL, no framework assumed. The one skill that applies to *any* `.pas`
file, so it is listed first: it is what keeps the agent from writing C# in Pascal clothing.

> *Does this unit compile on Delphi 11, or am I using Athens-only syntax?*
> *Find the memory leak in this unit*
> *This interface reference causes an access violation on shutdown — why?*
> *Rewrite this loop with inline `var` and a `for-in`*
> *Should this be a `TObjectList<T>` with `OwnsObjects` or a plain `TList<T>`?*
> *Convert this string to UTF-8 bytes and back without mangling it*
> *This code runs in a thread and touches a VCL label — what is wrong with it?*
> *Which unit is `IncMonth` in?*

**`delphi-code-smells`** — the review pass, and the leak hunt

> *Review this unit and tell me what is actually wrong with it, not the style*
> *This service leaks memory over a few days — find it*
> *Which compiler warnings am I ignoring that mean a real bug?*
> *Make a memory leak fail the build*
> *Why does this AV only happen on shutdown?*

**`delphi-firedac`** — FireDAC in plain Delphi

> *Why are my rows committed when I close the connection without calling Commit?*
> *Set up FireDAC connection pooling for a Windows service*
> *Insert 10,000 rows with array DML*
> *Why does RecordCount return 50?*
> *Move this BDE dataset code to FireDAC*

**`delphi-testing`** — DUnitX

> *Create a DUnitX console test project for this unit*
> *Make the CI build fail when a test fails*
> *Why does a test that leaks memory pass?*
> *Write a golden-master test for this report, ignoring the timestamp line*

**`delphi-build`** — command-line builds

> *Build this project for Win64 and show me the first error*
> *Turn W1035 into an error in the build*
> *Why does msbuild build Debug when I passed Configuration=Release?*

**`delphi-security`** — desktop, service and client code

> *How should this desktop app store user passwords?*
> *Is THTTPClient checking the server certificate?*
> *Is this check enough to stop path traversal?*
> *What must I keep out of this log?*

**`dmvcframework`** — REST API, ORM, DI, validation

> *Create a DMVCFramework REST controller for Customers with GET/POST/PUT/DELETE*
> *Add a TMVCActiveRecord entity mapped to the `orders` table with a nullable delivery date*
> *Validate this DTO: name required, email valid, age between 18 and 120*
> *Register a service in the DI container and inject it into the controller*
> *Move the port and the connection string into .env*
> *Add JWT authentication to my DMVC API*
> *Push live updates to the browser with SSE*

**`dmvcframework-minimal-api`** — lambda routes

> *Write this as a DMVCFramework Minimal API — no controller classes*
> *Add a MapGet route with a route parameter and a query-string filter*
> *Protect the /admin route group with an auth filter*
> *Handle a file upload in a minimal API endpoint*

**`dmvcframework-webapp`** — TemplatePro + HTMX

> *Add a page that lists customers, using TemplatePro*
> *Return an HTMX fragment when the request comes from htmx, the full page otherwise*
> *Set up template inheritance with a baselayout*
> *Add cookie-based JWT login to my web app*

**`dmvcframework-ui`** — layout and CSS

> *Add a Customers entry to the navbar*
> *Style this list as Bootstrap cards*
> *Show a toast when the customer is saved*
> *Make this table look right in dark mode*

**`dmvcframework-security`** — usually loads on its own, pulled in by the others. Ask it directly for a review:

> *Review this controller for security issues*
> *Can a user read someone else's order through this endpoint?*
> *Is this file upload safe?*

**`dmvcframework-testing`** — DUnitX

> *Write integration tests for the Customers endpoints*
> *Add a test that a POST with an invalid email returns 422*
> *Add a test that user B cannot read user A's order*

**`dmvcframework-jsonrpc`** — JSON-RPC 2.0

> *Expose these service methods over JSON-RPC*
> *Why is my published method not found by the client?*
> *Call this JSON-RPC endpoint from a Delphi client*
> *Add a notification method that the client fires without waiting for a result*
> *Return a proper JSON-RPC error with a custom code instead of a 500*
> *Who frees the object I return from an RPC method?*

**`exewatch-delphi`** — the ExeWatch SDK, for projects that use it

> *Add ExeWatch to this VCL app: initialize it, log errors and send stack traces*
> *What happens to ExeWatch logs when the network is down?*

**`htmx-skill`** — htmx reference

> *What does hx-swap="outerHTML swap:1s" actually do?*
> *Which HTMX event fires after the swap completes?*

## Forcing a skill

Auto-matching is a heuristic. When the task is ambiguous, when the agent already answered from memory, or
when you simply want the guarantee, name the skill yourself. **Naming it in plain words works on every
agent** — it is a file the agent can open:

> *Use the `delphi` skill, then review this unit for lifetime bugs.*
> *Read `skills/dmvcframework-jsonrpc/SKILL.md` first, then expose TOrdersService over JSON-RPC.*

Per agent, the shortest way:

| Agent | Force it with |
|-------|--------------|
| **Claude Code** | Type `/` and the skill name — `/delphi`, `/dmvcframework-jsonrpc`. Installed skills show up in the slash-command list. Naming it in the prompt works too. |
| **Codex** (`AGENTS.md`) | Reference the path: *"Read `skills/delphi/SKILL.md`, then …"*. The `AGENTS.md` section the installer writes tells it the files exist; the path makes it certain. |
| **Cursor** | `@`-mention the rule or the file: `@dmvcframework` (the `.mdc` rule) or `@skills/delphi/SKILL.md`. |
| **Gemini CLI** (`GEMINI.md`) | Same as Codex — name the path in the prompt. |
| **Anything else** | Paste or `@`-attach the `SKILL.md`. Plain Markdown, no tool-specific syntax. |

To keep a skill on for a whole session, put the instruction in your first message: *"For everything in this
session, follow `skills/delphi/SKILL.md` and `skills/dmvcframework/SKILL.md`."*

Making it permanent for a project: `install_in_claude.bat .` installs into `.claude/skills` so the skills
travel with the repository, and the `AGENTS.md` / `GEMINI.md` / `.cursor/rules` files the other installers
write are committed alongside — every agent that opens the project then finds them without being told.

## Checking it worked

Claude Code prints the skill it loaded. If it did not load, say so explicitly:

> *Use the dmvcframework skill. Then create a controller for Orders.*

A ten-second way to tell a skilled agent from an unskilled one — ask:

> *In a DMVCFramework functional action, do I need `ToFree` on the object I return?*

The right answer is **no: the framework frees the returned object, and `ToFree` would free it twice**. An
agent without the skill usually says yes, and its code double-frees.
