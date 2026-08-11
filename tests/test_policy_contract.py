import unittest
from pathlib import Path


class PolicyContractTests(unittest.TestCase):
    def test_policy_defines_three_boundaries_and_two_permanent_branches(self):
        policy = (Path(__file__).parents[1] / "policy.md").read_text(encoding="utf-8")
        for phrase in (
            "Development boundary",
            "Formal boundary",
            "Release boundary",
            "`develop`",
            "`main`",
            "fast-forward-only",
            "formal/vX.Y.Z",
            "vX.Y.Z",
            "cross-Skill",
            "standalone",
            "sole enabled Plugin",
        ):
            with self.subTest(phrase=phrase):
                self.assertIn(phrase, policy)


if __name__ == "__main__":
    unittest.main()
