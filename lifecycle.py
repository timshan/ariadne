#!/usr/bin/env python3
"""Repository entry point for the packaged Ariadne lifecycle controller."""

from __future__ import annotations

import importlib.util
import sys
from pathlib import Path


CONTROLLER = Path(__file__).resolve().parent / "plugins" / "ariadne" / "lifecycle.py"
SPEC = importlib.util.spec_from_file_location("_ariadne_lifecycle", CONTROLLER)
if SPEC is None or SPEC.loader is None:
    raise RuntimeError(f"cannot load Ariadne controller: {CONTROLLER}")
MODULE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(MODULE)

if __name__ == "__main__":
    raise SystemExit(MODULE.main())

# Make repository imports and mocks target the packaged controller itself.
sys.modules[__name__] = MODULE
