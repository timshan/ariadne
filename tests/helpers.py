import json
import os
import subprocess
from pathlib import Path


def run(*args, cwd):
    return subprocess.run(args, cwd=cwd, check=True, text=True, capture_output=True)


def init_repo(path: Path, version: str = "1.0.0") -> Path:
    path.mkdir()
    run("git", "init", "-b", "main", cwd=path)
    run("git", "config", "user.email", "tests@example.invalid", cwd=path)
    run("git", "config", "user.name", "Lifecycle Tests", cwd=path)
    (path / ".codex-plugin").mkdir()
    (path / ".codex-plugin" / "plugin.json").write_text(
        json.dumps(
            {
                "name": "sample-plugin",
                "version": version,
                "description": "A sample plugin used by lifecycle tests.",
                "author": {"name": "Tests"},
                "skills": "./skills/",
                "interface": {
                    "displayName": "Sample Plugin",
                    "shortDescription": "Lifecycle test fixture",
                },
            }
        ),
        encoding="utf-8",
    )
    skill = path / "skills" / "sample"
    skill.mkdir(parents=True)
    (skill / "SKILL.md").write_text(
        "---\nname: sample-skill\ndescription: Test fixture.\n---\n\n# Sample\n",
        encoding="utf-8",
    )
    (path / "lifecycle.json").write_text(
        json.dumps(
            {
                "plugin_path": ".",
                "checks": [],
                "independence": {
                    "standalone_checks": [
                        [
                            "python3",
                            "-c",
                            "from pathlib import Path; assert Path('skills/sample/SKILL.md').is_file()",
                        ]
                    ]
                },
            }
        ),
        encoding="utf-8",
    )
    run("git", "add", ".", cwd=path)
    run("git", "commit", "-m", "initial", cwd=path)
    run("git", "switch", "-c", "develop", cwd=path)
    return path


def channel_env(channel: Path):
    previous = os.environ.get("SKILL_LIFECYCLE_CHANNEL")
    os.environ["SKILL_LIFECYCLE_CHANNEL"] = str(channel)
    return previous


def restore_channel_env(previous):
    if previous is None:
        os.environ.pop("SKILL_LIFECYCLE_CHANNEL", None)
    else:
        os.environ["SKILL_LIFECYCLE_CHANNEL"] = previous
