#!/usr/bin/env python3
"""Weekly human/machine request counts from the Caddy access log.

Reads ~/data/caddy/access.log plus Caddy's rolled files (access-*.log[.gz]),
classifies each request, prints one 🟢 line for the morning brief and appends
the week's numbers to ~/data/caddy/weekly.jsonl so later decisions do not
depend on raw-log retention.

Kinds:
  human   browser page view from outside this host: document load, or a Next.js
          client navigation (Rsc header, not a prefetch); 2xx/304 only
  asset   other browser traffic (scripts, API calls, prefetches, login redirects)
  local   this host (agents, curl) and the vps-sweep self-check probe
  machine everything else from outside (bots, scripts, scanners, 4xx/5xx)

Usage: python3 scripts/access_stats.py [--days 7] [--no-history]
"""
import argparse
import datetime as dt
import gzip
import ipaddress
import json
import pathlib
import re
import socket
import subprocess
import sys

LOG_DIR = pathlib.Path('/home/ubuntu/data/caddy')
HISTORY = LOG_DIR / 'weekly.jsonl'
TPE = dt.timezone(dt.timedelta(hours=8))

# Top-level routes in the Caddyfile; longest prefix wins.
SERVICES = ['/tao-conviction', '/tao-research', '/crisis-watch', '/evm-utils', '/task-hub',
            '/health', '/reader', '/lib', '/auth-admin', '/auth', '/vpn', '/ban-status',
            '/services-status.json', '/public', '/safe-pull']
UNROUTED = '(未路由)'
BOT_RE = re.compile(r'bot|crawl|spider|slurp|preview|headless|python|curl|wget|go-http|java/|'
                    r'scan|monitor|fetch|http-client|okhttp|axios|node|libwww|facebookexternalhit',
                    re.I)
LOCAL_UA = ('vps-sweep/',)
ASSET_RE = re.compile(r'/_next/|/assets/|\.(js|mjs|css|map|png|jpe?g|gif|svg|ico|webp|woff2?|ttf|json|txt|xml|webmanifest)$', re.I)


def _h(headers, name):
    vals = headers.get(name) or headers.get(name.lower()) or []
    return vals[0] if vals else ''


def service_of(path):
    if path == '/':
        return '/'
    for prefix in sorted(SERVICES, key=len, reverse=True):
        if path == prefix or path.startswith(prefix + '/') or path.startswith(prefix + '?'):
            return prefix
    return UNROUTED


def watcher_page(path):
    rest = path[len('/tao-conviction'):].rstrip('/') or '/'
    rest = re.sub(r'^/netuid/[^/]+', '/netuid/*', rest)
    return rest


def is_local_ip(ip, local_ips):
    if ip in local_ips:
        return True
    try:
        return ipaddress.ip_address(ip).is_loopback
    except ValueError:
        return False


def classify(e, local_ips):
    req = e.get('request', {})
    headers = req.get('headers', {})
    uri = req.get('uri', '')
    path = uri.split('?', 1)[0]
    ua = _h(headers, 'User-Agent')
    ip = req.get('client_ip') or req.get('remote_ip', '')
    status = int(e.get('status', 0))
    svc = service_of(path)
    out = {'service': svc, 'page': watcher_page(path) if svc == '/tao-conviction' else None,
           'locale': e.get('locale') or 'zh', 'visitor': f'{ip}|{ua}'}

    if ua.startswith(LOCAL_UA) or is_local_ip(ip, local_ips):
        kind = 'local'
    elif not ua or not ua.startswith('Mozilla/') or BOT_RE.search(ua) or status >= 400:
        kind = 'machine'
    else:
        dest = _h(headers, 'Sec-Fetch-Dest')
        rsc = _h(headers, 'Rsc') == '1'
        prefetch = bool(_h(headers, 'Next-Router-Prefetch')) or 'prefetch' in _h(headers, 'Sec-Purpose')
        ok = 200 <= status < 300 or status == 304
        if rsc:
            nav = not prefetch
        elif dest:
            nav = dest == 'document'
        else:
            nav = 'text/html' in _h(headers, 'Accept') and not ASSET_RE.search(path)
        kind = 'human' if (nav and ok and req.get('method', 'GET') == 'GET') else 'asset'
    out['kind'] = kind
    return out


