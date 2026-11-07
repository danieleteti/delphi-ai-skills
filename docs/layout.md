# Layout

The core skill keeps its bulk out of the way: `SKILL.md` is the working core (bootstrap, controllers,
responses, ownership, middleware, pitfalls), and the heavy material sits in files the agent opens only when
the task calls for them.

```
check.py                          mechanical validation of every skill - see versioning.md
install_in_claude.bat             installers - see installing.md
install_in_codex.bat
install_in_cursor.bat
install_in_gemini.bat
tools/gen_htmx_index.py           regenerates skills/htmx-skill/SKILL.md (not shipped)
.github/workflows/htmx-skill.yml  weekly: refresh that file on main and dmvc-3.5
docs/                             prompts, installing, layout, versioning, changelog
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
