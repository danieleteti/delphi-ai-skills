# Installing

Each skill is a folder under `skills/` with a `SKILL.md` inside. Copy the **whole folder** — `dmvcframework`,
`dmvcframework-jsonrpc` and `delphi` have `reference/` files that must sit next to their `SKILL.md`, and two
skills ship `scripts/`.

**Install them all.** They cross-reference each other by name, and the agent loads only what the task needs.

## The scripts (Windows)

Run them from the folder where you cloned this repo. Each one is safe to re-run: it overwrites the skills and
never duplicates the section it adds to your instruction file — the appended block is guarded by an
`<!-- delphi-ai-skills -->` marker.

| Script | What it does |
|--------|--------------|
| `install_in_claude.bat` | Installs for your user (`%USERPROFILE%\.claude\skills`). Claude Code discovers them — nothing else to configure. |
| `install_in_claude.bat <project>` | Installs into that project's `.claude\skills\` instead, so you can commit them for your team. Pass `.` for the current folder. |
| `install_in_claude.sh [project]` | Same as `install_in_claude.bat`, for macOS and Linux (`~/.claude/skills` without an argument). |
| `install_in_codex.bat [project]` | Copies `skills\` into the project **and** appends a Skills section to `AGENTS.md`. |
| `install_in_cursor.bat [project]` | Copies `skills\` **and** writes one `.cursor\rules\*.mdc` per skill (with `alwaysApply: false`, so they load only when relevant). |
| `install_in_gemini.bat [project]` | Copies `skills\` **and** appends a Skills section to `GEMINI.md`. |

Those scripts also write a pointer (`AGENTS.md`, `GEMINI.md`, a Cursor rule) that names the files and says when
to read them. It works on every version of every tool. Several agents can also discover skills on their own, but
from a folder these scripts do not install into:

| Agent | Discovers skills in | Documented at |
|-------|--------------------|---------------|
| **Claude Code** | `.claude/skills/` only. It does **not** read `.agents/skills/` (checked on Claude Code 2.1.319: a skill placed there was not listed). | [docs](https://code.claude.com/docs/en/skills) |
| **Codex** | `.agents/skills/`, from the working directory up to the repository root, and `~/.agents/skills/` | [docs](https://developers.openai.com/codex/skills) |
| **Cursor** | `.agents/skills/` and `.cursor/skills/`; for compatibility also `.claude/skills/` | [docs](https://cursor.com/docs/skills) |
| **Gemini CLI / Antigravity CLI** | `.agents/skills/` (Gemini CLI also `.gemini/skills/`) | [Gemini CLI](https://geminicli.com/docs/cli/skills/), [Antigravity](https://antigravity.google/docs/skills/) |

So a project that commits `.claude/skills/` (what `install_in_claude.bat .` writes) is found natively by Claude
Code and Cursor; for Codex and Gemini the pointer does the work.

## Claude Code — by hand

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

## Codex, or any agent that reads `AGENTS.md` — by hand

`install_in_codex.bat` does this for you. By hand: copy `skills/` into your project, then tell the agent the
files exist and when to open them:

```markdown
## Skills

Before writing Delphi or DelphiMVCFramework code, read the relevant skill:

- `skills/delphi/SKILL.md` — the language and the RTL: version gating, lifetime, strings, generics, threading
- `skills/delphi-code-smells/SKILL.md` — code review: compiler warnings, static analysis, memory leaks
- `skills/delphi-build/SKILL.md` — building Delphi projects from the command line: msbuild, dcc32/dcc64, warnings as errors, exit codes
- `skills/delphi-firedac/SKILL.md` — FireDAC in plain Delphi: connections, pooling, transactions, parameters and macros, cached updates
- `skills/delphi-security/SKILL.md` — secure coding for desktop, service and client code: hashing, random, TLS, paths, secrets, logs
- `skills/delphi-testing/SKILL.md` — unit tests with DUnitX: fixtures, attributes, assertions, CI exit codes, leak detection
- `skills/dmvcframework/SKILL.md` — controllers, ActiveRecord, validation, DI, middleware, servers, dotEnv
- `skills/dmvcframework-minimal-api/SKILL.md` — lambda routes, route groups, filters
- `skills/dmvcframework-webapp/SKILL.md` — TemplatePro views, fragments, ViewData
- `skills/dmvcframework-ui/SKILL.md` — Bootstrap 5.3 layout, style.css, dark mode
- `skills/dmvcframework-security/SKILL.md` — REQUIRED for any endpoint taking client input
- `skills/dmvcframework-jsonrpc/SKILL.md` — JSON-RPC 2.0 services and client
- `skills/dmvcframework-testing/SKILL.md` — DUnitX integration tests
- `skills/htmx-skill/SKILL.md` — index of the htmx 2.x reference pages
- `skills/exewatch-delphi/SKILL.md` — ExeWatch Delphi SDK: initialization, logging, device info, offline buffering, stack traces

Do not write Delphi or DMVCFramework code from memory: the API names in these files are authoritative.
```

That is exactly what `install_in_codex.bat` appends, wrapped in the `<!-- delphi-ai-skills -->` marker it
uses to avoid appending twice.

## Cursor — by hand

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

Repeat for the other fourteen skills, changing `description` and the `@` path. Keep `alwaysApply: false` so they
stay out of context until relevant — then `@dmvcframework` in the chat pulls one in on demand.

## Gemini CLI — by hand

`install_in_gemini.bat` does this for you. Otherwise: copy `skills/` into the project and list the files in `GEMINI.md`, exactly as in the `AGENTS.md` example
above. Gemini reads `GEMINI.md` at startup and opens the referenced file when the task matches.

## Windsurf, Continue, and the rest

Same recipe: commit `skills/` to your repo, add a short section to that agent's instruction file listing the
skills and when to read each. The skills are plain Markdown with no tool-specific syntax.

## No configuration at all

Paste the relevant `SKILL.md` into the chat before asking for code. Less convenient, works with any model.
