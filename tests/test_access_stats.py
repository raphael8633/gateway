"""Behaviour of scripts/access_stats.py: who counts as a human page view."""
import datetime as dt
import gzip
import json
import pathlib
import sys
import tempfile
import unittest

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent.parent / 'scripts'))
import access_stats as A  # noqa: E402

BROWSER = 'Mozilla/5.0 (iPhone; CPU iPhone OS 18_0 like Mac OS X) AppleWebKit/605.1.15 Version/18.0 Mobile Safari/604.1'
LOCAL = {'10.0.0.5'}
TS = 1794543890.0


def entry(uri, ua=BROWSER, status=200, ip='203.0.113.7', headers=None, locale='', ts=TS, method='GET'):
    h = {'User-Agent': [ua]} if ua else {}
    h.update(headers or {})
    e = {'ts': ts, 'status': status,
         'request': {'remote_ip': ip, 'client_ip': ip, 'method': method, 'uri': uri, 'headers': h}}
    if locale:
        e['locale'] = locale
    return e


DOC = {'Sec-Fetch-Dest': ['document']}


class ClassifyTest(unittest.TestCase):
    def kind(self, e):
        return A.classify(e, LOCAL)['kind']

    def test_browser_document_load_is_human(self):
        self.assertEqual(self.kind(entry('/task-hub/', headers=DOC)), 'human')

    def test_next_client_navigation_is_human_but_prefetch_is_not(self):
        nav = entry('/tao-conviction/emission?_rsc=abc', headers={'Rsc': ['1'], 'Sec-Fetch-Dest': ['empty']})
        prefetch = entry('/tao-conviction/emission?_rsc=abc',
                         headers={'Rsc': ['1'], 'Next-Router-Prefetch': ['1'], 'Sec-Fetch-Dest': ['empty']})
        self.assertEqual(self.kind(nav), 'human')
        self.assertEqual(self.kind(prefetch), 'asset')

    def test_static_assets_and_xhr_are_not_page_views(self):
        self.assertEqual(self.kind(entry('/tao-conviction/_next/static/chunks/a.js',
                                         headers={'Sec-Fetch-Dest': ['script']})), 'asset')
        self.assertEqual(self.kind(entry('/task-hub/api/tasks', headers={'Sec-Fetch-Dest': ['empty']})), 'asset')

    def test_login_redirect_and_errors_are_not_page_views(self):
        self.assertEqual(self.kind(entry('/task-hub/', status=302, headers=DOC)), 'asset')
        self.assertEqual(self.kind(entry('/wp-login.php', status=404, headers=DOC)), 'machine')

    def test_health_check_and_this_host_count_as_local(self):
        self.assertEqual(self.kind(entry('/tao-conviction', ua='vps-sweep/1')), 'local')
        self.assertEqual(self.kind(entry('/tao-conviction', ua='curl/8.5.0', ip='10.0.0.5')), 'local')
        self.assertEqual(self.kind(entry('/tao-conviction', ip='127.0.0.1', ua='curl/8.5.0')), 'local')

    def test_browser_navigation_from_this_host_is_its_own_kind(self):
        # Shadowsocks clients reach raphtools.com from this host's IP.
        self.assertEqual(self.kind(entry('/tao-conviction', ip='10.0.0.5', headers=DOC)), 'local_browser')
        headless = 'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 HeadlessChrome/120.0 Safari/537.36'
        self.assertEqual(self.kind(entry('/reader/', ua=headless, ip='10.0.0.5', headers=DOC)), 'local')
        self.assertEqual(self.kind(entry('/tao-conviction/_next/static/a.js', ip='10.0.0.5',
                                         headers={'Sec-Fetch-Dest': ['script']})), 'local')

    def test_bots_and_scripts_from_outside_are_machine(self):
        self.assertEqual(self.kind(entry('/tao-conviction', ua='curl/8.5.0')), 'machine')
        self.assertEqual(self.kind(entry('/', ua='Mozilla/5.0 (compatible; Googlebot/2.1)', headers=DOC)), 'machine')
        self.assertEqual(self.kind(entry('/', ua='')), 'machine')

    def test_old_browser_without_fetch_metadata_falls_back_to_accept(self):
        e = entry('/reader/', headers={'Accept': ['text/html,application/xhtml+xml']})
        self.assertEqual(self.kind(e), 'human')


