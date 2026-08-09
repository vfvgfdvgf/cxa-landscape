#!/usr/bin/env python3
"""Install the owner-supplied Thmanyah WOFF2 files into the project.

Usage:
    python scripts/install_thmanyah_fonts.py "Thmanyah-Font-Family.zip"
"""
from __future__ import annotations

import shutil
import sys
import tempfile
import zipfile
from pathlib import Path

EXPECTED = {
    "thmanyahsans-Light.woff2",
    "thmanyahsans-Regular.woff2",
    "thmanyahsans-Medium.woff2",
    "thmanyahsans-Bold.woff2",
    "thmanyahsans-Black.woff2",
    "thmanyahserifdisplay-Regular.woff2",
    "thmanyahserifdisplay-Bold.woff2",
    "thmanyahserifdisplay-Black.woff2",
    "thmanyahseriftext-Regular.woff2",
    "thmanyahseriftext-Bold.woff2",
}


def main() -> int:
    if len(sys.argv) != 2:
        print("Usage: python scripts/install_thmanyah_fonts.py path/to/Thmanyah-Font-Family.zip")
        return 2
    archive = Path(sys.argv[1]).expanduser().resolve()
    if not archive.is_file():
        print(f"Font archive not found: {archive}")
        return 2
    target = Path(__file__).resolve().parents[1] / "static" / "fonts" / "thmanyah"
    target.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory() as temp_dir:
        temp = Path(temp_dir)
        with zipfile.ZipFile(archive) as zipped:
            zipped.extractall(temp)
        found = {path.name: path for path in temp.rglob("*.woff2") if "__MACOSX" not in path.parts}
        missing = sorted(EXPECTED - found.keys())
        if missing:
            print("Missing expected font files:")
            print("\n".join(f"- {name}" for name in missing))
            return 1
        for name in sorted(EXPECTED):
            shutil.copy2(found[name], target / name)
    print(f"Installed {len(EXPECTED)} Thmanyah font files into {target}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
