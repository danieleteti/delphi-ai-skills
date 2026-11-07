#!/usr/bin/env python
"""Regenerate skills/htmx-skill/SKILL.md from a checkout of the htmx repo at a release tag.

    git clone --depth 1 --branch v2.0.11 https://github.com/bigskysoftware/htmx.git <dir>
    python -I tools/gen_htmx_index.py <dir>      # [--out FILE]
    python -I tools/gen_htmx_index.py --latest   # newest v2.x.y tag; no-op if already current
    python check.py --urls

The scheduled workflow (.github/workflows/htmx-skill.yml) runs --latest on main and dmvc-3.5.

Descriptions are htmx's own page frontmatter (htmx is 0BSD). Where htmx gives none, MANUAL holds a
line written for this skill; for the worked examples the line is generic. Any other page without a
description, or any stale MANUAL entry, stops the run: a partial index is worse than none.
"""

import html
import io
import os
import re
import subprocess
import sys
import tempfile
import tomllib

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUT = os.path.join(REPO, 'skills', 'htmx-skill', 'SKILL.md')  # --out FILE overrides (the workflow, per branch)
REMOTE = 'https://github.com/bigskysoftware/htmx.git'
SITE = 'https://v2.htmx.org'

# Pages htmx 2.0.11 gives no description for. Written from the pages themselves.
MANUAL = {
    'events': 'Every `htmx:*` event, one section each: when it fires and the fields of its `detail`, '
              'including `htmx:abort`, which htmx listens for instead of firing.',
    'reference': 'One-page reference: core and additional attributes, CSS classes, request and response '
                 'headers, events, the JavaScript API and the configuration options (`#config`).',
    'docs': 'The main guide: installing, AJAX requests, attribute inheritance, boosting, WebSockets and SSE, '
            'history, requests and responses, validation, animations, extensions, events and logging, debugging.',
    'migration-guide-htmx-1': 'Upgrading from htmx 1.x to 2.x: what changed (module-type dist files, extensions '
                              'moved out of the core distribution) and the steps to upgrade.',
    'server-examples': 'Links to server-side integration examples on GitHub, grouped by language and framework.',
    'extensions/building': 'How to write an extension: `htmx.defineExtension()` and the hooks an extension '
                           'receives, such as `onEvent`.',
    'extensions/head-support': 'Adds support for `head` tags in responses to htmx requests: installing, usage '
                               'and its events.',
    'extensions/htmx-1-compat': 'Lets a project move from htmx 1.x to 2 with few changes; the page says what it '
                                'covers and what it does not.',
    'extensions/idiomorph': 'Use the Idiomorph DOM-morphing algorithm as an `hx-swap` strategy, reusing existing '
                            'DOM nodes for smoother transitions.',
    'extensions/preload': 'Loads HTML fragments into the browser cache before the user asks for them, so pages '
                          'appear to load faster; warns against preloading too much.',
    'extensions/response-targets': 'Choose the swap target by HTTP status with `hx-target-[CODE]` (a trailing '
                                   'wildcard is allowed) and `hx-target-error` for 4xx and 5xx.',
    'extensions/sse': 'Server Sent Events: connects to an EventSource from HTML and swaps server events into the '
                      'page. One-directional; use the WebSocket extension to send messages.',
    'extensions/ws': 'WebSockets: bi-directional communication with a WebSocket server from HTML (`ws-connect`); '
                     'replaces the old `hx-ws` attribute.',
}
EXAMPLE_LINE = 'Worked example.'

# In the v2.0.11 sources but not part of htmx 2: v2.htmx.org answers 404 and src/htmx.js only
# mentions it in a comment. The generator stops if a SKIP entry no longer exists.
SKIP = {'attributes/hx-partial'}


def page(root, key):
    path = os.path.join(root, 'www', 'content', *key.split('/')) + '.md'
    if not os.path.exists(path):
        path = os.path.join(root, 'www', 'content', *key.split('/'), '_index.md')
    text = io.open(path, encoding='utf-8').read().replace('\r\n', '\n')
    m = re.match(r'\+\+\+\n(.*?)\n\+\+\+\n', text, re.S)
    if not m:
        sys.exit('%s: no +++ frontmatter' % key)
    fm = tomllib.loads(m.group(1))
    if 'title' not in fm:
        sys.exit('%s: no title' % key)
    return fm


def keys_in(root, folder, nested=False):
    base = os.path.join(root, 'www', 'content', folder)
    keys = [folder + '/' + f[:-3] for f in os.listdir(base) if f.endswith('.md') and f != '_index.md']
    if nested:
        keys += [folder + '/' + d for d in os.listdir(base)
                 if os.path.exists(os.path.join(base, d, '_index.md'))]
    return keys