class ServiceTest(unittest.TestCase):
    def test_service_and_watcher_subpage(self):
        c = A.classify(entry('/tao-conviction/netuid/64?x=1', headers=DOC, locale='en'), LOCAL)
        self.assertEqual((c['service'], c['page'], c['locale']), ('/tao-conviction', '/netuid/*', 'en'))
        c = A.classify(entry('/tao-conviction', headers=DOC), LOCAL)
        self.assertEqual((c['service'], c['page']), ('/tao-conviction', '/'))
        c = A.classify(entry('/tao-conviction/emission?_rsc=1', headers={'Rsc': ['1']}), LOCAL)
        self.assertEqual(c['page'], '/emission')

    def test_other_services(self):
        self.assertEqual(A.classify(entry('/', headers=DOC), LOCAL)['service'], '/')
        self.assertEqual(A.classify(entry('/lib/private/view/x.md', headers=DOC), LOCAL)['service'], '/lib')
        self.assertEqual(A.classify(entry('/reader/book/1', headers=DOC), LOCAL)['service'], '/reader')
        self.assertEqual(A.classify(entry('/nope', headers=DOC, status=404), LOCAL)['service'], '(未路由)')


class SummaryTest(unittest.TestCase):
    def test_line_counts_humans_visitors_machine_and_local(self):
        es = [
            entry('/tao-conviction', headers=DOC),
            entry('/tao-conviction/emission?_rsc=a', headers={'Rsc': ['1']}),
            entry('/tao-conviction/emission', headers=DOC, ip='198.51.100.9', locale='en'),
            entry('/task-hub/', headers=DOC),
            entry('/tao-conviction', ua='vps-sweep/1'),
            entry('/wp-login.php', status=404, ua='python-requests/2'),
            entry('/tao-conviction/_next/static/a.js', headers={'Sec-Fetch-Dest': ['script']}),
            entry('/task-hub/', headers=DOC, ip='10.0.0.5'),
        ]
        s = A.summarize(es, LOCAL)
        self.assertEqual(s['services']['/tao-conviction']['views'], 3)
        self.assertEqual(s['services']['/tao-conviction']['visitors'], 2)
        self.assertEqual(s['services']['/tao-conviction']['pages'], {'/': 1, '/emission': 2})
        self.assertEqual(s['services']['/tao-conviction']['locale'], {'en': 1, 'zh': 2})
        self.assertEqual((s['machine'], s['local'], s['asset']), (1, 1, 1))
        line = A.render_line(s, dt.date(2026, 11, 6), dt.date(2026, 11, 12))
        self.assertTrue(line.startswith('🟢 '))
        self.assertNotIn('\n', line)
        self.assertIn('/tao-conviction 3／2', line)
        self.assertIn('emission 2', line)
        self.assertIn('en 1', line)
        self.assertIn('機器 1', line)
        self.assertIn('本機健檢 1', line)
        self.assertEqual(s['local_browser'], 1)
        self.assertIn('本機瀏覽器（Shadowsocks 等）1', line)

    def test_watcher_beacon_events_are_counted_per_event(self):
        beacon = {'Sec-Fetch-Dest': ['empty']}
        es = [
            entry('/tao-conviction/api/beacon?e=simulator-open', headers=beacon, status=204),
            entry('/tao-conviction/api/beacon?e=simulator-open', headers=beacon, status=204, ip='198.51.100.9'),
            entry('/tao-conviction/api/beacon?e=simulator-open', headers=beacon, status=204),
            entry('/tao-conviction/api/beacon?e=simulator-open', ua='curl/8.5.0', status=204),
        ]
        s = A.summarize(es, LOCAL)
        self.assertEqual(s['events'], {'simulator-open': {'count': 3, 'visitors': 2}})
        self.assertEqual(s['human'], 0)
        line = A.render_line(s, dt.date(2026, 11, 6), dt.date(2026, 11, 12))
        self.assertIn('試算器展開 3／2', line)

    def test_empty_window_still_reports(self):
        line = A.render_line(A.summarize([], LOCAL), dt.date(2026, 11, 6), dt.date(2026, 11, 12))
        self.assertTrue(line.startswith('🟢 '))
        self.assertIn('人類頁面瀏覽 0', line)


class ReadTest(unittest.TestCase):
    def test_reads_rolled_gzip_and_filters_window(self):
        with tempfile.TemporaryDirectory() as d:
            d = pathlib.Path(d)
            old = entry('/a', ts=TS - 10 * 86400)
            inside = entry('/b', ts=TS - 86400)
            with gzip.open(d / 'access-2026-11-10T00-00-00.000.log.gz', 'wt') as f:
                f.write(json.dumps(old) + '\n' + json.dumps(inside) + '\n')
            (d / 'access.log').write_text(json.dumps(entry('/c', ts=TS)) + '\nnot json\n')
            since = dt.datetime.fromtimestamp(TS - 7 * 86400, dt.timezone.utc)
            until = dt.datetime.fromtimestamp(TS + 1, dt.timezone.utc)
            uris = [e['request']['uri'] for e in A.iter_entries(d, since, until)]
            self.assertEqual(sorted(uris), ['/b', '/c'])


if __name__ == '__main__':
    unittest.main()
