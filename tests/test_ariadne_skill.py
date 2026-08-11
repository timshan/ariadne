import ast
import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SKILL = ROOT / "skills" / "ariadne"


class AriadneSkillTests(unittest.TestCase):
    def test_plugin_and_skill_identity_are_final_and_consistent(self):
        manifest = json.loads(
            (ROOT / ".codex-plugin" / "plugin.json").read_text(encoding="utf-8")
        )
        skill = (SKILL / "SKILL.md").read_text(encoding="utf-8")
        self.assertEqual(manifest["name"], "ariadne")
        self.assertEqual(manifest["version"], "1.0.0")
        self.assertEqual(manifest["skills"], "./skills/")
        self.assertIn("name: ariadne", skill)
        self.assertIn("description:", skill)

    def test_skill_defines_all_boundaries_without_other_skill_dependencies(self):
        skill = (SKILL / "SKILL.md").read_text(encoding="utf-8")
        for phrase in (
            "Development boundary",
            "Formal boundary",
            "Release boundary",
            "`develop`",
            "`main`",
            "dry-run",
            "duplicate",
            "references/lifecycle-policy.md",
            "scripts/ariadne.py",
        ):
            with self.subTest(phrase=phrase):
                self.assertIn(phrase, skill)
        for forbidden in ("$eureka", "$daedalus", "$herdr", "$skill-creator"):
            with self.subTest(forbidden=forbidden):
                self.assertNotIn(forbidden, skill.lower())

    def test_controller_uses_only_python_standard_library(self):
        tree = ast.parse((ROOT / "lifecycle.py").read_text(encoding="utf-8"))
        imports = set()
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                imports.update(alias.name.split(".")[0] for alias in node.names)
            elif isinstance(node, ast.ImportFrom) and node.module:
                imports.add(node.module.split(".")[0])
        standard = set(sys.stdlib_module_names)
        self.assertFalse(imports - standard, f"non-standard imports: {imports - standard}")

    def test_bundled_launcher_works_from_unrelated_directory(self):
        launcher = SKILL / "scripts" / "ariadne.py"
        with tempfile.TemporaryDirectory() as raw:
            completed = subprocess.run(
                [sys.executable, str(launcher), "--help"],
                cwd=raw,
                text=True,
                capture_output=True,
                check=False,
            )
        self.assertEqual(completed.returncode, 0, completed.stderr)
        self.assertIn("inspect", completed.stdout)
        self.assertIn("promote", completed.stdout)
        self.assertIn("release", completed.stdout)
        self.assertIn("rollback", completed.stdout)

    def test_self_lifecycle_configuration_runs_repository_tests(self):
        config = json.loads((ROOT / "lifecycle.json").read_text(encoding="utf-8"))
        self.assertEqual(config["plugin_path"], ".")
        self.assertEqual(config["discovery_roots"], ["~/.codex/skills", "~/.agents/skills"])
        self.assertIn(
            ["python3", "-m", "unittest", "discover", "-s", "tests", "-v"],
            config["checks"],
        )


if __name__ == "__main__":
    unittest.main()
