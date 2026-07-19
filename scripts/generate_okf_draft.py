#!/usr/bin/env python3
"""Print a deterministic OKF catalog candidate for human review."""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.okf.generator import build_catalog_draft


if __name__ == "__main__":
    print(build_catalog_draft(), end="")
