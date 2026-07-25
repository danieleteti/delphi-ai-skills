# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## What this repository is

This repo contains **no code**. It is a set of AI-agent *skills* — Markdown documents that teach a coding
agent the real API of [DelphiMVCFramework](https://github.com/danieleteti/delphimvcframework), so the agent
stops inventing plausible-but-wrong Delphi identifiers.

The product is prose. The failure mode is a confidently wrong API name that costs a user a compile error.
Everything below exists to prevent that.

## The iron rule

**Every Delphi identifier written into a skill must be copied from the framework source. Never from memory.**

The framework lives at `C:\DEV\dmvcframework` on this machine (`sources/` and `samples/`); otherwise read
[sources](https://github.com/danieleteti/delphimvcframework/tree/master/sources) and
[samples](https://github.com/danieleteti/delphimvcframework/tree/master/samples).

- A skill and a sample disagree → **the sample wins**, and the skill has a bug.
- Cannot verify something → say so in the skill, or leave it out. Do not guess.
- The samples document *usage*; `sources/` documents *signatures*. You usually need both.

Real bugs this rule caught, all of which read as perfectly plausible: `ToFree` on a returned object (double
free — the framework already frees it), `TCORSMiddleware` (it is `TMVCCORSMiddleware`),
`MVCFramework.Validators.CrossField` (no such unit), `[MVCFromBody(bvSkip)]` (the enum is `bvDoNotValidate`),
`Context.ServiceContainer` (only `ServiceContainerResolver` exists), an invented 422 response body.

## Layout

```
skills/<skill-name>/SKILL.md          one skill; frontmatter + body
skills/dmvcframework/reference/*.md   heavy material the agent opens on demand
skills/*/scripts/*.bat                build/run helpers shipped with a skill
install_in_{claude,codex,cursor,gemini}.bat
docs/logo.png
```

`skills/dmvcframework` is the core; the others (`-minimal-api`, `-webapp`, `-ui`, `-security`, `-jsonrpc`,
`-testing`, plus `htmx-skill`) build on it and cross-reference it by skill name.

`skills/delphi` and `skills/delphi-code-smells` are the exception: they are about the **language and the
RTL**, not the framework, so the iron rule points at the shipped RTL/VCL source
(`C:\Program Files (x86)\Embarcadero\Studio\<n>.0\source\rtl\`, `…\vcl\`) and the Embarcadero docwiki instead
of `C:\DEV\dmvcframework`. They carry no wizard-first section — they apply to any `.pas` file. A version
claim ("available since Delphi X") is as damaging there as a wrong identifier: check it, never recall it.
The two split by job: `delphi` explains how the language works, `delphi-code-smells` finds what is wrong with
existing code. Ownership *semantics* live in the first, leak *diagnosis* in the second — they cross-reference
rather than repeat. A **warning code** (`W1035`) is verified the only honest way: write the offending code
and compile it with `dcc32.exe`, then copy what it printed.

Adding a skill? Also add it to: the four `install_in_*.bat` (three of them carry a hand-written one-line
description per skill), and the four places README.md lists the set — the skills table, the prompts section,
the `AGENTS.md` example, the layout tree.

**The core skill's `SKILL.md` is deliberately thin.** Bulk goes in `reference/` — it is loaded only when the
task needs it. When adding substantial material, ask whether it belongs in a reference file rather than in
`SKILL.md`, and add a row to the reference index table in `SKILL.md`.

## Hard constraints on a SKILL.md

- YAML frontmatter with `name` and `description`. **Total frontmatter must stay under 1024 characters** — over
  that, the skill silently fails to load. This has happened.
- `name` must exactly match the folder name; letters, numbers and hyphens only.
- `description` = *when to use it*, in third person. It is the only thing the agent reads when deciding
  whether to load the skill. Do not summarize the skill's workflow there: agents follow the description
  instead of reading the body.

## `check.py` — run it after every edit

```bash
python check.py        # exits non-zero on any defect
```

Four mechanical checks, about five seconds:

- **frontmatter** — under 1024 chars, `name` == folder, `description` present
- **links** — every `reference/*.md` and every sibling skill named actually exists
- **identifiers** — every Delphi identifier in the prose exists in a source tree
  (`C:\DEV\dmvcframework\{sources,samples,ideexpert,lib}` and the Delphi `source\{rtl,vcl,data,DunitX,internet}`).
  Override with `DMVC_HOME` / `DELPHI_SOURCE`; if neither tree is present the check is skipped, not failed.
- **coverage** — every skill is listed in the three installers that name skills, and in README.md

When it flags an identifier you know is an example (`TProductsController`, `TMyRecord`), either declare it in
the doc — `TFoo = class(...)` is recognised repo-wide — or add it to `ALLOW` in `check.py`, deliberately.
That prompt is the point: a new identifier is either sourced or it is admittedly fictional.

**What it does not prove.** It checks that a name exists, not that it is used correctly. `Result := ToFree(x)`
passes every check and double-frees. Real names with the wrong arity are caught only by a compiler; ownership
bugs only by running something. So, in order of cost:

1. `check.py` — on every edit.
2. Compile: paste the skill's code skeletons into a wizard project and build it (`scripts/build.bat`). Catches
   wrong signatures. With `ReportMemoryLeaksOnShutdown := True` plus the DUnitX suite, it also catches the
   double-free/leak class — the one this repo exists to prevent.
3. Agent RED/GREEN (below) — before tagging a release.

## Two positions the skills take, deliberately

Do not weaken these without being asked — they are decisions, not oversights.

1. **Wizard-first.** The skills never scaffold a project from scratch. They detect a project generated by the
   DMVCFramework IDE wizard (`EngineConfigU.pas`, `RoutesU.pas`, `bin/.env`, …) and add features inside it. If
   there is none, they stop and tell the user to create one.
2. **Indy Direct is the default host — but only for a *new* project.** An existing WebBroker project (ISAPI,
   Apache module) is legitimate: the skills detect the host, keep it, and never suggest migrating. Everything
   above the host is identical on every backend.

## How skills are tested

`check.py` covers the mechanical half (above). The half that matters — does the skill actually change what an
agent writes — is verified by **running an agent against it**:

- **Baseline (RED):** dispatch a subagent to do a task *without* the skill, forbidding it from reading the
  framework source. Record the exact wrong names it invents. That list is the specification.
- **With the skill (GREEN):** same task, agent restricted to the skill folder only (no source, no samples).
  Then ask it check questions whose answers are the bugs from the baseline — e.g. *"do you need `ToFree` on
  the object you return?"* (correct answer: no, it would double-free).
- **Audit:** dispatch an agent to fact-check every identifier in a skill against `sources/` and `samples/`,
  reporting only defects with `file:line`. Do this before publishing changes. `check.py` now does the
  name-exists part; the agent's job is the part a script cannot do — wrong arity, wrong ownership, an example
  that would not compile.

**Keep `check.py` honest.** A checker that never fails is decoration. After changing it, mutate a skill on
purpose and confirm it fails: rename a class to something plausible that does not exist, point a
`reference/` link at a missing file, pad a `description` past 1024. Restore from a **copy** — never
`git checkout` a file whose edits are not committed yet.

## Installers

The four `install_in_*.bat` are idempotent and must stay so: re-running overwrites the skills but must not
duplicate the section appended to `AGENTS.md` / `GEMINI.md` (guarded by the `<!-- delphi-ai-skills -->`
marker). Claude Code auto-discovers skills; Codex, Cursor and Gemini do not, which is why those scripts also
write the pointer file.

Test an installer against a scratch directory before shipping it — cmd.exe escaping is treacherous
(`!` inside a `<!-- -->` comment is eaten by delayed expansion and needs `^^!`).

## Versioning

Currently **0.2.0**, pre-1.0: the shape of the skill set is explicitly unsettled, and skills may be split,
merged or renamed between minor versions. The skills version is independent of the framework's; the README
states which DelphiMVCFramework release the content was verified against. Update both when content changes
materially.
