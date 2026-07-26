<p align="center">
  <img src="docs/logo.png" alt="delphi-ai-skills" width="260">
</p>

<p align="center">
  AI coding-agent <strong>skills</strong> for <strong>Delphi</strong> —
  the language and the RTL, plus
  <a href="https://github.com/danieleteti/delphimvcframework">DelphiMVCFramework</a>.
</p>

<p align="center">
  <img src="https://img.shields.io/badge/skills-0.3.0-fbbf24" alt="skills version 0.3.0">
  <img src="https://img.shields.io/badge/Delphi-11%20Alexandria%2B-1a1a1a" alt="Delphi 11 Alexandria and later">
  <img src="https://img.shields.io/badge/DelphiMVCFramework-3.5.0-1a1a1a" alt="targets DelphiMVCFramework 3.5.0">
  <img src="https://img.shields.io/badge/license-Apache--2.0-1a1a1a" alt="Apache 2.0">
</p>

**For every Delphi developer, not only the ones using DMVCFramework.** The `delphi` skill is about the
language itself — what compiles on 11 versus 12 versus 13, object lifetime and `Free`, interfaces and
reference counting, strings and encodings, exceptions, generics and RTTI, threading, conventions. It assumes
no framework and applies to any `.pas` file: a VCL form, a service, a legacy unit, a library. If you write
Delphi and your agent writes Java in Pascal clothing, that skill is the one you want.

Its companion `delphi-code-smells` is for the other half of the job — **reviewing** code rather than writing
it: the compiler warnings that mean a real bug, hunting a memory leak, and making one fail the build.

Building a server on top of that? Then the seven DMVCFramework skills are already here too — REST
controllers, Minimal API, TemplatePro web apps, JSON-RPC, security, testing.

A *skill* is a Markdown file your AI agent loads **on demand**, when your request matches it. It teaches the
agent the **real** API — exact unit names, signatures, attributes, ownership rules, idioms — so it stops
inventing plausible-but-wrong code. Every identifier was copied from the shipped Delphi RTL/VCL source and
the DelphiMVCFramework sources and samples, never written from memory, and a
[checker](#checking-the-skills-themselves) re-verifies all of them on every change.

**Version 0.3.0 — early release.** Verified against **Delphi 13 Florence's RTL** (targeting **11 Alexandria**
and later) and **DelphiMVCFramework 3.5.0** (`silicon`), but not yet battle-tested across many projects:
expect rough edges, and please report them.

Works with Claude Code, Codex, Cursor, Gemini CLI, Windsurf, Continue, and anything else that can read
Markdown instructions.

