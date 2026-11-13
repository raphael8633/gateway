"""The one parser for the workspace ../README.md project table.

gen-index.py (nav page), gen-service-registry.py (CLAUDE.md registry) and
scripts/services-status.py (status dots) all read the same rows through here.
Only tables with a `Gateway` column are read; rows whose Gateway cell is empty
or `-` are skipped (the archived-projects table has no Gateway column).

Gateway cell:         "/path:Title, /other:Other title" (title defaults to the project name)
Systemd Service cell: "`a.service`, `b.timer`（user）, `c.timer`（user，note）"; a
                      parenthetical containing "user" marks a user-manager unit.
"""
import os
import re
from dataclasses import dataclass, field

README_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'README.md')

_PAREN = re.compile(r'[（(]([^）)]*)[）)]')


@dataclass
class Row:
    name: str
    desc: str
    tech: str
    entries: list = field(default_factory=list)  # [(path, title)]
    units: list = field(default_factory=list)    # [(unit, 'system' | 'user')]


def strip_markdown(text):
    """[label](url) → label; drop backticks."""
    text = re.sub(r'\[([^\]]+)\]\([^)]+\)', r'\1', text)
    text = re.sub(r'`([^`]+)`', r'\1', text)
    return text.strip()


def derive_label(tech):
    t = tech.lower()
    for needle, label in (('streamlit', 'Streamlit'), ('next.js', 'Next.js'), ('fastapi', 'FastAPI'),
                          ('authelia', 'Authelia'), ('wsgi', 'WSGI'), ('python', 'Python'),
                          ('caddy', 'Caddy')):
        if needle in t:
            if needle == 'fastapi' and 'vite' in t:
                return 'Vite + FastAPI'
            return label
    return re.split(r'[\s/+]+', tech)[0]


def parse_units(raw):
    raw = raw.strip()
    if raw in ('', '-', '—'):
        return []
    units = []
    # Split on commas outside parentheses so "（user，note）" stays with its unit.
    for part in re.split(r'[,，](?![^（(]*[）)])', raw):
        notes = ' '.join(_PAREN.findall(part))
        unit = _PAREN.sub('', part).replace('`', '').strip()
        if not unit or unit in ('-', '—'):
            continue
        if not unit.endswith(('.service', '.timer', '.socket', '.path')):
            unit += '.service'
        units.append((unit, 'user' if re.search(r'\buser\b', notes) else 'system'))
    return units


def parse_gateway(raw, name):
    entries = []
    for entry in raw.split(','):
        entry = entry.strip()
        if not entry:
            continue
        path, _, title = entry.partition(':')
        entries.append((path.strip(), title.strip() or name))
    return entries


def parse_readme(path=README_PATH):
    with open(path, encoding='utf-8') as f:
        lines = f.read().splitlines()
    rows, col = [], None
    for line in lines:
        if not line.startswith('|'):
            col = None
            continue
        parts = [c.strip() for c in line.split('|')[1:-1]]
        if all(not p or re.fullmatch(r'[-: ]+', p) for p in parts):
            continue
        if col is None:
            if 'Gateway' in parts:
                col = {h: i for i, h in enumerate(parts)}
            continue
        if len(parts) <= col['Gateway']:
            continue
        gateway = strip_markdown(parts[col['Gateway']])
        if not gateway or gateway == '-':
            continue
        cell = lambda key, default: parts[col.get(key, default)] if col.get(key, default) < len(parts) else ''  # noqa: E731
        name = strip_markdown(cell('專案名稱', 0))
        rows.append(Row(
            name=name,
            desc=strip_markdown(cell('說明', 1)),
            tech=strip_markdown(cell('技術棧', 2)),
            entries=parse_gateway(gateway, name),
            units=parse_units(parts[col['Systemd Service']]) if 'Systemd Service' in col
            and col['Systemd Service'] < len(parts) else [],
        ))
    return rows