def latest_tag():
    out = subprocess.run(['git', 'ls-remote', '--tags', '--refs', REMOTE, 'refs/tags/v2.*'],
                         capture_output=True, text=True, check=True).stdout
    tags = [t for t in (l.split('refs/tags/')[1] for l in out.splitlines()) if re.match(r'^v2\.\d+\.\d+$', t)]
    if not tags:
        sys.exit('no v2.x.y tag found on %s' % REMOTE)
    return max(tags, key=lambda t: tuple(int(n) for n in t[1:].split('.')))


def main():
    global OUT
    args = sys.argv[1:]
    if '--out' in args:
        i = args.index('--out')
        OUT = os.path.abspath(args[i + 1])
        del args[i:i + 2]
    if args == ['--latest']:
        # unattended mode (the scheduled workflow): do nothing unless htmx published a newer v2.x.y
        current = re.search(r'htmx 2\.x\*\*, release `(v2\.\d+\.\d+)`', io.open(OUT, encoding='utf-8').read())
        newest = latest_tag()
        if current and current.group(1) == newest:
            return print('up to date at %s' % newest)
        print('%s -> %s' % (current and current.group(1), newest))
        clone = tempfile.mkdtemp(prefix='htmx_')
        subprocess.run(['git', '-c', 'advice.detachedHead=false', 'clone', '-q', '--depth', '1',
                        '--branch', newest, REMOTE, clone], check=True)
        return generate(clone)
    if len(args) != 1:
        sys.exit(__doc__)
    generate(args[0])


def generate(root):
    tag = subprocess.run(['git', '-C', root, 'describe', '--tags', '--exact-match'],
                         capture_output=True, text=True).stdout.strip()
    if not re.match(r'^v2\.\d+\.\d+$', tag):
        sys.exit('checkout must be exactly at a v2.x.y release tag, got %r' % tag)

    sections = [
        ('General', ['api', 'events', 'reference', 'docs', 'migration-guide-htmx-1', 'server-examples'], False),
        ('Attributes', keys_in(root, 'attributes'), False),
        ('Examples', keys_in(root, 'examples', nested=True), True),
        ('Extensions', keys_in(root, 'extensions'), False),
        ('Headers', keys_in(root, 'headers'), False),
    ]
    used, skipped, body = set(), set(), []
    for name, keys, is_example in sections:
        rows = []
        for key in keys:
            if key in SKIP:
                skipped.add(key)
                continue
            fm = page(root, key)
            if 'description' in fm:
                desc = fm['description']
            elif key in MANUAL:
                desc = MANUAL[key]
                used.add(key)
            elif is_example:
                desc = EXAMPLE_LINE
            else:
                sys.exit('%s has no description in htmx and none in MANUAL' % key)
            title = html.unescape(fm['title']).replace('→', '->').strip()
            rows.append((title, ' '.join(desc.split()), '%s/%s/' % (SITE, key)))
        if name != 'General':
            rows.sort(key=lambda r: r[0].lower())
        body.append('### %s\n' % name)
        body += ['- **%s**: %s\n  - Reference: %s\n' % r for r in rows]
    stale = (set(MANUAL) - used) | (SKIP - skipped)
    if stale:
        sys.exit('MANUAL/SKIP entries not used (page gone, now described, or a typo): %s' % sorted(stale))

    ver = tag[1:]
    text = TEMPLATE.format(ver=ver, tag=tag, site=SITE, index='\n'.join(body))
    io.open(OUT, 'w', encoding='utf-8', newline='\n').write(text)
    print('wrote %s (htmx %s, %d pages)' % (os.path.relpath(OUT, REPO), ver, text.count('Reference: ')))


TEMPLATE = '''---
name: htmx-skill
description: Use when you need accurate htmx 2.x syntax or behavior: attributes, events, headers, the JS API, extensions, or a worked example. Indexes the htmx {ver} reference pages with a description each, so the right page can be fetched and read instead of recalled from memory. Not for htmx 4 (see the body).
---

# htmx Reference (htmx {ver})

Use the index below to open the most specific page for the user's question: read the linked
page (WebFetch) instead of answering from memory. Attribute inheritance, swap modifiers and event
names are easy to misremember.

This index covers **htmx 2.x**, release `{tag}`; links go to `{site}`.
htmx 4 is a different major version with its own documentation: for a 4.x project use
https://four.htmx.org/llms.txt and do not mix its answers with this index.

If nothing in the index matches, start from {site}/reference/.

## Reference Index

{index}
## Usage Notes

- Prefer the attribute, header or event page over a general guide.
- Every event is on {site}/events/, one section each. Configuration options are in the
  Configuration Reference section of {site}/reference/#config.
- "Worked example." means the page is a live demo with markup and server responses: fetch it.
- Moving a project from htmx 1.x: read {site}/migration-guide-htmx-1/ first.
'''

if __name__ == '__main__':
    main()
