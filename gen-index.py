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
import sys
from html import escape as h

import readme_table
from readme_table import derive_label

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
README_PATH = os.path.join(SCRIPT_DIR, '..', 'README.md')
TEMPLATE_PATH = os.path.join(SCRIPT_DIR, 'www', 'index.template.html')
OUTPUT_PATH = os.path.join(SCRIPT_DIR, 'www', 'index.html')

# Order here defines section order on the page. First matching rule wins;
# the catch-all '' rule must stay last.
CATEGORY_RULES = [
    ('/auth-admin',  'Identity & Access'),
    ('/health',      'Personal'),
    ('/task-hub',    'Personal'),
    ('/reader',      'Personal'),
    ('/tao',         'Research'),
    ('/vpn',         'Tools'),
    ('/lib',         'Library'),
    ('',             'Other'),
]


def categorise(path: str) -> str:
    for prefix, label in CATEGORY_RULES:
        if path.startswith(prefix):
            return label
    return 'Other'


def parse_readme(path):
    """Return list of card dicts, one per Gateway entry in the README table."""
    return [
        {'path': gw_path, 'title': title, 'desc': row.desc, 'label': derive_label(row.tech)}
        for row in readme_table.parse_readme(path)
        for gw_path, title in row.entries
    ]


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
