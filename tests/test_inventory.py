import tempfile
import unittest
from pathlib import Path

import lifecycle


class InventoryTests(unittest.TestCase):
    def test_inventory_keeps_distinct_payloads_and_does_not_write(self):
        with tempfile.TemporaryDirectory() as raw:
            root = Path(raw)
            paths = []
            for index, body in enumerate(("one", "two")):
                folder = root / str(index)
                folder.mkdir()
                skill = folder / "SKILL.md"
                skill.write_text(
                    f"---\nname: shared\ndescription: {body}\n---\n\n{body}\n",
                    encoding="utf-8",
                )
                paths.append(skill)
            before = [path.read_bytes() for path in paths]
            report = lifecycle.inspect_roots([root])
            self.assertEqual(len(report["skills"]), 2)
            self.assertNotEqual(report["skills"][0]["sha256"], report["skills"][1]["sha256"])
            self.assertEqual(before, [path.read_bytes() for path in paths])


if __name__ == "__main__":
    unittest.main()
