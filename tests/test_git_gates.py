import tempfile
import unittest
import json
from unittest import mock
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

    def test_configured_discovery_root_blocks_duplicate_skill(self):
        with tempfile.TemporaryDirectory() as raw:
            root = Path(raw)
            repo = init_repo(root / "repo")
            discovery = root / "runtime"
            duplicate = discovery / "sample"
            duplicate.mkdir(parents=True)
            (duplicate / "SKILL.md").write_text(
                "---\nname: sample-skill\ndescription: Legacy duplicate.\n---\n",
                encoding="utf-8",
            )
            config = json.loads((repo / "lifecycle.json").read_text(encoding="utf-8"))
            config["discovery_roots"] = [str(discovery)]
            (repo / "lifecycle.json").write_text(json.dumps(config), encoding="utf-8")
            lifecycle.git_run(repo, "add", "lifecycle.json")
            lifecycle.git_run(repo, "commit", "-m", "configure discovery audit")
            with self.assertRaisesRegex(lifecycle.LifecycleError, "E_DISCOVERY"):
                lifecycle.promotion_preflight(repo, "1.0.0")

    def test_develop_change_after_preflight_does_not_advance_main(self):
        with tempfile.TemporaryDirectory() as raw:
            repo = init_repo(Path(raw) / "repo")
            validated = lifecycle.promotion_preflight(repo, "1.0.0")
            (repo / "later.txt").write_text("not validated", encoding="utf-8")
            lifecycle.git_run(repo, "add", "later.txt")
            lifecycle.git_run(repo, "commit", "-m", "later change")
            main_before = lifecycle.git_output(repo, "rev-parse", "main")
            with mock.patch("lifecycle.promotion_preflight", return_value=validated):
                with self.assertRaisesRegex(lifecycle.LifecycleError, "E_GIT_CHANGED"):
                    lifecycle.promote(repo, "1.0.0", channel=Path(raw) / "channel", apply=True)
            self.assertEqual(main_before, lifecycle.git_output(repo, "rev-parse", "main"))


if __name__ == "__main__":
    unittest.main()
