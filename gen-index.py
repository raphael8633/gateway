#!/usr/bin/env python3
"""Generate www/index.html from ../README.md Gateway column.

Usage: python3 gen-index.py
Reads:  ../README.md  (Gateway column)
Writes: www/index.html
"""

import os
import re
import sys

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
README_PATH = os.path.join(SCRIPT_DIR, '..', 'README.md')
OUTPUT_PATH = os.path.join(SCRIPT_DIR, 'www', 'index.html')


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

        # Separator row (---|---|...)
        if all(not p or re.fullmatch(r'[-: ]+', p) for p in parts):
            continue

        # Header row — detect by presence of 'Gateway'
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

        # Parse gateway entries: "/path:Title, /path2:Title2"
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


def render_html(cards):
    cards_html = '\n\n'.join(
        f'    <a class="card" href="{c["path"]}">\n'
        f'      <div class="card-label">{c["label"]}</div>\n'
        f'      <div class="card-title">{c["title"]}</div>\n'
        f'      <div class="card-desc">{c["desc"]}</div>\n'
        f'      <div class="card-path">{c["path"]}</div>\n'
        f'    </a>'
        for c in cards
    )

    return f'''<!DOCTYPE html>
<html lang="zh-TW">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>raphtools.com</title>
  <style>
    *, *::before, *::after {{ box-sizing: border-box; margin: 0; padding: 0; }}

    body {{
      font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif;
      background: #0f0f0f;
      color: #e0e0e0;
      min-height: 100vh;
      display: flex;
      flex-direction: column;
      align-items: center;
      padding: 48px 24px;
    }}

    header {{
      text-align: center;
      margin-bottom: 48px;
    }}

    header h1 {{
      font-size: 1.8rem;
      font-weight: 600;
      letter-spacing: -0.02em;
      color: #fff;
    }}

    header p {{
      margin-top: 8px;
      font-size: 0.9rem;
      color: #666;
    }}

    .grid {{
      display: grid;
      grid-template-columns: repeat(auto-fill, minmax(280px, 1fr));
      gap: 16px;
      width: 100%;
      max-width: 900px;
    }}

    .card {{
      display: block;
      padding: 24px;
      background: #1a1a1a;
      border: 1px solid #2a2a2a;
      border-radius: 10px;
      text-decoration: none;
      color: inherit;
      transition: border-color 0.15s, background 0.15s;
    }}

    .card:hover {{
      border-color: #444;
      background: #222;
    }}

    .card-label {{
      font-size: 0.7rem;
      font-weight: 600;
      text-transform: uppercase;
      letter-spacing: 0.08em;
      color: #555;
      margin-bottom: 8px;
    }}

    .card-title {{
      font-size: 1rem;
      font-weight: 600;
      color: #fff;
      margin-bottom: 6px;
    }}

    .card-desc {{
      font-size: 0.85rem;
      color: #888;
      line-height: 1.5;
    }}

    .card-path {{
      margin-top: 14px;
      font-size: 0.75rem;
      color: #444;
      font-family: "SF Mono", "Fira Code", monospace;
    }}

    footer {{
      margin-top: 64px;
      font-size: 0.8rem;
      color: #333;
    }}
  </style>
</head>
<body>
  <header>
    <h1>raphtools.com</h1>
    <p>工具導覽</p>
  </header>

  <div class="grid">

{cards_html}

  </div>

  <footer>raphtools.com</footer>
</body>
</html>
'''


def main():
    cards = parse_readme(README_PATH)
    if not cards:
        print('Warning: no Gateway entries found in README.md', file=sys.stderr)
        sys.exit(1)
    html = render_html(cards)
    with open(OUTPUT_PATH, 'w', encoding='utf-8') as f:
        f.write(html)
    print(f'Generated {OUTPUT_PATH} ({len(cards)} cards)')


if __name__ == '__main__':
    main()
