#!/usr/bin/env python3
"""Generate www/index.html from ../README.md's Gateway column.

Source of truth: the workspace README.md table (parent dir). The HTML layout
and CSS live in www/index.template.html — edit that file for styling changes.
Cards are grouped into sections via a path-prefix → category heuristic
(see CATEGORY_RULES below); add a rule when introducing a new top-level path.

Usage: python3 gen-index.py
Reads:  ../README.md, www/index.template.html
Writes: www/index.html
"""

import os
import re
import sys
from html import escape as h

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
README_PATH = os.path.join(SCRIPT_DIR, '..', 'README.md')
TEMPLATE_PATH = os.path.join(SCRIPT_DIR, 'www', 'index.template.html')
OUTPUT_PATH = os.path.join(SCRIPT_DIR, 'www', 'index.html')

# Order here defines section order on the page. First matching rule wins;
# the catch-all '' rule must stay last.
CATEGORY_RULES = [
    ('/auth-admin',  'Identity & Access'),
    ('/poly',        'Polymarket'),
    ('/health',      'Personal'),
    ('/task-hub',    'Personal'),
    ('/reader',      'Personal'),
    ('/tao',         'Research'),
    ('/maple',       'Tools'),
    ('/vpn',         'Tools'),
    ('/hermes',      'Tools'),
    ('/public',      'Sharing'),
    ('',             'Other'),
]


def categorise(path: str) -> str:
    for prefix, label in CATEGORY_RULES:
        if path.startswith(prefix):
            return label
    return 'Other'


def strip_markdown(text):
    """Remove markdown links [label](url) → label, and backticks."""
    text = re.sub(r'\[([^\]]+)\]\([^)]+\)', r'\1', text)
    text = re.sub(r'`([^`]+)`', r'\1', text)
    return text.strip()


def derive_label(tech):
    t = tech.lower()
    if 'streamlit' in t:
        return 'Streamlit'
    if 'next.js' in t:
        return 'Next.js'
    if 'vite' in t and 'fastapi' in t:
        return 'Vite + FastAPI'
    if 'fastapi' in t:
        return 'FastAPI'
    if 'caddy' in t:
        return 'Caddy'
    return re.split(r'[\s/+]+', tech)[0]


def parse_readme(path):
    """Return list of card dicts extracted from the README.md table."""
    with open(path, encoding='utf-8') as f:
        lines = f.readlines()

    headers = None
    col = {}
    cards = []

    for line in lines:
        line = line.rstrip('\n')
        if not line.startswith('|'):
            headers = None
            continue

        parts = [c.strip() for c in line.split('|')[1:-1]]

        if all(not p or re.fullmatch(r'[-: ]+', p) for p in parts):
            continue

        if headers is None:
            if 'Gateway' in parts:
                headers = parts
                col = {h: i for i, h in enumerate(headers)}
            continue

        if len(parts) <= col['Gateway']:
            continue

        gateway_raw = strip_markdown(parts[col['Gateway']])
        if not gateway_raw or gateway_raw == '-':
            continue

        name = strip_markdown(parts[col.get('專案名稱', 0)])
        desc = strip_markdown(parts[col.get('說明', 1)])
        tech = strip_markdown(parts[col.get('技術棧', 2)])
        label = derive_label(tech)

        # "path1:title1, path2:title2" — each entry may carry its own title.
        for entry in gateway_raw.split(','):
            entry = entry.strip()
            if ':' in entry:
                path, title = entry.split(':', 1)
            else:
                path, title = entry, name
            cards.append({
                'path': path.strip(),
                'title': title.strip(),
                'desc': desc,
                'label': label,
            })

    return cards


def render_card(c):
    return (
        f'      <a class="card" href="{h(c["path"])}">\n'
        f'        <div class="card-head">\n'
        f'          <div class="card-label">{h(c["label"])}</div>\n'
        f'          <div class="status-dot" data-state="unknown" data-path="{h(c["path"])}" title="unknown"></div>\n'
        f'        </div>\n'
        f'        <div class="card-title">{h(c["title"])}</div>\n'
        f'        <div class="card-desc">{h(c["desc"])}</div>\n'
        f'        <div class="card-path">{h(c["path"])}</div>\n'
        f'      </a>'
    )


def render_sections(cards):
    by_category = {}
    for c in cards:
        cat = categorise(c['path'])
        by_category.setdefault(cat, []).append(c)

    section_order = []
    for _, label in CATEGORY_RULES:
        if label in by_category and label not in section_order:
            section_order.append(label)

    blocks = []
    for cat in section_order:
        cards_html = '\n\n'.join(render_card(c) for c in by_category[cat])
        blocks.append(
            f'    <section>\n'
            f'      <h2>{h(cat)}</h2>\n'
            f'      <div class="grid">\n\n{cards_html}\n\n      </div>\n'
            f'    </section>'
        )
    return '\n\n'.join(blocks)


def main():
    cards = parse_readme(README_PATH)
    if not cards:
        print('Warning: no Gateway entries found in README.md', file=sys.stderr)
        sys.exit(1)
    with open(TEMPLATE_PATH, encoding='utf-8') as f:
        template = f.read()
    html_doc = template.replace('{{SECTIONS}}', render_sections(cards))
    with open(OUTPUT_PATH, 'w', encoding='utf-8') as f:
        f.write(html_doc)
    print(f'Generated {OUTPUT_PATH} ({len(cards)} cards across sections)')


if __name__ == '__main__':
    main()