def summarize(entries, local_ips):
    s = {'services': {}, 'machine': 0, 'local': 0, 'asset': 0, 'human': 0}
    visitors = {}
    for e in entries:
        c = classify(e, local_ips)
        if c['kind'] != 'human':
            s[c['kind']] += 1
            continue
        s['human'] += 1
        svc = s['services'].setdefault(c['service'], {'views': 0, 'visitors': 0, 'pages': {}, 'locale': {}})
        svc['views'] += 1
        visitors.setdefault(c['service'], set()).add(c['visitor'])
        if c['page']:
            svc['pages'][c['page']] = svc['pages'].get(c['page'], 0) + 1
            svc['locale'][c['locale']] = svc['locale'].get(c['locale'], 0) + 1
    for name, v in visitors.items():
        s['services'][name]['visitors'] = len(v)
    return s


def render_line(s, start, end):
    head = f'🟢 網頁存取 {start:%m-%d}–{end:%m-%d}：人類頁面瀏覽 {s["human"]}'
    parts = []
    for name, v in sorted(s['services'].items(), key=lambda kv: -kv[1]['views']):
        item = f'{name} {v["views"]}／{v["visitors"]}'
        if v['pages']:
            pages = '、'.join(f'{p.lstrip("/") or "overview"} {n}'
                             for p, n in sorted(v['pages'].items(), key=lambda kv: -kv[1]))
            item += f'（{pages}；en {v["locale"].get("en", 0)}）'
        parts.append(item)
    body = f'（瀏覽／訪客）：{"，".join(parts)}' if parts else ''
    return f'{head}{body}｜機器 {s["machine"]}、本機健檢 {s["local"]}、其他瀏覽器請求 {s["asset"]}'


def _open(path):
    if path.suffix == '.gz':
        return gzip.open(path, 'rt', encoding='utf-8', errors='replace')
    return path.open(encoding='utf-8', errors='replace')


def iter_entries(log_dir, since, until):
    lo, hi = since.timestamp(), until.timestamp()
    for path in sorted(pathlib.Path(log_dir).glob('access*.log*')):
        with _open(path) as f:
            for line in f:
                try:
                    e = json.loads(line)
                except ValueError:
                    continue
                ts = e.get('ts')
                if isinstance(ts, (int, float)) and lo <= ts < hi:
                    yield e


def host_ips():
    ips = set()
    try:
        out = subprocess.run(['hostname', '-I'], capture_output=True, text=True, timeout=5).stdout
        ips.update(out.split())
    except (OSError, subprocess.TimeoutExpired):
        pass
    try:
        ips.add(socket.gethostbyname('raphtools.com'))
    except OSError:
        pass
    return ips


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.split('\n', 1)[0])
    ap.add_argument('--days', type=int, default=7)
    ap.add_argument('--log-dir', default=str(LOG_DIR))
    ap.add_argument('--no-history', action='store_true', help='do not append to weekly.jsonl')
    args = ap.parse_args(argv)
    until = dt.datetime.now(TPE).replace(hour=0, minute=0, second=0, microsecond=0)
    since = until - dt.timedelta(days=args.days)
    s = summarize(iter_entries(args.log_dir, since, until), host_ips())
    print(render_line(s, since.date(), (until - dt.timedelta(days=1)).date()))
    if not args.no_history:
        rec = {'since': since.isoformat(), 'until': until.isoformat(), **s}
        with HISTORY.open('a', encoding='utf-8') as f:
            f.write(json.dumps(rec, ensure_ascii=False) + '\n')
    return 0


if __name__ == '__main__':
    sys.exit(main())
