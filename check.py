#!/usr/bin/env python
"""Mechanical checks on the skills. Run from the repo root:  python check.py

Exits non-zero if anything is wrong. What it proves and what it does not:

  - frontmatter        loads at all (under 1024 chars, name == folder)
  - links              every reference/ file and sibling skill named actually exists
  - identifiers        every Delphi identifier in the prose exists in the sources
  - coverage           every skill is listed in the installers and the README

An identifier that exists is not an identifier used correctly: this catches
`TCORSMiddleware` (invented), not `Result := ToFree(x)` (real names, double free).
For that you need the compile/leak harness or an agent RED/GREEN run - see CLAUDE.md.
"""

import io
import os
import re
import sys
import glob

REPO = os.path.dirname(os.path.abspath(__file__))
SKILLS = os.path.join(REPO, 'skills')

# Source trees searched for identifiers. Missing tree => that check is skipped, not failed,
# so this still runs on a machine without Delphi installed.
DMVC = os.environ.get('DMVC_HOME', r'C:\DEV\dmvcframework')
STUDIO = os.environ.get('DELPHI_SOURCE') or next(
    iter(sorted(glob.glob(r'C:\Program Files (x86)\Embarcadero\Studio\*\source'), reverse=True)), '')

SOURCE_DIRS = [os.path.join(DMVC, d) for d in ('sources', 'samples', 'ideexpert', 'lib')] + \
              [os.path.join(STUDIO, d) for d in ('rtl', 'vcl', 'data', 'DunitX', 'internet') if STUDIO]

# Skills whose prose is not Delphi at all.
NO_DELPHI = {'htmx-skill'}

# Identifiers that are deliberately not in any source tree: placeholders in prose and
# fictional example types the docs use without declaring.
ALLOW = {
    # families written with a * in prose
    'MVCAudit', 'EMVCJSONRPC',
    # placeholders: "your partitioned entity", "some class of yours"
    'TPartitionedClass', 'TMyClass', 'TMyHandler', 'TMyRecord', 'TThing', 'TBar',
    'TRec', 'TBaseClass', 'TEditor', 'TFormMain', 'ENew', 'EFileNotFound',
    # example domain types used without being declared in the same doc
    'TRepository', 'ILogger', 'IOrderService', 'IInvoiceStore', 'TOrderService',
    'TInvoice', 'EOrderNotFound', 'EInvoiceError', 'EImportFailed',
    'ICustomerService', 'TCustomerService', 'IProductService', 'TProductService',
    'TProductIn', 'TProductsController', 'TUsersController', 'TOrderLine',
    'TMyTests', 'TOrdersTests', 'TSecureTests',
}

# Fenced blocks in these languages are not Delphi and are not scanned.
NOT_DELPHI_FENCE = re.compile(
    r'```(?:html|css|javascript|js|json|jsonc|bash|sh|bat|cmd|powershell|sql|yaml|yml|text|txt|markdown|md|ini|http)\b.*?```',
    re.S | re.I)

CANDIDATE = re.compile(
    r'\b[TIE][A-Z][A-Za-z0-9_]{2,}\b'          # TFoo, IFoo, EFoo
    r'|\bMVC[A-Za-z0-9_]+\b'                   # MVCPath, MVCFromBody, MVCFramework.X
    r'|\b(?:fo|ea|nc|lo|bv|ht|et|rk|mv|mk|pp|st|sw)[A-Z][A-Za-z0-9]+\b')  # enum members

# A type the document declares itself is an example, not a claim about the framework.
DECLARED = re.compile(
    r'\b([TIE][A-Za-z0-9_]+)\s*(?:<[^>\n]*>)?\s*=\s*(?:packed\s+)?'
    r'(?:class|record|interface|object|reference\s+to|set\s+of|array|\()', re.I)

problems = []


def fail(where, msg):
    problems.append('%s: %s' % (where, msg))


def skill_dirs():
    return sorted(d for d in os.listdir(SKILLS) if os.path.isdir(os.path.join(SKILLS, d)))


def read(path):
    return io.open(path, encoding='utf-8').read()


