import tempfile
import unittest
from pathlib import Path

import lifecycle
from helpers import init_repo


class ReleaseTests(unittest.TestCase):
    def test_modified_formal_artifact_is_rejected_before_external_call(self):
        with tempfile.TemporaryDirectory() as raw:
            root = Path(raw)
            repo = init_repo(root / "repo")
            channel = root / "channel"
            lifecycle.promote(repo, "1.0.0", channel=channel, apply=True)
            artifact = next((channel / "versions" / "sample-plugin" / "1.0.0").glob("*.zip"))
            artifact.write_bytes(artifact.read_bytes() + b"drift")
            with self.assertRaisesRegex(lifecycle.LifecycleError, "E_ARTIFACT_DRIFT"):
                lifecycle.release(repo, "1.0.0", channel=channel, apply=False)


if __name__ == "__main__":
    unittest.main()