📝 **Articles about this project** — release announcements, worked sessions and the reasoning behind the
rules — are collected on the author's blog:
**[danieleteti.it/tags/delphi-ai-skills](https://www.danieleteti.it/tags/delphi-ai-skills/)**.

---

## Quick start

**1. Clone**

```bash
git clone https://github.com/danieleteti/delphi-ai-skills.git
```

**2. Install** — run the script for your agent (Windows):

```bat
cd delphi-ai-skills
install_in_claude.bat
```

That is it for Claude Code: it discovers skills on its own. For the other agents see
[Installing](#installing) — there is a script for each.

**3. Start the agent in any Delphi project** and ask. Nothing else to set up: the `delphi` skill needs no
particular project shape.

> *Why does this unit leak? Fix it.*

**If what you are building is a DMVCFramework server**, there is one more step — the DMVC skills add
features to a wizard-generated project, they do not scaffold one from scratch:

> **Delphi IDE → File → New → Other → Delphi Projects → DelphiMVCFramework → New DMVCFramework Application**

Pick the preset you need, accept the defaults, compile and run it once. Then start the agent **inside the
project folder** and ask for what you want:

> *Add a Customers controller with full CRUD, backed by an ActiveRecord entity on table `customers`*

The agent reads the project, loads the right skills, and writes code against the real API.

---

## The skills

| Skill | What it covers | Loads when you… |
|-------|----------------|-----------------|
| **`delphi`** | The language itself, no framework assumed: version gating (what compiles on 11 vs 12 vs 13), inline `var`, memory and lifetime, strings and encodings, exceptions, `System.Generics.Collections`, RTTI, threading, naming conventions. | Write or review any Delphi code — it underpins all the others. |
| **`delphi-code-smells`** | Reviewing code, not writing it: the compiler warnings and hints that mean a real bug, warnings-as-errors, leak detection and how to make a leak fail the build, third-party static analysis, and a catalogue of smells each with a way to find it. | Review, audit or refactor Delphi code — or hunt a leak or an AV. |
| **`dmvcframework`** | The core: engine bootstrap and the server backends, controllers and functional actions, routing attributes, `IMVCResponse`, object-ownership rules, ActiveRecord ORM, the Repository pattern, the DI service container, validation, middleware, JWT, SSE, dotEnv configuration. | Build a REST API or any server-side feature with controller classes. |
| **`dmvcframework-minimal-api`** | The Minimal API: lambda routes with no controller class — route groups (`Prefix`, `MapGet`/`MapPost`/`MapMethods`), type-driven parameter binding, records from the query string, file uploads, endpoint filters vs HTTP filters, `.AsWeb` for TemplatePro/HTMX handlers. | Write routes as anonymous methods instead of controller classes — REST *or* web app. |
| **`dmvcframework-webapp`** | Server-side web apps: TemplatePro templates (inheritance, blocks, filters, partials), fragments, `ViewData` and its ownership rules, cookie/JWT login, static files, the HTMX helpers on the Delphi side. | Render HTML pages and HTMX fragments from Delphi. |
| **`dmvcframework-ui`** | The presentation layer the wizard generates: Bootstrap 5.3, `baselayout.html` blocks, the brand tokens in `style.css`, dark/light mode via `data-bs-theme`, toasts, the HTMX activity classes. | Write markup or CSS for a DMVCFramework web app. |
| **`dmvcframework-security`** | Secure coding, with the DMVCFramework API that implements each control: access control and IDOR, mass assignment, SQL injection, XSS in TemplatePro, CSRF, path traversal, uploads, SSRF and open redirect, security headers, JWT hardening, secrets. | Automatically — the server skills require it for any endpoint that takes client input. |
| **`dmvcframework-jsonrpc`** | JSON-RPC 2.0 services: publishing a controller, which methods are callable, `function` = request vs `procedure` = notification, named and positional parameters, who frees what, error codes, hooks, and the `IMVCJSONRPCExecutor` client. | Expose or consume a JSON-RPC endpoint. |
| **`dmvcframework-testing`** | Integration and unit tests: an in-process `IMVCServer` + `IMVCRESTClient` + DUnitX; CRUD, authentication and authorization test patterns; database fixtures. | Write tests for a DMVCFramework API. |
| **`htmx-skill`** | An index of every page of the official htmx.org documentation, each with a description, so the agent fetches and reads the right page instead of recalling htmx from memory. | Ask about any htmx attribute, trigger/swap modifier, event, header or extension. |

They are complementary: the Minimal API, web-app and JSON-RPC skills assume the core one for entities,
validation and DI, and all of them sit on `delphi` for the language itself. Every server skill requires
`dmvcframework-security` for any endpoint that touches untrusted input.
The web-app skill delegates markup to `dmvcframework-ui` and htmx syntax to `htmx-skill` rather than
duplicating either. **Install them all** — the agent picks the right ones on its own.

### Two things the DMVCFramework skills insist on

Both are about *server* projects. The two Delphi skills have no such rules: they apply to any unit, in any
project, with no layout requirements at all.

**1. Start from a wizard project.** They do not scaffold a project from scratch. Create it in the IDE,
accept the defaults, compile it, then `cd` into the folder and start your agent **there**. The skills detect
the wizard layout (`EngineConfigU.pas`, `RoutesU.pas`, `bin/.env`, …) and add features inside it. If there is
no project, they stop and tell you to create one rather than inventing a half-correct bootstrap.

**2. The server backend is Indy Direct.** For a *new* project: a self-contained executable, no WebModule, no
WebBroker. But an **existing WebBroker project — ISAPI under IIS, an Apache module — is fully supported**:
the skills detect the host, keep it, and never suggest migrating it. Everything above the host (controllers,
routing, ActiveRecord, validation, DI, middleware) is identical on every backend.

---

## Prompts that activate each skill

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

**`htmx-skill`** — htmx reference

> *What does hx-swap="outerHTML swap:1s" actually do?*
> *Which HTMX event fires after the swap completes?*

### Forcing a skill

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

### Checking it worked

Claude Code prints the skill it loaded. If it did not load, say so explicitly:

> *Use the dmvcframework skill. Then create a controller for Orders.*

A ten-second way to tell a skilled agent from an unskilled one — ask:

> *In a DMVCFramework functional action, do I need `ToFree` on the object I return?*

The right answer is **no: the framework frees the returned object, and `ToFree` would free it twice**. An
agent without the skill usually says yes, and its code double-frees.

---

## Installing

Each skill is a folder under `skills/` with a `SKILL.md` inside. Copy the **whole folder** — `dmvcframework`,
`dmvcframework-jsonrpc` and `delphi` have `reference/` files that must sit next to their `SKILL.md`, and two
skills ship `scripts/`.

**Install them all.** They cross-reference each other by name, and the agent loads only what the task needs.

### The scripts (Windows)

Run them from the folder where you cloned this repo. Each one is safe to re-run: it overwrites the skills and
never duplicates the section it adds to your instruction file — the appended block is guarded by an
`<!-- delphi-ai-skills -->` marker.

| Script | What it does |
|--------|--------------|
| `install_in_claude.bat` | Installs for your user (`%USERPROFILE%\.claude\skills`). Claude Code discovers them — nothing else to configure. |
| `install_in_claude.bat <project>` | Installs into that project's `.claude\skills\` instead, so you can commit them for your team. Pass `.` for the current folder. |
| `install_in_codex.bat [project]` | Copies `skills\` into the project **and** appends a Skills section to `AGENTS.md`. |
| `install_in_cursor.bat [project]` | Copies `skills\` **and** writes one `.cursor\rules\*.mdc` per skill (with `alwaysApply: false`, so they load only when relevant). |
| `install_in_gemini.bat [project]` | Copies `skills\` **and** appends a Skills section to `GEMINI.md`. |

Codex, Cursor and Gemini do not auto-discover skills, which is why those scripts also write the pointer — the
agent has to be told the files exist and when to read them.

### Claude Code — by hand

If you would rather not run a script:

```powershell
# PowerShell
Copy-Item -Recurse -Force .\delphi-ai-skills\skills\* "$env:USERPROFILE\.claude\skills\"
```
```bash
# Git Bash / macOS / Linux
cp -r delphi-ai-skills/skills/* ~/.claude/skills/
```

To stay current with a `git pull`, symlink rather than copy (PowerShell, with Developer Mode on or as
Administrator):

```powershell
foreach ($s in Get-ChildItem .\delphi-ai-skills\skills -Directory) {
  New-Item -ItemType SymbolicLink -Force `
    -Path "$env:USERPROFILE\.claude\skills\$($s.Name)" -Target $s.FullName
}
```

### Codex, or any agent that reads `AGENTS.md` — by hand

`install_in_codex.bat` does this for you. By hand: copy `skills/` into your project, then tell the agent the
files exist and when to open them:

```markdown
## Skills

Before writing Delphi or DelphiMVCFramework code, read the relevant skill:

- `skills/delphi/SKILL.md` — the language and the RTL: version gating, lifetime, strings, generics, threading
- `skills/delphi-code-smells/SKILL.md` — code review: compiler warnings, static analysis, memory leaks
- `skills/dmvcframework/SKILL.md` — controllers, ActiveRecord, validation, DI, middleware, servers, dotEnv
- `skills/dmvcframework-minimal-api/SKILL.md` — lambda routes, route groups, filters
- `skills/dmvcframework-webapp/SKILL.md` — TemplatePro views, fragments, ViewData
- `skills/dmvcframework-ui/SKILL.md` — Bootstrap 5.3 layout, style.css, dark mode
- `skills/dmvcframework-security/SKILL.md` — REQUIRED for any endpoint taking client input
- `skills/dmvcframework-jsonrpc/SKILL.md` — JSON-RPC 2.0 services and client
- `skills/dmvcframework-testing/SKILL.md` — DUnitX integration tests
- `skills/htmx-skill/SKILL.md` — index of the official htmx.org docs

Do not write Delphi or DMVCFramework code from memory: the API names in these files are authoritative.
```

That is exactly what `install_in_codex.bat` appends, wrapped in the `<!-- delphi-ai-skills -->` marker it
uses to avoid appending twice.

### Cursor — by hand

`install_in_cursor.bat` does this for you. Cursor loads rules from `.cursor/rules/*.mdc`. Give each skill a rule whose `description` tells Cursor when to
pull it in, and reference the skill file rather than duplicating it:

`.cursor/rules/dmvcframework.mdc`

```markdown
---
description: DelphiMVCFramework core - controllers, ActiveRecord, validation, DI, middleware, servers, dotEnv
globs: ["**/*.pas", "**/*.dpr", "**/*.inc", "**/*.html"]
alwaysApply: false
---

@skills/dmvcframework/SKILL.md
```

Repeat for the other eight skills, changing `description` and the `@` path. Keep `alwaysApply: false` so they
stay out of context until relevant — then `@dmvcframework` in the chat pulls one in on demand.

### Gemini CLI — by hand

`install_in_gemini.bat` does this for you. Otherwise: copy `skills/` into the project and list the files in `GEMINI.md`, exactly as in the `AGENTS.md` example
above. Gemini reads `GEMINI.md` at startup and opens the referenced file when the task matches.

### Windsurf, Continue, and the rest

Same recipe: commit `skills/` to your repo, add a short section to that agent's instruction file listing the
skills and when to read each. The skills are plain Markdown with no tool-specific syntax.

### No configuration at all

Paste the relevant `SKILL.md` into the chat before asking for code. Less convenient, works with any model.

---

## Layout

The core skill keeps its bulk out of the way: `SKILL.md` is the working core (bootstrap, controllers,
responses, ownership, middleware, pitfalls), and the heavy material sits in files the agent opens only when
the task calls for them.

```
check.py                          mechanical validation of every skill - see Checking the skills themselves
install_in_claude.bat             installers - see Installing
install_in_codex.bat
install_in_cursor.bat
install_in_gemini.bat
skills/
  dmvcframework/
    SKILL.md
    reference/servers.md            Indy Direct (default) · HTTP.sys · WebBroker/ISAPI/Apache · FireDAC
    reference/dotenv.md             Boot pattern, profiles, precedence, .env syntax, secrets
    reference/activerecord.md       the ORM: mapping, CRUD, RQL, hooks, soft delete, versioning,
                                    the connection middleware, the automatic REST CRUD controller
    reference/di-and-repository.md  service container · IMVCRepository<T>
    reference/validation.md         validator attributes · OnValidate · the real 422 body
    reference/sse.md                TMVCSSEController · SSEBroker
    scripts/build.bat               build a project with the newest installed Delphi
    scripts/run.bat                 run it
  dmvcframework-minimal-api/SKILL.md
  dmvcframework-webapp/SKILL.md
  dmvcframework-ui/SKILL.md
  dmvcframework-security/SKILL.md
  dmvcframework-jsonrpc/
    SKILL.md
    reference/client.md             IMVCJSONRPCExecutor: calls, notifications, ownership
  dmvcframework-testing/
    SKILL.md
    scripts/run-tests.bat           build and run a DUnitX test project
  delphi/
    SKILL.md                        version gating, the core rules, the reference index
    reference/memory.md             Free/try-finally, interfaces, managed records, ownership
    reference/strings.md            string vs UTF8String vs TBytes, TEncoding, TStringBuilder
    reference/exceptions.md         hierarchy, raise..at, re-raise, what not to catch
    reference/generics-and-rtti.md  Generics.Collections/Defaults, comparers, RTTI, attributes
    reference/concurrency.md        TThread, Synchronize/Queue, TTask, TParallel, the VCL rule
    reference/style.md              docwiki style guide vs community guide vs house style
  delphi-code-smells/
    SKILL.md                        order of attack for a review, the ranked defect table
    reference/static-analysis.md    verified warning/hint codes, $WARN, warnings-as-errors, the tools
    reference/leaks.md              the shipped memory manager, reading a leak report, failing a build on one
    reference/smells.md             the catalogue: bad code, what breaks, the fix, how to detect it
  htmx-skill/SKILL.md
```

---

## Why these skills exist

Ask an agent for a DelphiMVCFramework Minimal API without them and you get confident, well-shaped,
**uncompilable** code: `MapGroup` instead of `Prefix`, `OkResponse` instead of `Ok`, middleware classes that
do not exist, a `ToFree` around the returned object that frees it twice. The names are plausible — they are
what the framework *would* be called if it were ASP.NET.

Each skill was built by running that failure first, documenting the API the framework really has, then
re-running the same task to confirm the agent gets it right.

---

## Versioning

| | |
|---|---|
| **Skills version** | **0.3.0** (pre-1.0) |
| **Targets DelphiMVCFramework** | **3.5.0** (`silicon`) |
| Delphi | The framework supports 10 Seattle and later; the wizard projects these skills assume target 11 Alexandria or later |

The skills version is independent of the framework's.

**While on 0.x**, treat the shape of the skill set as unsettled: skills may be split, merged, renamed or
dropped between minor versions as real use shows what actually helps. 1.0.0 will follow once the set has
proven itself on real projects. From then on: **major** when a skill is removed or restructured in a way that
breaks how you invoke it, **minor** when a skill is added or new API coverage lands, **patch** for a
correction.

**The skills know they can be out of date.** Each one instructs the agent that, when it needs a signature the
skill does not cover, it must *verify rather than guess*: first by asking you for the path to your local
DelphiMVCFramework checkout (reading `sources/` and the matching `samples/` project), otherwise by reading the
official repository —

- Sources: https://github.com/danieleteti/delphimvcframework/tree/master/sources
- Samples: https://github.com/danieleteti/delphimvcframework/tree/master/samples

— and, failing that, by saying plainly that it is not sure. **Where a skill and a sample disagree, the sample
wins**, and the skill has a bug.

**Pointing the agent at your checkout up front makes it sharper.** If you have the framework on disk, say so:
*"the DMVCFramework sources are in C:\DEV\dmvcframework"*.

### Checking the skills themselves

```bash
python check.py
```

Verifies, in about five seconds and with no dependencies: every frontmatter still loads (under 1024
characters, `name` matching the folder), every `reference/` file and sibling skill named actually exists,
**every Delphi identifier in the prose exists in the sources**, and every skill is listed in the installers
and in this README. It exits non-zero on the first defect, so it fits a pre-commit hook or CI.

It reads `C:\DEV\dmvcframework` and your Delphi `source\` tree — override with `DMVC_HOME` and
`DELPHI_SOURCE`. Without either it still runs, and skips the identifier check rather than failing.

It proves a name *exists*, not that it is used correctly: a real API called with the wrong arguments needs a
compiler, and an ownership bug needs to be run. See CLAUDE.md for the two levels above this one.

### Changelog

**0.3.0** — `delphi-code-smells`: the review pass. Compiler warnings and hints that indicate a real bug —
every code produced by running `dcc32` rather than recalled — `$WARN` and warnings-as-errors, leak detection
with the shipped memory manager, how to read a leak report and how to make a leak fail the build, an honest
note on the third-party analysers, and a catalogue of smells where every entry says how to *find* it. In `delphi`, the target
release is now **established rather than assumed**: ask `dcc32.exe --version`, else read the installed Studio
folders, else ask the user, and only then fall back to 11 Alexandria with a `{$IF}` guard (the `.dproj`
`<ProjectVersion>` is explicitly ruled out as a signal: it is the project-file format, not the product), and
an API is verified against **the source tree of the target release** (`Studio\23.0\source` for 12 Athens),
not whichever install is newest. That found a real defect, now fixed: the DUnitX container in
`delphi-code-smells`, `reference/leaks.md` is `TDUnitXServiceLocator` only on 13 Florence, and `TDUnitXIoC`
on 12 Athens. `check.py` now searches every installed release rather than only the newest, and
`DELPHI_SOURCE` accepts a `;`-separated list. Related: a declaration is now explicitly **half** the answer,
and the skills also read a real call site (your own code first, then the RTL's own uses or a framework
sample) before writing a call; when they cannot tell which sources to read they ask for the path and offer to
record it in a `<!-- delphi-local-sources -->` block in `CLAUDE.md` / `AGENTS.md`, so the question is asked
once per project rather than once per session. Also corrected two claims in `delphi`, `reference/memory.md`: the shutdown report names classes only for small
blocks, and it does nothing at all in a module that shares another module's memory manager.

**0.2.0** — two skills added, nine in total.

- **`delphi`** — the language and the RTL, no framework assumed: version gating (what compiles on 11 vs 12 vs
  13), memory and lifetime, strings and encodings, exceptions, generics and RTTI, threading, conventions.
  Identifiers taken from the shipped RTL/VCL source; version boundaries checked against the docwiki release
  by release. Six `reference/` files.
- **`dmvcframework-jsonrpc`** — JSON-RPC 2.0: publishing a service, `function` = request vs `procedure` =
  notification, named and positional parameters, the three ownership rules, error codes, hooks, and the
  `IMVCJSONRPCExecutor` client.
- Fixes in the existing skills: a wrong exception name in the ActiveRecord reference, a duplicated project
  layout that contradicted the wizard-first rule, a DB test example that could not have worked as written.
- `check.py` — mechanical validation of the whole set: frontmatter, links, identifiers against the sources,
  installer and README coverage.

**0.1.0** — first public release. Seven skills, every API name verified against the DelphiMVCFramework 3.5.0
sources and samples.

Some of what an unaided agent gets wrong, and these skills get right: `ToFree` on a returned object is a
double free; the CORS and JWT middleware classes are `TMVCCORSMiddleware` and
`TMVCJWTAuthenticationMiddleware`; `MVCFramework.Validators.CrossField` does not exist; validation triggers on
any validator attribute, not only on `TMVCValidatable`; the DI container is built once in the `.dpr`, not per
request; `ViewData` owns nothing, so you free what you put in it; the Minimal API DSL is `Prefix` and `Ok`,
not `MapGroup` and `OkResponse`; `[MVCRequiresRole]` compiles but does nothing without the role-based auth
handler.

---

## Contributing

Found an API the skills get wrong, or a pattern they are missing? Open an issue or a PR. One rule: every claim
must be verifiable against the DelphiMVCFramework source or a sample project — cite the file. No API names
from memory.

## Credits

The secure-coding skill adapts the topic coverage of [VibeSec](https://github.com/BehiSecc/VibeSec-Skill)
(Apache-2.0) to DelphiMVCFramework — every control is rewritten against the framework's real API.

## License

Apache License 2.0 — see [LICENSE](LICENSE).
