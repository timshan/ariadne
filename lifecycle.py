#!/usr/bin/env python3
"""Repository entry point for the packaged Ariadne lifecycle controller."""

from __future__ import annotations

from pathlib import Path


CONTROLLER = Path(__file__).resolve().parent / "plugins" / "ariadne" / "lifecycle.py"
SOURCE = CONTROLLER.read_bytes()
exec(compile(SOURCE, str(CONTROLLER), "exec"), globals(), globals())
