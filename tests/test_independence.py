import json
import os
import tempfile
import unittest
from pathlib import Path
from unittest import mock

import lifecycle
from helpers import init_repo


FAKE_CODEX = '''#!/usr/bin/env python3
import json
import os
import shutil
import sys
from pathlib import Path

args = sys.argv[1:]
payload = os.environ["ARIADNE_STANDALONE_PAYLOAD"]
plugin = os.environ["ARIADNE_STANDALONE_PLUGIN"]
version = os.environ["ARIADNE_STANDALONE_VERSION"]
marketplace = os.environ["ARIADNE_STANDALONE_MARKETPLACE"]
installed_path = Path(os.environ["CODEX_HOME"]) / "plugins" / "cache" / marketplace / plugin / version
if os.environ.get("FAKE_CODEX_OUTSIDE_PATH"):
    installed_path = Path(payload)
record = {
    "pluginId": f"{plugin}@{marketplace}",
    "name": plugin,
    "marketplaceName": marketplace,
    "version": version,
    "installed": True,
    "enabled": True,
    "installedPath": str(installed_path),
}
if args[:3] == ["plugin", "marketplace", "add"]:
    raise SystemExit(0)
if args[:2] == ["plugin", "add"]:
    if installed_path != Path(payload):
        installed_path.parent.mkdir(parents=True, exist_ok=True)
        shutil.copytree(payload, installed_path)
    print(json.dumps(record))
    raise SystemExit(0)
if args[:3] == ["plugin", "list", "--json"]:
    installed = [record]
    if os.environ.get("FAKE_CODEX_EXTRA_PLUGIN"):
        installed.append({
            "pluginId": "other@elsewhere",
            "name": "other",
            "marketplaceName": "elsewhere",
            "version": "1.0.0",
            "installed": True,
            "enabled": True,
            "installedPath": payload,
        })
    print(json.dumps({"installed": installed, "available": []}))
    raise SystemExit(0)
print(f"unsupported fake codex call: {args}", file=sys.stderr)
raise SystemExit(3)
'''


