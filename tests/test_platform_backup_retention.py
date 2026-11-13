"""platform-backup.sh keep_recent_backups: local dated dirs keep only the newest 2 (history is in restic).

Readers that must keep working: raph-vps-state/watchdog.sh (newest dated dir + its .complete),
restore-drill.sh (newest dated dir in the restic snapshot + .complete) and RESTORE.md
("no .complete → use the previous day"). So the newest complete dir always survives too.
"""
import pathlib
import subprocess
import tempfile
import unittest

SCRIPT = pathlib.Path(__file__).resolve().parent.parent / 'scripts' / 'platform-backup.sh'


class RetentionTest(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.root = pathlib.Path(self._tmp.name) / 'backups'
        self.root.mkdir()
        for other in ('mirror', 'latest-large', 'lib-rename-20261102T012634Z'):
            (self.root / other).mkdir()
        (self.root / '.platform-backup.lock').touch()

    def tearDown(self):
        self._tmp.cleanup()

    def dated(self, *days, complete=True):
        for day in days:
            d = self.root / day
            (d / 'sqlite').mkdir(parents=True)
            if complete:
                (d / '.complete').write_text('completed=x\n')

    def prune(self):
        root = str(self.root)
        self.assertTrue(root.startswith(tempfile.gettempdir()), root)  # the function runs rm -rf
        proc = subprocess.run(['bash', '-c', 'source "$1"; BACKUP_ROOT=$2; keep_recent_backups', '_',
                               str(SCRIPT), root], capture_output=True, text=True, timeout=60)
        self.assertEqual(proc.returncode, 0, proc.stderr)
        return sorted(p.name for p in self.root.iterdir())

    def test_keeps_the_newest_two_dated_dirs_and_every_other_entry(self):
        self.dated('2026-10-18', '2026-10-25', '2026-11-01', '2026-11-06', '2026-11-07', '2026-11-08',
                   '2026-11-09', '2026-11-10', '2026-11-11', '2026-11-12')
        self.assertEqual(self.prune(), ['.platform-backup.lock', '2026-11-11', '2026-11-12',
                                        'latest-large', 'lib-rename-20261102T012634Z', 'mirror'])

    def test_todays_unfinished_dir_counts_toward_the_two(self):
        # keep_recent_backups runs before today's .complete is written
        self.dated('2026-11-10', '2026-11-11', '2026-11-12')
        self.dated('2026-11-13', complete=False)
        self.assertEqual([n for n in self.prune() if n.startswith('2026')], ['2026-11-12', '2026-11-13'])

    def test_newest_complete_dir_survives_consecutive_incomplete_runs(self):
        self.dated('2026-11-09', '2026-11-10')
        self.dated('2026-11-11', '2026-11-12', '2026-11-13', complete=False)
        self.assertEqual([n for n in self.prune() if n.startswith('2026')],
                         ['2026-11-10', '2026-11-12', '2026-11-13'])


if __name__ == '__main__':
    unittest.main()
