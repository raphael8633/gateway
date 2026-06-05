#!/usr/bin/env python3
"""Tiny status endpoint for the nav page (raphtools.com/).

Serves JSON on http://127.0.0.1:8030/services-status.json behind Caddy. Every
{CACHE_TTL_SECONDS}s it runs `systemctl is-active <unit>` for each service
listed in workspace ../README.md's "Systemd Service" column, joined to its
Gateway path.

Run standalone: python3 services-status.py
Production:     deploy/gateway-services-status.service (systemd unit)
"""
import json
import re
import shutil
import subprocess
import threading
import time
from datetime import datetime, timezone
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

PORT = 8030
HOST = '127.0.0.1'
CACHE_TTL_SECONDS = 30
README_PATH = Path(__file__).resolve().parent.parent.parent / 'README.md'


def _strip_md(text: str) -> str:
    text = re.sub(r'\[([^\]]+)\]\([^)]+\)', r'\1', text)
    text = re.sub(r'`([^`]+)`', r'\1', text)
    return text.strip()


def _parse_unit_field(raw: str) -> list[str]:
    """Pull bare unit names out of the 'Systemd Service' column.

    The column uses backticked, comma-separated entries like
    ``\\`foo.service\\`, \\`foo.timer\\```; some rows use ``—`` / ``-`` /
    empty to mean "no systemd unit".
    """
    raw = raw.strip()
    if raw in ('', '-', '—'):
        return []
    cleaned = re.sub(r'`', '', raw)
    units = []
    for part in cleaned.split(','):
        unit = part.strip()
        if not unit or unit in ('-', '—'):
            continue
        units.append(unit if unit.endswith(('.service', '.timer', '.socket')) else unit + '.service')
    return units


def load_service_map() -> dict[str, list[str]]:
    """Return {gateway_path: [systemd_unit, ...]} from workspace README."""
    lines = README_PATH.read_text(encoding='utf-8').splitlines()
    headers, col = None, {}
    result: dict[str, list[str]] = {}
    for line in lines:
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
        if 'Gateway' not in col or 'Systemd Service' not in col:
            continue
        if len(parts) <= max(col['Gateway'], col['Systemd Service']):
            continue
        gateway = _strip_md(parts[col['Gateway']])
        if not gateway or gateway == '-':
            continue
        units = _parse_unit_field(parts[col['Systemd Service']])
        for entry in gateway.split(','):
            path = entry.strip().split(':', 1)[0].strip()
            if path:
                result[path] = units
    return result


def _is_active(unit: str) -> str:
    """Return 'up' / 'down' / 'unknown' for a single systemd unit."""
    if not shutil.which('systemctl'):
        return 'unknown'
    try:
        proc = subprocess.run(
            ['systemctl', 'is-active', unit],
            capture_output=True, text=True, timeout=2,
        )
    except subprocess.TimeoutExpired:
        return 'unknown'
    out = proc.stdout.strip()
    if out == 'active':
        return 'up'
    if out in ('inactive', 'failed', 'deactivating', 'activating'):
        return 'down'
    return 'unknown'


def collect_states() -> dict:
    """Run is-active for every known service and return the JSON payload."""
    services_map = load_service_map()
    now = datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M UTC')
    services = {}
    for path, units in services_map.items():
        if not units:
            services[path] = {'state': 'unknown', 'checked_at': now, 'units': []}
            continue
        # If any required unit is up we count the service as up; the worst
        # individual state wins otherwise (down beats unknown).
        states = [_is_active(u) for u in units]
        if 'up' in states:
            state = 'up'
        elif 'down' in states:
            state = 'down'
        else:
            state = 'unknown'
        services[path] = {'state': state, 'checked_at': now, 'units': units}
    return {'services': services, 'checked_at': now}


_cache_lock = threading.Lock()
_cache = {'payload': None, 'ts': 0.0}


def get_cached_payload() -> dict:
    with _cache_lock:
        if _cache['payload'] and time.time() - _cache['ts'] < CACHE_TTL_SECONDS:
            return _cache['payload']
    fresh = collect_states()
    with _cache_lock:
        _cache['payload'] = fresh
        _cache['ts'] = time.time()
    return fresh


class Handler(BaseHTTPRequestHandler):
    def do_GET(self):  # noqa: N802 (stdlib API)
        if self.path != '/services-status.json':
            self.send_error(404)
            return
        body = json.dumps(get_cached_payload()).encode('utf-8')
        self.send_response(200)
        self.send_header('Content-Type', 'application/json; charset=utf-8')
        self.send_header('Content-Length', str(len(body)))
        self.send_header('Cache-Control', 'max-age=30')
        self.end_headers()
        self.wfile.write(body)

    def log_message(self, *args, **kwargs):
        return  # silence stderr access log


def main():
    server = ThreadingHTTPServer((HOST, PORT), Handler)
    print(f'services-status listening on http://{HOST}:{PORT}')
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        server.server_close()


if __name__ == '__main__':
    main()
