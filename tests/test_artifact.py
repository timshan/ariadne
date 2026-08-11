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


if __name__ == "__main__":
    unittest.main()
