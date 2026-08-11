import json
import tempfile
import unittest
import zipfile
from pathlib import Path

import lifecycle
from helpers import init_repo


class ArtifactTests(unittest.TestCase):
    def test_artifact_is_deterministic(self):
        with tempfile.TemporaryDirectory() as raw:
            root = Path(raw)
            repo = init_repo(root / "repo")
            first = lifecycle.build_artifact(repo, root / "one.zip")
            second = lifecycle.build_artifact(repo, root / "two.zip")
            self.assertEqual(first["sha256"], second["sha256"])
            self.assertEqual((root / "one.zip").read_bytes(), (root / "two.zip").read_bytes())

    def test_artifact_rejects_symlink(self):
        with tempfile.TemporaryDirectory() as raw:
            root = Path(raw)
            repo = init_repo(root / "repo")
            (repo / "bad-link").symlink_to(repo / "lifecycle.json")
            with self.assertRaises(lifecycle.LifecycleError):
                lifecycle.build_artifact(repo, root / "bad.zip")

    def test_artifact_mode_is_normalized_across_source_permissions(self):
        with tempfile.TemporaryDirectory() as raw:
            root = Path(raw)
            repo = init_repo(root / "repo")
            source = repo / "skills" / "sample" / "SKILL.md"
            first = lifecycle.build_artifact(repo, root / "one.zip")
            source.chmod(0o755)
            second = lifecycle.build_artifact(repo, root / "two.zip")
            self.assertEqual(first["sha256"], second["sha256"])

    def test_safe_extract_rejects_parent_path(self):
        with tempfile.TemporaryDirectory() as raw:
            root = Path(raw)
            archive = root / "malicious.zip"
            with zipfile.ZipFile(archive, "w") as handle:
                handle.writestr("../escape", b"bad")
            with self.assertRaisesRegex(lifecycle.LifecycleError, "E_ARCHIVE_PATH"):
                lifecycle._safe_extract(archive, root / "payload")
            self.assertFalse((root / "escape").exists())

    def test_package_paths_exclude_generated_channel_and_its_duplicate_skill(self):
        with tempfile.TemporaryDirectory() as raw:
            root = Path(raw)
            repo = init_repo(root / "repo")
            config = lifecycle.read_json(repo / "lifecycle.json")
            config["package_paths"] = [".codex-plugin", "skills", "lifecycle.json"]
            (repo / "lifecycle.json").write_text(json.dumps(config), encoding="utf-8")
            (repo / ".gitignore").write_text("channels/\n", encoding="utf-8")
            duplicate = repo / "channels" / "formal" / "skills" / "sample"
            duplicate.mkdir(parents=True)
            (duplicate / "SKILL.md").write_text(
                "---\nname: sample-skill\ndescription: generated duplicate\n---\n",
                encoding="utf-8",
            )
            lifecycle.git_run(repo, "add", "lifecycle.json", ".gitignore")
            lifecycle.git_run(repo, "commit", "-m", "scope package payload")
            result = lifecycle.promotion_preflight(repo, "1.0.0")
            self.assertEqual(result["plugin"], "sample-plugin")
            artifact = root / "sample.zip"
            lifecycle.build_artifact(repo, artifact)
            with zipfile.ZipFile(artifact) as handle:
                self.assertFalse(any(name.startswith("channels/") for name in handle.namelist()))


if __name__ == "__main__":
    unittest.main()
