# Changelog

**0.4.0** — five skills added, fifteen in total.

- **`delphi-firedac`** — FireDAC in plain Delphi: the `uses` set for a non-visual program, connection definitions
  and pooling, transactions (a connection closed with an open transaction *commits*), parameters and macros
  (`&` and `!` prefixes), `RecordCount` and fetch options, array DML, cached updates (a second `ApplyUpdates`
  inserts the rows again), who frees what, errors and threading, and a map from BDE/ADO/dbExpress.
- **`delphi-testing`** — DUnitX: a project skeleton that compiles and runs, attributes, test data providers,
  assertion semantics, CI exit codes (an empty run exits 0), per-test leak detection, testable code and
  characterization tests.
- **`delphi-build`** — `msbuild` and `dcc32`/`dcc64` from the command line: `Config` and not `Configuration`,
  `Make` vs `Build`, warnings as errors by name, the compile-fix loop, and `scripts/build.bat`.
- **`delphi-security`** — secure coding outside web servers: what `System.Hash` does and does not have, random
  numbers, Base64, TLS and certificate handling in `THTTPClient`, FireDAC macros, paths, secrets, command
  injection, DLL loading, untrusted lengths, and what a log or crash report must not contain.
- **`exewatch-delphi`** — the ExeWatch Delphi SDK (version 0.25.0): initialization, logging, user and device
  information, offline buffering, stack traces, server-side use.
- **`delphi`** — a procedure and verified facts for moving old code forward (`reference/legacy-migration.md`),
  a table of which unit declares what (`reference/units.md`), and a block of critical rules in each file.
- **`delphi-code-smells`** — a staged review (discover, judge, refute, verify, report) with evidence labels
  (VERIFIED, INFERRED, ASSUMED), and a search pattern for every smell.
- **`htmx-skill`** — indexes the htmx **2.x** reference pages (release 2.0.11): 83 pages, up from 79, with a
  line for each page. Links go to `v2.htmx.org` instead of `htmx.org`, so they keep describing 2.x when
  `htmx.org` moves to a newer major version, and the skill points htmx 4 projects to
  `https://four.htmx.org/llms.txt`.
- Corrections: a comment in `delphi` claimed a closure over a `for var` loop prints `3 3 3`; it prints `4 4 4`
  on 12 and 13. `delphi-code-smells`: several `rg` one-liners did not run or missed cases, and `leaks.md`
  said both DUnitX leak adapters register only under a define (the FastMM5 one registers always and needs the
  external `FastMM5.pas`).
- The README is now a short front page; installing, example prompts, layout, versioning and this changelog
  moved to `docs/`.

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
