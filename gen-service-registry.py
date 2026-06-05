#!/usr/bin/env python3
"""Regenerate the Service Registry table inside CLAUDE.md.

The single source of truth for what exists in the gateway is split:
  - workspace ../README.md owns project metadata (name, tech, Gateway path)
  - Caddyfile owns routing (path → upstream port)

This script joins them on the Gateway path so CLAUDE.md doesn't drift from
either. CLAUDE.md must contain the markers below; everything between them is
replaced verbatim each run.

Markers:
    <!-- BEGIN:SERVICE_REGISTRY -->
    <!-- END:SERVICE_REGISTRY -->

Usage: python3 gen-service-registry.py
"""
import os
import re
import sys

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
README_PATH = os.path.join(SCRIPT_DIR, '..', 'README.md')
CADDYFILE_PATH = os.path.join(SCRIPT_DIR, 'Caddyfile')
CLAUDE_MD_PATH = os.path.join(SCRIPT_DIR, 'CLAUDE.md')

BEGIN = '<!-- BEGIN:SERVICE_REGISTRY -->'
END = '<!-- END:SERVICE_REGISTRY -->'


def strip_markdown(text):
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
    if 'authelia' in t:
        return 'Authelia'
    if 'python wsgi' in t or 'wsgi' in t:
        return 'WSGI'
    if 'python' in t:
        return 'Python'
    if 'caddy' in t:
        return 'Caddy'
    return re.split(r'[\s/+]+', tech)[0]


def parse_readme(path):
    """Return list of (gateway_path, project_name, type_label) from README."""
    rows = []
    with open(path, encoding='utf-8') as f:
        lines = f.readlines()
    headers, col = None, {}
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
                headers, col = parts, {h: i for i, h in enumerate(parts)}
            continue
        if len(parts) <= col['Gateway']:
            continue
        gateway = strip_markdown(parts[col['Gateway']])
        if not gateway or gateway == '-':
            continue
        project = strip_markdown(parts[col.get('專案名稱', 0)])
        tech = strip_markdown(parts[col.get('技術棧', 2)])
        label = derive_label(tech)
        for entry in gateway.split(','):
            entry = entry.strip()
            path = entry.split(':', 1)[0].strip()
            rows.append((path, project, label))
    return rows


_PORT_PATTERNS = [
    # reverse_proxy localhost:PORT  /  reverse_proxy 127.0.0.1:PORT
    re.compile(r'reverse_proxy\s+(?:localhost|127\.0\.0\.1):(\d+)'),
    # import proxy_auth PORT
    re.compile(r'import\s+proxy_auth\s+(\d+)\b'),
    # import proxy_auth_strip /prefix PORT
    re.compile(r'import\s+proxy_auth_strip\s+\S+\s+(\d+)\b'),
]


def parse_caddyfile_ports(path):
    """Return {handle_path: port} for each `handle` / `handle_path` block.

    Walks the file once, tracking the current handle block by brace depth so
    nested `route { ... }` / snippets resolve to their enclosing handle.
    """
    with open(path, encoding='utf-8') as f:
        src = f.read()

    ports = {}
    open_re = re.compile(r'^(\s*)handle(?:_path)?\s+(\S+?)\*?\s*\{', re.MULTILINE)
    matches = list(open_re.finditer(src))
    for i, m in enumerate(matches):
        start = m.end()
        # Scan forward, balancing braces, to find this handle's body.
        depth = 1
        j = start
        while j < len(src) and depth:
            c = src[j]
            if c == '{':
                depth += 1
            elif c == '}':
                depth -= 1
            j += 1
        body = src[start:j - 1] if depth == 0 else src[start:]
        handle_path = m.group(2).rstrip('/')
        if handle_path == '/':
            continue
        for pat in _PORT_PATTERNS:
            hit = pat.search(body)
            if hit:
                ports.setdefault(handle_path, hit.group(1))
                break
    return ports


def best_port(path, ports):
    path = path.rstrip('/')
    if path in ports:
        return ports[path]
    # Prefix match only at a / boundary so /auth-admin does not pick up /auth.
    candidates = [
        k for k in ports
        if path == k or path.startswith(k + '/')
    ]
    if candidates:
        return ports[max(candidates, key=len)]
    return None


def render_table(rows, ports):
    lines = [
        '| Path | Port | Project | Type |',
        '|------|------|---------|------|',
    ]
    for path, project, label in rows:
        port = best_port(path, ports) or '—'
        lines.append(f'| `{path}` | {port} | {project} | {label} |')
    return '\n'.join(lines)


def splice(claude_md, table):
    pattern = re.compile(re.escape(BEGIN) + r'.*?' + re.escape(END), re.DOTALL)
    block = f'{BEGIN}\n<!-- Auto-generated by gen-service-registry.py — do not edit. -->\n\n{table}\n\n{END}'
    if not pattern.search(claude_md):
        raise SystemExit(
            f'CLAUDE.md is missing the {BEGIN} / {END} markers — add them where '
            f'the Service Registry table should live.'
        )
    return pattern.sub(block, claude_md)


def main():
    rows = parse_readme(README_PATH)
    ports = parse_caddyfile_ports(CADDYFILE_PATH)
    table = render_table(rows, ports)
    with open(CLAUDE_MD_PATH, encoding='utf-8') as f:
        original = f.read()
    updated = splice(original, table)
    if updated == original:
        print('Service Registry already up to date.')
        return 0
    with open(CLAUDE_MD_PATH, 'w', encoding='utf-8') as f:
        f.write(updated)
    print(f'Updated {CLAUDE_MD_PATH} ({len(rows)} services)')
    return 0


if __name__ == '__main__':
    sys.exit(main())
