#!/usr/bin/env python3
"""Build the whole distributable: font, metadata, docs, preview images, ZIP.

    python3 tools/build_package.py [--bravura /path/to/Bravura.otf]

Bravura is only used to render the before/after preview; leave it out and the
preview step is skipped.
"""

from __future__ import annotations

import argparse
import subprocess
import sys
import zipfile
from pathlib import Path

HERE = Path(__file__).resolve().parent
REPO = HERE.parent
PACKAGE = REPO / "package"
ZIP_PATH = REPO / "WettstaiFont-MuseScore4-Setup.zip"
ZIP_ROOT = "WettstaiFont-MuseScore4-Setup"

# Everything that goes into the ZIP, in the order a user would meet it.
CONTENTS = [
    "LIESMICH.md",
    "Install-WettstaiFont.ps1",
    "Uninstall-WettstaiFont.ps1",
    "WettstaiFont.otf",
    "WettstaiFont.json",
    "glyphnames.json",
    "Symbolliste.md",
]


def run(script: str, *args: str) -> None:
    print(f"\n$ python3 tools/{script} {' '.join(args)}".rstrip())
    result = subprocess.run([sys.executable, str(HERE / script), *args], cwd=REPO)
    if result.returncode != 0:
        raise SystemExit(f"tools/{script} failed with exit code {result.returncode}")


def build_zip() -> None:
    missing = [name for name in CONTENTS if not (PACKAGE / name).is_file()]
    if missing:
        raise SystemExit(f"missing package files: {missing}")

    # Deterministic archive: fixed timestamps so rebuilding without changes
    # produces an identical file instead of a noisy diff.
    with zipfile.ZipFile(ZIP_PATH, "w", zipfile.ZIP_DEFLATED) as archive:
        for name in CONTENTS:
            payload = (PACKAGE / name).read_bytes()
            # The package is for Windows; ship the text files with CRLF so they
            # read correctly in Notepad and the ISE.
            if name.endswith((".ps1", ".md")):
                payload = payload.replace(b"\r\n", b"\n").replace(b"\n", b"\r\n")
            info = zipfile.ZipInfo(f"{ZIP_ROOT}/{name}", date_time=(2026, 1, 1, 0, 0, 0))
            info.compress_type = zipfile.ZIP_DEFLATED
            info.external_attr = 0o644 << 16
            archive.writestr(info, payload)

    size = ZIP_PATH.stat().st_size
    print(f"\n  {ZIP_PATH.name}: {len(CONTENTS)} files, {size} bytes")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--bravura", type=Path, default=None)
    args = parser.parse_args()

    run("build_font.py")
    run("build_metadata.py")
    if args.bravura:
        run("render_preview.py", "--bravura", str(args.bravura))
    else:
        print("\n(no --bravura given, skipping preview rendering)")
    run("verify_musescore.py")
    build_zip()
    print("\nDone.")


if __name__ == "__main__":
    main()
