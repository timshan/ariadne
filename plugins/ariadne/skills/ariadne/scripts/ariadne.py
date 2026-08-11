#!/usr/bin/env python3
"""Launch the bundled Ariadne lifecycle controller from any directory."""

from __future__ import annotations

import os
import sys
from pathlib import Path


CONTROLLER = Path(__file__).resolve().parents[3] / "lifecycle.py"


def main() -> None:
    if not CONTROLLER.is_file():
        raise SystemExit(f"E_CONTROLLER_MISSING: {CONTROLLER}")
    os.execv(sys.executable, [sys.executable, str(CONTROLLER), *sys.argv[1:]])


if __name__ == "__main__":
    main()
