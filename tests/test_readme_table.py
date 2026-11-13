"""Behaviour of readme_table.py (the one README parser) and services-status.py."""
import importlib.util
import pathlib
import sys
import tempfile
import unittest
from unittest import mock

GATEWAY = pathlib.Path(__file__).resolve().parent.parent
sys.path.insert(0, str(GATEWAY))
import readme_table as R  # noqa: E402

README = """# Workspace

| 專案名稱 | 說明 | 技術棧 | Gateway | Repo | Systemd Service |
|---|---|---|---|---|---|
| [evm-utils](evm-utils/) | EVM `grove` 與 safe-pull | Python stdlib WSGI + SQLite | /evm-utils/:EVM Utils | x | `evm-utils.service`, `evm-utils-grove-tick.timer`（user） |
| [crisis-watch](crisis-watch/) | 危機預警 | Python stdlib WSGI | /crisis-watch/:Crisis Watch | x | `crisis-watch-web.service`, `crisis-watch.timer`（user）, `job-crisis-watch-daily.timer`（user，raph-platform 排程） |
| [subtensor-hub](subtensor-hub/) | 研究 | Next.js + Python | /tao-conviction:Conviction, /tao-research:Research | x | `bittensor-conviction-watcher.service` |
| [task-hub](task-hub/) | 任務 | Next.js | /task-hub | x | task-hub |
| [cli-tool](cli-tool/) | 沒有網頁 | Go | - | x | — |

## 已歸檔專案

| 專案名稱 | 說明 | 恢復方式 |
|---|---|---|
| old | 舊的 | git clone |
"""


def load_rows(text=README):
    with tempfile.NamedTemporaryFile('w', suffix='.md', delete=False, encoding='utf-8') as f:
        f.write(text)
    return R.parse_readme(f.name)


class ParseReadmeTest(unittest.TestCase):
    def test_only_rows_with_gateway_path(self):
        rows = load_rows()
        self.assertEqual([r.name for r in rows], ['evm-utils', 'crisis-watch', 'subtensor-hub', 'task-hub'])
        self.assertEqual(rows[0].desc, 'EVM grove 與 safe-pull')

    def test_gateway_entries_carry_their_own_title(self):
        rows = {r.name: r for r in load_rows()}
        self.assertEqual(rows['subtensor-hub'].entries,
                         [('/tao-conviction', 'Conviction'), ('/tao-research', 'Research')])
        self.assertEqual(rows['task-hub'].entries, [('/task-hub', 'task-hub')])

    def test_units_keep_user_scope_and_drop_annotation(self):
        rows = {r.name: r for r in load_rows()}
        self.assertEqual(rows['crisis-watch'].units, [
            ('crisis-watch-web.service', 'system'),
            ('crisis-watch.timer', 'user'),
            ('job-crisis-watch-daily.timer', 'user'),
        ])
        self.assertEqual(rows['evm-utils'].units[1], ('evm-utils-grove-tick.timer', 'user'))
        self.assertEqual(rows['task-hub'].units, [('task-hub.service', 'system')])

    def test_derive_label(self):
        self.assertEqual(R.derive_label('Python stdlib WSGI + SQLite'), 'WSGI')
        self.assertEqual(R.derive_label('Next.js + Python'), 'Next.js')
        self.assertEqual(R.derive_label('Go'), 'Go')


def load_services_status():
    spec = importlib.util.spec_from_file_location('services_status', GATEWAY / 'scripts' / 'services-status.py')
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


class ServicesStatusTest(unittest.TestCase):
    def setUp(self):
        self.S = load_services_status()

    def test_service_map_uses_real_unit_names(self):
        with tempfile.NamedTemporaryFile('w', suffix='.md', delete=False, encoding='utf-8') as f:
            f.write(README)
        with mock.patch.object(self.S, 'README_PATH', pathlib.Path(f.name)):
            m = self.S.load_service_map()
        self.assertEqual(m['/crisis-watch/'][1], ('crisis-watch.timer', 'user'))
        self.assertTrue(all('（' not in u for units in m.values() for u, _ in units))

    def test_user_units_are_queried_on_the_user_manager(self):
        calls = []

        def fake_run(argv, **kw):
            calls.append((argv, kw.get('env') or {}))
            return mock.Mock(stdout='active\n')

        with mock.patch.object(self.S.subprocess, 'run', fake_run), \
                mock.patch.object(self.S.shutil, 'which', return_value='/usr/bin/systemctl'):
            self.assertEqual(self.S._is_active('crisis-watch.timer', 'user'), 'up')
            self.assertEqual(self.S._is_active('task-hub.service', 'system'), 'up')
        self.assertEqual(calls[0][0], ['systemctl', '--user', 'is-active', 'crisis-watch.timer'])
        self.assertIn('XDG_RUNTIME_DIR', calls[0][1])
        self.assertEqual(calls[1][0], ['systemctl', 'is-active', 'task-hub.service'])


if __name__ == '__main__':
    unittest.main()