def check_frontmatter(name):
    path = os.path.join(SKILLS, name, 'SKILL.md')
    if not os.path.exists(path):
        return fail(name, 'no SKILL.md')
    text = read(path)
    if not text.startswith('---\n'):
        return fail(name, 'does not start with YAML frontmatter')
    end = text.find('\n---\n', 3)
    if end < 0:
        return fail(name, 'unterminated frontmatter')
    fm = text[:end + 5]
    if len(fm) >= 1024:
        fail(name, 'frontmatter is %d chars - over 1024 it silently fails to load' % len(fm))
    m = re.search(r'^name:\s*(\S+)', fm, re.M)
    if not m:
        fail(name, 'no name: in frontmatter')
    elif m.group(1) != name:
        fail(name, 'name is %r but the folder is %r' % (m.group(1), name))
    if not re.search(r'^description:\s*\S', fm, re.M):
        fail(name, 'no description: in frontmatter')
    if not re.match(r'^[a-z0-9-]+$', name):
        fail(name, 'folder name must be lowercase letters, digits and hyphens')


def check_links(name, names):
    folder = os.path.join(SKILLS, name)
    for path in glob.glob(os.path.join(folder, '**', '*.md'), recursive=True):
        text = read(path)
        rel = os.path.relpath(path, REPO)
        for ref in set(re.findall(r'`(reference/[A-Za-z0-9_.-]+\.md)`', text)):
            # a skill may point at another skill's reference file ("see dmvcframework, reference/servers.md")
            if not any(os.path.exists(os.path.join(SKILLS, s, ref)) for s in names):
                fail(rel, 'points at %s which exists in no skill' % ref)
        for other in set(re.findall(r'`skills/([A-Za-z0-9_-]+)/SKILL\.md`', text)):
            if other not in names:
                fail(rel, 'points at skill %r which does not exist' % other)
        for other in set(re.findall(r'`(dmvcframework(?:-[a-z]+)?|delphi|htmx-skill)`', text)):
            if other not in names:
                fail(rel, 'names skill %r which does not exist' % other)


def load_source_tokens():
    tokens = set()
    found = False
    for root in SOURCE_DIRS:
        if not os.path.isdir(root):
            continue
        found = True
        for dirpath, _, filenames in os.walk(root):
            for fn in filenames:
                if fn.lower().endswith(('.pas', '.inc')):
                    try:
                        text = io.open(os.path.join(dirpath, fn), encoding='utf-8', errors='ignore').read()
                    except OSError:
                        continue
                    tokens.update(t.lower() for t in re.findall(r'[A-Za-z_][A-Za-z0-9_]*', text))
    return tokens if found else None


def declared_in_docs():
    """Types the docs declare themselves are examples, not claims about a library.
    Collected repo-wide: one skill declares TMyResource, another uses it."""
    declared = set()
    for path in glob.glob(os.path.join(SKILLS, '**', '*.md'), recursive=True):
        declared.update(DECLARED.findall(read(path)))
    return declared


def known(ident, tokens):
    lower = ident.lower()
    # Attributes are written [MVCPath] but declared MVCPathAttribute.
    return lower in tokens or lower + 'attribute' in tokens


def check_identifiers(name, tokens, declared):
    if name in NO_DELPHI:
        return
    for path in glob.glob(os.path.join(SKILLS, name, '**', '*.md'), recursive=True):
        text = NOT_DELPHI_FENCE.sub('', read(path))
        unknown = sorted({i for i in CANDIDATE.findall(text)
                          if i not in declared and i not in ALLOW
                          and i != i.upper()             # skip acronyms: IDOR, TEST_PORT
                          and not known(i, tokens)})
        for ident in unknown:
            fail(os.path.relpath(path, REPO), '%s is in no source tree - invented?' % ident)


def check_coverage(names):
    targets = {
        'install_in_codex.bat': 'skills/%s/SKILL.md',
        'install_in_gemini.bat': 'skills/%s/SKILL.md',
        'install_in_cursor.bat': ':rule %s ',
        'README.md': '%s',
    }
    for fn, pattern in targets.items():
        text = read(os.path.join(REPO, fn))
        for name in names:
            if pattern % name not in text:
                fail(fn, 'does not list the %r skill' % name)


def main():
    names = skill_dirs()
    if not names:
        fail('skills/', 'no skills found - run this from the repo root')
    for name in names:
        check_frontmatter(name)
        check_links(name, names)
    check_coverage(names)

    tokens = load_source_tokens()
    if tokens is None:
        print('SKIP identifier check: no source tree found.')
        print('     Set DMVC_HOME (DelphiMVCFramework checkout) and/or install Delphi.')
    else:
        declared = declared_in_docs()
        for name in names:
            check_identifiers(name, tokens, declared)

    print('%d skills checked.' % len(names))
    if problems:
        print('\n%d problem(s):\n' % len(problems))
        for p in problems:
            print('  ' + p)
        return 1
    print('OK.')
    return 0


if __name__ == '__main__':
    sys.exit(main())
