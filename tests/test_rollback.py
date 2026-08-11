import tempfile
import unittest
from pathlib import Path

import lifecycle
from helpers import init_repo


class RollbackTests(unittest.TestCase):
    def test_rollback_switches_current_without_removing_versions(self):
        with tempfile.TemporaryDirectory() as raw:
            root = Path(raw)
            repo = init_repo(root / "repo", version="1.0.0")
            channel = root / "channel"
            lifecycle.promote(repo, "1.0.0", channel=channel, apply=True)
            lifecycle.set_manifest_version(repo, "1.1.0")
            lifecycle.git_run(repo, "add", ".codex-plugin/plugin.json")
            lifecycle.git_run(repo, "commit", "-m", "version 1.1.0")
            lifecycle.promote(repo, "1.1.0", channel=channel, apply=True)
            lifecycle.rollback("sample-plugin", "1.0.0", channel=channel, apply=True)
            lock = lifecycle.read_json(channel / "formal-lock.json")
            self.assertEqual(lock["plugins"]["sample-plugin"]["current_formal"], "1.0.0")
            self.assertTrue((channel / "versions" / "sample-plugin" / "1.1.0").is_dir())


if __name__ == "__main__":
    unittest.main()
