import tempfile
import unittest
from pathlib import Path

import lifecycle
from helpers import init_repo


class DryRunTests(unittest.TestCase):
    def test_promote_dry_run_changes_neither_git_nor_channel(self):
        with tempfile.TemporaryDirectory() as raw:
            root = Path(raw)
            repo = init_repo(root / "repo")
            channel = root / "channel"
            before = lifecycle.git_output(repo, "rev-parse", "HEAD")
            result = lifecycle.promote(repo, "1.0.0", channel=channel, apply=False)
            self.assertEqual(result["action"], "dry-run")
            self.assertEqual(before, lifecycle.git_output(repo, "rev-parse", "HEAD"))
            self.assertFalse(channel.exists())

    def test_repeated_apply_is_idempotent_and_keeps_lock_bytes(self):
        with tempfile.TemporaryDirectory() as raw:
            root = Path(raw)
            repo = init_repo(root / "repo")
            channel = root / "channel"
            lifecycle.promote(repo, "1.0.0", channel=channel, apply=True)
            before = (channel / "formal-lock.json").read_bytes()
            result = lifecycle.promote(repo, "1.0.0", channel=channel, apply=True)
            self.assertEqual(result["action"], "idempotent")
            self.assertEqual(before, (channel / "formal-lock.json").read_bytes())


if __name__ == "__main__":
    unittest.main()
