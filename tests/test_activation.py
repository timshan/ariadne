import json
import os
import tempfile
import unittest
from pathlib import Path
from unittest import mock

import lifecycle


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


if __name__ == "__main__":
    unittest.main()
