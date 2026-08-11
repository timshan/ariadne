import tempfile
import unittest
from pathlib import Path

import lifecycle


class InspectTests(unittest.TestCase):
    def test_duplicate_names_and_symlinks_fail_formal_gate(self):
        with tempfile.TemporaryDirectory() as raw:
            root = Path(raw)
            for folder in (root / "a", root / "b"):
                folder.mkdir()
                (folder / "SKILL.md").write_text(
                    "---\nname: duplicate\ndescription: fixture\n---\n", encoding="utf-8"
                )
            (root / "linked").symlink_to(root / "a", target_is_directory=True)
            report = lifecycle.inspect_roots([root])
            self.assertEqual(len(report["duplicates"]["duplicate"]), 2)
            self.assertTrue(report["symlinks"])
            self.assertFalse(report["formal_ready"])


if __name__ == "__main__":
    unittest.main()
