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
import os
import shutil
import subprocess
import sys
import threading
import time
from datetime import datetime, timezone
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

PORT = 8030
HOST = '127.0.0.1'
CACHE_TTL_SECONDS = 30
README_PATH = Path(__file__).resolve().parent.parent.parent / 'README.md'

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
import readme_table  # noqa: E402


def load_service_map() -> dict[str, list[tuple[str, str]]]:
    """Return {gateway_path: [(unit, 'system' | 'user'), ...]} from workspace README."""
    result: dict[str, list[tuple[str, str]]] = {}
    for row in readme_table.parse_readme(README_PATH):
        for path, _ in row.entries:
            if path:
                result[path] = row.units
    return result


def _is_active(unit: str, scope: str = 'system') -> str:
    """Return 'up' / 'down' / 'unknown' for a single systemd unit.

    User units ("（user）" in the README) live on ubuntu's user manager; this
    service runs as ubuntu under the system manager, so point systemctl at the
    user runtime dir explicitly.
    """
    if not shutil.which('systemctl'):
        return 'unknown'
    argv = ['systemctl', 'is-active', unit]
    env = None
    if scope == 'user':
        argv = ['systemctl', '--user', 'is-active', unit]
        env = {**os.environ, 'XDG_RUNTIME_DIR': os.environ.get('XDG_RUNTIME_DIR') or f'/run/user/{os.getuid()}'}
    try:
        proc = subprocess.run(argv, capture_output=True, text=True, timeout=2, env=env)
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
        states = [_is_active(u, scope) for u, scope in units]
        if 'up' in states:
            state = 'up'
        elif 'down' in states:
            state = 'down'
        else:
            state = 'unknown'
        services[path] = {'state': state, 'checked_at': now, 'units': [u for u, _ in units]}
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
