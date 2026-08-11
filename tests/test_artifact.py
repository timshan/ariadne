import tempfile
import unittest
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


if __name__ == "__main__":
    unittest.main()
