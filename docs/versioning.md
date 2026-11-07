# Versioning details and checking the skills

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

## Checking the skills themselves

```bash
python check.py
```

Verifies, in about five seconds and with no dependencies: every frontmatter still loads (under 1024
characters, `name` matching the folder), every `reference/` file and sibling skill named actually exists,
**every Delphi identifier in the prose exists in the sources**, and every skill is listed in the installers
and in the README. It exits non-zero on any defect, so it fits a pre-commit hook or CI.
`python check.py --urls` adds the one check that needs the network: every link in `htmx-skill` must answer 200.

It reads `C:\DEV\dmvcframework` and your Delphi `source\` tree — override with `DMVC_HOME` and
`DELPHI_SOURCE`. Without either it still runs, and skips the identifier check rather than failing.

It proves a name *exists*, not that it is used correctly: a real API called with the wrong arguments needs a
compiler, and an ownership bug needs to be run. See CLAUDE.md for the two levels above this one.