class IndependenceTests(unittest.TestCase):
    def fake_codex(self, root: Path, *, extra_plugin: bool = False, outside_path: bool = False):
        binary = root / "bin"
        binary.mkdir()
        codex = binary / "codex"
        source = FAKE_CODEX.replace(
            'if os.environ.get("FAKE_CODEX_OUTSIDE_PATH"):',
            f"if {outside_path!r}:",
        ).replace(
            'if os.environ.get("FAKE_CODEX_EXTRA_PLUGIN"):',
            f"if {extra_plugin!r}:",
        )
        codex.write_text(source, encoding="utf-8")
        codex.chmod(0o755)
        return mock.patch.dict(os.environ, {"PATH": f"{binary}{os.pathsep}{os.environ['PATH']}"})

    def test_missing_independence_contract_fails(self):
        with tempfile.TemporaryDirectory() as raw:
            repo = init_repo(Path(raw) / "repo")
            config_path = repo / "lifecycle.json"
            config = lifecycle.read_json(config_path)
            config.pop("independence")
            config_path.write_text(json.dumps(config), encoding="utf-8")
            with self.assertRaisesRegex(lifecycle.LifecycleError, "E_INDEPENDENCE_CONFIG"):
                lifecycle.independence_preflight(repo)

    def test_explicit_other_skill_call_is_rejected(self):
        with tempfile.TemporaryDirectory() as raw:
            repo = init_repo(Path(raw) / "repo")
            skill = repo / "skills" / "sample" / "SKILL.md"
            skill.write_text(skill.read_text(encoding="utf-8") + "\nUse $other-skill first.\n", encoding="utf-8")
            with self.assertRaisesRegex(lifecycle.LifecycleError, "E_SKILL_DEPENDENCY") as raised:
                lifecycle.independence_preflight(repo)
            self.assertIn("other-skill", str(raised.exception))
            self.assertIn("SKILL.md", str(raised.exception))

    def test_external_skill_path_is_rejected_even_when_not_discovered(self):
        with tempfile.TemporaryDirectory() as raw:
            repo = init_repo(Path(raw) / "repo")
            skill = repo / "skills" / "sample" / "SKILL.md"
            skill.write_text(
                skill.read_text(encoding="utf-8")
                + "\nRead ~/.codex/skills/hidden-helper/SKILL.md first.\n",
                encoding="utf-8",
            )
            with self.assertRaisesRegex(lifecycle.LifecycleError, "E_SKILL_DEPENDENCY") as raised:
                lifecycle.independence_preflight(repo)
            self.assertIn("hidden-helper", str(raised.exception))
            self.assertIn("absolute-skill-path", str(raised.exception))

    def test_discovered_external_skill_name_is_rejected_without_dollar_prefix(self):
        with tempfile.TemporaryDirectory() as raw:
            root = Path(raw)
            repo = init_repo(root / "repo")
            external = root / "external" / "helper"
            external.mkdir(parents=True)
            (external / "SKILL.md").write_text(
                "---\nname: helper-skill\ndescription: helper\n---\n", encoding="utf-8"
            )
            config_path = repo / "lifecycle.json"
            config = lifecycle.read_json(config_path)
            config["discovery_roots"] = [str(root / "external")]
            config_path.write_text(json.dumps(config), encoding="utf-8")
            skill = repo / "skills" / "sample" / "SKILL.md"
            skill.write_text(skill.read_text(encoding="utf-8") + "\nInvoke helper-skill.\n", encoding="utf-8")
            with self.assertRaisesRegex(lifecycle.LifecycleError, "E_SKILL_DEPENDENCY") as raised:
                lifecycle.independence_preflight(repo)
            self.assertIn("discovered-name", str(raised.exception))

    def test_own_skill_reference_is_allowed_and_exact_payload_runs(self):
        with tempfile.TemporaryDirectory() as raw:
            root = Path(raw)
            repo = init_repo(root / "repo")
            skill = repo / "skills" / "sample" / "SKILL.md"
            skill.write_text(skill.read_text(encoding="utf-8") + "\nUse $sample-skill.\n", encoding="utf-8")
            with self.fake_codex(root):
                report = lifecycle.independence_preflight(repo)
            self.assertTrue(report["independent"])
            self.assertEqual(report["packaged_skills"], ["sample-skill"])
            self.assertEqual(report["references"], [])
            self.assertEqual(report["standalone"]["checks_passed"], 1)
            self.assertEqual(report["standalone"]["installed_plugin"], "sample-plugin@ariadne-standalone")

    def test_standalone_check_failure_blocks_independence(self):
        with tempfile.TemporaryDirectory() as raw:
            root = Path(raw)
            repo = init_repo(root / "repo")
            config_path = repo / "lifecycle.json"
            config = lifecycle.read_json(config_path)
            config["independence"]["standalone_checks"] = [
                ["python3", "-c", "raise SystemExit(7)"]
            ]
            config_path.write_text(json.dumps(config), encoding="utf-8")
            with self.fake_codex(root):
                with self.assertRaisesRegex(lifecycle.LifecycleError, "E_STANDALONE_CHECK"):
                    lifecycle.independence_preflight(repo)

    def test_shell_string_standalone_check_is_rejected(self):
        with tempfile.TemporaryDirectory() as raw:
            repo = init_repo(Path(raw) / "repo")
            config_path = repo / "lifecycle.json"
            config = lifecycle.read_json(config_path)
            config["independence"]["standalone_checks"] = ["python3 --version"]
            config_path.write_text(json.dumps(config), encoding="utf-8")
            with self.assertRaisesRegex(lifecycle.LifecycleError, "E_INDEPENDENCE_CONFIG"):
                lifecycle.independence_preflight(repo)

    def test_extra_enabled_plugin_blocks_isolated_install(self):
        with tempfile.TemporaryDirectory() as raw:
            root = Path(raw)
            repo = init_repo(root / "repo")
            with self.fake_codex(root, extra_plugin=True):
                with self.assertRaisesRegex(lifecycle.LifecycleError, "E_STANDALONE_IDENTITY"):
                    lifecycle.independence_preflight(repo)

    def test_install_path_outside_isolated_codex_home_is_rejected(self):
        with tempfile.TemporaryDirectory() as raw:
            root = Path(raw)
            repo = init_repo(root / "repo")
            with self.fake_codex(root, outside_path=True):
                with self.assertRaisesRegex(lifecycle.LifecycleError, "E_STANDALONE_IDENTITY"):
                    lifecycle.independence_preflight(repo)

    def test_standalone_environment_does_not_inherit_ambient_variables(self):
        with tempfile.TemporaryDirectory() as raw:
            root = Path(raw)
            repo = init_repo(root / "repo")
            config_path = repo / "lifecycle.json"
            config = lifecycle.read_json(config_path)
            ambient_only = root / "ambient-only-bin"
            config["independence"]["standalone_checks"] = [
                [
                    "python3",
                    "-c",
                    (
                        "import os; "
                        "assert 'ARIADNE_AMBIENT_SECRET' not in os.environ; "
                        f"assert {str(ambient_only)!r} not in os.environ['PATH'].split(os.pathsep)"
                    ),
                ]
            ]
            config_path.write_text(json.dumps(config), encoding="utf-8")
            with self.fake_codex(root):
                ambient_path = f"{ambient_only}{os.pathsep}{os.environ['PATH']}"
                with mock.patch.dict(
                    os.environ,
                    {
                        "ARIADNE_AMBIENT_SECRET": "must-not-cross-boundary",
                        "PATH": ambient_path,
                    },
                ):
                    report = lifecycle.independence_preflight(repo)
            self.assertTrue(report["independent"])


if __name__ == "__main__":
    unittest.main()
