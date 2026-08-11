import json
import os
import tempfile
import unittest
from pathlib import Path
from unittest import mock

import lifecycle
from helpers import init_repo


class ActivationTests(unittest.TestCase):
    def test_activation_uses_json_preflight_and_installs_once(self):
        with tempfile.TemporaryDirectory() as raw:
            root = Path(raw)
            binary = root / "bin"
            binary.mkdir()
            log = root / "codex.log"
            fake = binary / "codex"
            fake.write_text(
                """#!/usr/bin/env python3
import json, os, sys
args = sys.argv[1:]
with open(os.environ['FAKE_CODEX_LOG'], 'a', encoding='utf-8') as handle:
    handle.write(json.dumps(args) + '\\n')
if args == ['plugin', 'marketplace', 'list', '--json']:
    print(json.dumps({'marketplaces': []}))
elif args == ['plugin', 'list', '--json']:
    print(json.dumps({'installed': [], 'available': []}))
else:
    print(json.dumps({'ok': True}))
""",
                encoding="utf-8",
            )
            fake.chmod(0o755)
            environment = {
                "PATH": f"{binary}{os.pathsep}{os.environ['PATH']}",
                "FAKE_CODEX_LOG": str(log),
            }
            with mock.patch.dict(os.environ, environment):
                lifecycle._activate(root / "channel", "sample-plugin", "1.0.0")
            commands = [json.loads(line) for line in log.read_text(encoding="utf-8").splitlines()]
            self.assertIn(["plugin", "marketplace", "add", str(root / "channel")], commands)
            self.assertIn(["plugin", "add", "sample-plugin@skill-formal", "--json"], commands)

    def test_repeated_promotion_retries_failed_activation_without_rewriting_formal_state(self):
        with tempfile.TemporaryDirectory() as raw:
            root = Path(raw)
            repo = init_repo(root / "repo")
            channel = root / "channel"

            with mock.patch.object(
                lifecycle,
                "_activate",
                side_effect=lifecycle.LifecycleError("E_CODEX_INSTALL: simulated failure"),
            ):
                with self.assertRaisesRegex(lifecycle.LifecycleError, "E_CODEX_INSTALL"):
                    lifecycle.promote(
                        repo,
                        "1.0.0",
                        channel=channel,
                        apply=True,
                        activate=True,
                    )

            lock_before = (channel / "formal-lock.json").read_bytes()
            artifact = channel / "versions" / "sample-plugin" / "1.0.0" / "sample-plugin-1.0.0.zip"
            artifact_before = artifact.read_bytes()
            main_before = lifecycle.git_output(repo, "rev-parse", "main")
            tag_before = lifecycle.git_output(repo, "rev-parse", "formal/v1.0.0")

            with mock.patch.object(lifecycle, "_activate") as activate:
                result = lifecycle.promote(
                    repo,
                    "1.0.0",
                    channel=channel,
                    apply=True,
                    activate=True,
                )

            self.assertEqual(result["action"], "idempotent")
            activate.assert_called_once_with(channel.resolve(), "sample-plugin", "1.0.0")
            self.assertEqual(lock_before, (channel / "formal-lock.json").read_bytes())
            self.assertEqual(artifact_before, artifact.read_bytes())
            self.assertEqual(main_before, lifecycle.git_output(repo, "rev-parse", "main"))
            self.assertEqual(tag_before, lifecycle.git_output(repo, "rev-parse", "formal/v1.0.0"))

    def test_repeated_promotion_without_activation_does_not_activate(self):
        with tempfile.TemporaryDirectory() as raw:
            root = Path(raw)
            repo = init_repo(root / "repo")
            channel = root / "channel"
            lifecycle.promote(repo, "1.0.0", channel=channel, apply=True)

            with mock.patch.object(lifecycle, "_activate") as activate:
                result = lifecycle.promote(repo, "1.0.0", channel=channel, apply=True)

            self.assertEqual(result["action"], "idempotent")
            activate.assert_not_called()


if __name__ == "__main__":
    unittest.main()
