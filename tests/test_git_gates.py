import tempfile
import unittest
from pathlib import Path

import lifecycle
from helpers import init_repo


class GitGateTests(unittest.TestCase):
    def test_dirty_tree_fails_without_changing_head(self):
        with tempfile.TemporaryDirectory() as raw:
            repo = init_repo(Path(raw) / "repo")
            before = lifecycle.git_output(repo, "rev-parse", "HEAD")
            (repo / "untracked.txt").write_text("dirty", encoding="utf-8")
            with self.assertRaisesRegex(lifecycle.LifecycleError, "E_GIT_DIRTY"):
                lifecycle.promotion_preflight(repo, "1.0.0")
            self.assertEqual(before, lifecycle.git_output(repo, "rev-parse", "HEAD"))

    def test_third_local_branch_is_rejected(self):
        with tempfile.TemporaryDirectory() as raw:
            repo = init_repo(Path(raw) / "repo")
            lifecycle.git_run(repo, "branch", "feature-left-behind")
            with self.assertRaisesRegex(lifecycle.LifecycleError, "E_GIT_BRANCH_SET"):
                lifecycle.promotion_preflight(repo, "1.0.0")


if __name__ == "__main__":
    unittest.main()
