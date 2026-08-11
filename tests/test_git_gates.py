import tempfile
import unittest
import json
import sys
from unittest import mock
from pathlib import Path

import lifecycle
from helpers import init_repo


class GitGateTests(unittest.TestCase):
    def test_independence_failure_blocks_promotion_preflight(self):
        with tempfile.TemporaryDirectory() as raw:
            repo = init_repo(Path(raw) / "repo")
            with mock.patch(
                "lifecycle.scan_skill_dependencies",
                side_effect=lifecycle.LifecycleError("E_SKILL_DEPENDENCY: fixture"),
            ), mock.patch("lifecycle._run_checks") as checks:
                with self.assertRaisesRegex(lifecycle.LifecycleError, "E_SKILL_DEPENDENCY"):
                    lifecycle.promotion_preflight(repo, "1.0.0")
            checks.assert_not_called()

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

    def test_project_check_cannot_mutate_packaged_payload(self):
        with tempfile.TemporaryDirectory() as raw:
            repo = init_repo(Path(raw) / "repo")
            config_path = repo / "lifecycle.json"
            config = lifecycle.read_json(config_path)
            config["checks"] = [
                [
                    sys.executable,
                    "-c",
                    "from pathlib import Path; Path('skills/sample/SKILL.md').write_text('mutated', encoding='utf-8')",
                ]
            ]
            config_path.write_text(json.dumps(config), encoding="utf-8")
            lifecycle.git_run(repo, "add", "lifecycle.json")
            lifecycle.git_run(repo, "commit", "-m", "configure mutating project check")
            with mock.patch("lifecycle.verify_standalone_install") as standalone:
                with self.assertRaisesRegex(lifecycle.LifecycleError, "E_PAYLOAD_CHANGED"):
                    lifecycle.promotion_preflight(repo, "1.0.0")
            standalone.assert_not_called()

    def test_formal_artifact_must_match_standalone_validated_bytes(self):
        with tempfile.TemporaryDirectory() as raw:
            root = Path(raw)
            repo = init_repo(root / "repo")
            (repo / ".gitignore").write_text("generated.txt\n", encoding="utf-8")
            lifecycle.git_run(repo, "add", ".gitignore")
            lifecycle.git_run(repo, "commit", "-m", "ignore generated payload fixture")
            baseline = lifecycle.build_artifact(repo, root / "baseline.zip")
            validated = {
                "plugin": "sample-plugin",
                "version": "1.0.0",
                "commit": lifecycle.git_output(repo, "rev-parse", "develop"),
                "formal_tag": "formal/v1.0.0",
                "config": lifecycle.read_json(repo / "lifecycle.json"),
                "plugin_path": str(repo),
                "independence": {
                    "standalone": {"artifact_sha256": baseline["sha256"]}
                },
            }
            (repo / "generated.txt").write_text("not validated", encoding="utf-8")
            self.assertEqual(lifecycle.git_output(repo, "status", "--porcelain"), "")
            with mock.patch("lifecycle.promotion_preflight", return_value=validated):
                with self.assertRaisesRegex(lifecycle.LifecycleError, "E_PAYLOAD_CHANGED"):
                    lifecycle.promote(repo, "1.0.0", channel=root / "channel", apply=True)


if __name__ == "__main__":
    unittest.main()
