import ast
import json
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock

import lifecycle


ROOT = Path(__file__).resolve().parents[1]
PLUGIN = ROOT / "plugins" / "ariadne"
SKILL = PLUGIN / "skills" / "ariadne"


class AriadneSkillTests(unittest.TestCase):
    def test_plugin_and_skill_identity_are_final_and_consistent(self):
        manifest = json.loads(
            (PLUGIN / ".codex-plugin" / "plugin.json").read_text(encoding="utf-8")
        )
        skill = (SKILL / "SKILL.md").read_text(encoding="utf-8")
        self.assertEqual(manifest["name"], "ariadne")
        self.assertEqual(manifest["version"], "1.1.1")
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

    def test_skill_requires_explicit_current_conversation_apply_authorization(self):
        skill = (SKILL / "SKILL.md").read_text(encoding="utf-8").lower()
        for phrase in (
            "explicit user authorization",
            "current conversation",
            "exact operation",
            "never construct or run `--apply`",
        ):
            with self.subTest(phrase=phrase):
                self.assertIn(phrase, skill)

    def test_runtime_policy_preserves_apply_authorization_gate(self):
        policy = (SKILL / "references" / "lifecycle-policy.md").read_text(
            encoding="utf-8"
        ).lower()
        for phrase in (
            "mutation authorization gate",
            "explicit user authorization",
            "current conversation",
            "exact operation",
            "broad prior approval is insufficient",
        ):
            with self.subTest(phrase=phrase):
                self.assertIn(phrase, policy)

    def test_controller_uses_only_python_standard_library(self):
        tree = ast.parse((PLUGIN / "lifecycle.py").read_text(encoding="utf-8"))
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
        self.assertIn("independence", completed.stdout)
        self.assertIn("promote", completed.stdout)
        self.assertIn("release", completed.stdout)
        self.assertIn("rollback", completed.stdout)

    def test_self_lifecycle_configuration_runs_repository_tests(self):
        config = json.loads((ROOT / "lifecycle.json").read_text(encoding="utf-8"))
        self.assertEqual(config["plugin_path"], "plugins/ariadne")
        self.assertEqual(
            config["package_paths"],
            [".codex-plugin", "LICENSE", "lifecycle.py", "skills"],
        )
        self.assertEqual(config["discovery_roots"], ["~/.codex/skills", "~/.agents/skills"])
        self.assertEqual(
            config["independence"]["standalone_checks"],
            [["python3", "skills/ariadne/scripts/ariadne.py", "--help"]],
        )
        self.assertIn(
            ["python3", "-m", "unittest", "discover", "-s", "tests", "-v"],
            config["checks"],
        )

    def test_repository_marketplace_points_only_to_installable_plugin(self):
        marketplace = json.loads(
            (ROOT / ".agents" / "plugins" / "marketplace.json").read_text(
                encoding="utf-8"
            )
        )
        self.assertEqual(marketplace["name"], "ariadne")
        self.assertEqual(len(marketplace["plugins"]), 1)
        entry = marketplace["plugins"][0]
        self.assertEqual(entry["name"], "ariadne")
        self.assertEqual(entry["source"], {"source": "local", "path": "./plugins/ariadne"})
        self.assertEqual(entry["policy"]["installation"], "AVAILABLE")
        self.assertEqual(entry["policy"]["authentication"], "ON_INSTALL")

    def test_installable_plugin_tree_contains_no_python_cache(self):
        leaked = [
            path.relative_to(PLUGIN).as_posix()
            for path in PLUGIN.rglob("*")
            if path.name == "__pycache__" or path.suffix in {".pyc", ".pyo"}
        ]
        self.assertEqual(leaked, [])

    def test_default_formal_channel_is_outside_source_and_discovery_roots(self):
        config = json.loads((ROOT / "lifecycle.json").read_text(encoding="utf-8"))
        with mock.patch.dict(
            os.environ,
            {"ARIADNE_FORMAL_CHANNEL": "", "SKILL_LIFECYCLE_CHANNEL": ""},
        ):
            channel = lifecycle.default_channel().resolve()
        boundaries = [
            (ROOT / config["plugin_path"]).resolve(),
            *(Path(raw).expanduser().resolve() for raw in config["discovery_roots"]),
        ]
        for boundary in boundaries:
            with self.subTest(boundary=boundary):
                overlap = (
                    channel == boundary
                    or channel in boundary.parents
                    or boundary in channel.parents
                )
                self.assertFalse(overlap)


if __name__ == "__main__":
    unittest.main()
