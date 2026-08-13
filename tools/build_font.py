#!/usr/bin/env python3
"""Rebuild WettstaiFont.otf from the untouched original, repairing everything
that stops it from working in MuseScore Studio.

What this does (and only this - no outline is ever modified):

1. Drops the ten placeholder rectangles that squat on real SMuFL codepoints
   (uniE000-uniE002, gClef, cClef, fClef, timeSig0-2, noteheadBlack). MuseScore
   only falls back to Bravura for glyphs a font does *not* have, so these boxes
   were being drawn instead of clefs, time signatures and noteheads.
2. Drops the six copies of the "Wert" marks that were mapped onto the SMuFL flag
   slots U+E240-U+E245, which replaced every flag in the score with a dotted
   vertical line.
3. Adds an alias mapping for all 60 Wettstai symbols into U+E770-U+E7AB so
   MuseScore can actually show and insert them (see wettstai_glyphs.py).
4. Repairs the advance widths, which were between 45 and 833 units while the ink
   ran up to 4199 units wide.
5. Repairs the vertical metrics (hhea / OS/2 / head) that claimed an ascent of
   2181 units and a typographic descender of 0 for glyphs reaching -297.

Usage: python3 tools/build_font.py [-o package/WettstaiFont.otf]
"""

from __future__ import annotations

import argparse
import hashlib
import sys
from pathlib import Path

from fontTools import subset
from fontTools.pens.boundsPen import BoundsPen
from fontTools.pens.recordingPen import RecordingPen
from fontTools.ttLib import TTFont

sys.path.insert(0, str(Path(__file__).resolve().parent))
from wettstai_glyphs import (  # noqa: E402
    FLAG_OVERRIDE_GLYPHS,
    FONT_NAME,
    FONT_VERSION,
    PLACEHOLDER_GLYPHS,
    RIGHT_SIDEBEARING,
    UNITS_PER_EM,
    WETTSTAI_GLYPHS,
    alias_codepoint,
)

HERE = Path(__file__).resolve().parent
REPO = HERE.parent
DEFAULT_SRC = HERE / "WettstaiFont-original.otf"
DEFAULT_OUT = REPO / "package" / "WettstaiFont.otf"


def outline_signature(font: TTFont, glyph_name: str) -> str:
    pen = RecordingPen()
    font.getGlyphSet()[glyph_name].draw(pen)
    return hashlib.sha256(repr(pen.value).encode()).hexdigest()


def glyph_bounds(font: TTFont, glyph_name: str):
    pen = BoundsPen(font.getGlyphSet())
    font.getGlyphSet()[glyph_name].draw(pen)
    return pen.bounds


def build(src: Path, out: Path) -> None:
    original = TTFont(str(src))
    keep = [name for _cp, name, _desc in WETTSTAI_GLYPHS]

    missing = [n for n in keep if n not in original.getGlyphOrder()]
    if missing:
        raise SystemExit(f"source font is missing expected glyphs: {missing}")

    # Record the outlines we intend to keep so we can prove they survive untouched.
    before = {name: outline_signature(original, name) for name in keep}
    original.close()

    font = TTFont(str(src))

    dropped = PLACEHOLDER_GLYPHS + FLAG_OVERRIDE_GLYPHS
    present = set(font.getGlyphOrder())
    for name in dropped:
        if name not in present:
            print(f"  note: '{name}' not present in source, nothing to drop")

    options = subset.Options()
    options.glyph_names = True
    options.notdef_glyph = True
    options.notdef_outline = True
    options.recalc_bounds = True
    options.recalc_timestamp = False
    options.drop_tables = []
    options.name_IDs = ["*"]
    options.name_legacy = True
    options.name_languages = ["*"]
    options.layout_features = ["*"]
    options.hinting = True
    options.legacy_kern = True

    subsetter = subset.Subsetter(options=options)
    subsetter.populate(glyphs=keep)
    subsetter.subset(font)

    remaining = set(font.getGlyphOrder())
    still_there = [n for n in dropped if n in remaining]
    if still_there:
        raise SystemExit(f"placeholder glyphs survived subsetting: {still_there}")

    # --- cmap: SMuFL optional codepoints + MuseScore-visible aliases ----------
    new_cmap = {}
    for index, (cp, name, _desc) in enumerate(WETTSTAI_GLYPHS):
        new_cmap[cp] = name
        new_cmap[alias_codepoint(index)] = name

    for table in font["cmap"].tables:
        if table.platformID == 1:
            # Legacy Mac roman subtable: nothing in this font is Mac-roman
            # encodable, so leave it empty rather than emitting bogus entries.
            table.cmap = {}
        else:
            table.cmap = dict(new_cmap)
    font["cmap"].tables = [t for t in font["cmap"].tables if t.platformID != 1]

    # --- hmtx: advance width must cover the ink ------------------------------
    hmtx = font["hmtx"]
    for _cp, name, _desc in WETTSTAI_GLYPHS:
        bounds = glyph_bounds(font, name)
        _adv, lsb = hmtx[name]
        if bounds is None:
            continue
        x_min, _y_min, x_max, _y_max = bounds
        advance = int(round(x_max)) + RIGHT_SIDEBEARING
        hmtx[name] = (max(advance, 0), int(round(x_min)))

    # --- global vertical metrics --------------------------------------------
    all_bounds = [glyph_bounds(font, n) for n in font.getGlyphOrder()]
    all_bounds = [b for b in all_bounds if b is not None]
    x_min = int(min(b[0] for b in all_bounds))
    y_min = int(min(b[1] for b in all_bounds))
    x_max = int(max(b[2] for b in all_bounds))
    y_max = int(max(b[3] for b in all_bounds))

    # Leave a little headroom so GDI/Qt never clip a glyph that touches the
    # extreme, and keep at least a conventional em of ascent.
    ascent = max(y_max + 25, UNITS_PER_EM)
    descent = min(y_min - 25, -250)

    head = font["head"]
    head.unitsPerEm = UNITS_PER_EM
    head.xMin, head.yMin, head.xMax, head.yMax = x_min, y_min, x_max, y_max
    head.fontRevision = float(FONT_VERSION.rsplit(".", 1)[0])

    hhea = font["hhea"]
    hhea.ascent = ascent
    hhea.descent = descent
    hhea.lineGap = 0

    os2 = font["OS/2"]
    os2.sTypoAscender = UNITS_PER_EM
    os2.sTypoDescender = descent
    os2.sTypoLineGap = 0
    os2.usWinAscent = ascent
    os2.usWinDescent = abs(descent)
    os2.usFirstCharIndex = min(new_cmap)
    os2.usLastCharIndex = max(new_cmap)
    # Unicode range bit 60 = Private Use Area (U+E000-U+F8FF); nothing else.
    os2.ulUnicodeRange1 = 0
    os2.ulUnicodeRange2 = 1 << (60 - 32)
    os2.ulUnicodeRange3 = 0
    os2.ulUnicodeRange4 = 0
    os2.fsType = 0

    # --- names ---------------------------------------------------------------
    major, minor, _patch = FONT_VERSION.split(".")
    name_table = font["name"]
    for name_id, value in (
        (3, f"{FONT_NAME} {major}.{minor}"),
        (5, f"Version {major}.{minor.zfill(3)}"),
    ):
        for record in name_table.names:
            if record.nameID == name_id:
                record.string = value.encode("utf-16-be") if record.platformID == 3 else value.encode("latin-1")

    out.parent.mkdir(parents=True, exist_ok=True)
    font.save(str(out))
    font.close()

    # --- verification --------------------------------------------------------
    rebuilt = TTFont(str(out))
    after = {name: outline_signature(rebuilt, name) for name in keep}
    changed = [n for n in keep if before[n] != after[n]]
    if changed:
        raise SystemExit(f"outlines changed during rebuild (must never happen): {changed}")

    cmap = rebuilt.getBestCmap()
    for index, (cp, name, _desc) in enumerate(WETTSTAI_GLYPHS):
        assert cmap.get(cp) == name, f"U+{cp:04X} -> {cmap.get(cp)}, expected {name}"
        alias = alias_codepoint(index)
        assert cmap.get(alias) == name, f"U+{alias:04X} -> {cmap.get(alias)}, expected {name}"
    for cp in list(range(0xE000, 0xE003)) + [0xE050, 0xE05C, 0xE062, 0xE080, 0xE081, 0xE082, 0xE0A4] \
            + list(range(0xE240, 0xE246)):
        assert cp not in cmap, f"U+{cp:04X} is still mapped ({cmap[cp]})"

    print(f"  outlines preserved : {len(keep)}/{len(keep)}")
    print(f"  glyphs in font     : {rebuilt['maxp'].numGlyphs}")
    print(f"  cmap entries       : {len(cmap)} (60 optional + 60 alias)")
    print(f"  bbox               : {x_min} {y_min} {x_max} {y_max}")
    print(f"  ascent/descent     : {ascent} / {descent}")
    print(f"  file size          : {out.stat().st_size} bytes")
    rebuilt.close()


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("-i", "--input", type=Path, default=DEFAULT_SRC)
    parser.add_argument("-o", "--output", type=Path, default=DEFAULT_OUT)
    args = parser.parse_args()

    print(f"Building {args.output.name} from {args.input.name}")
    build(args.input, args.output)
    print("OK")


if __name__ == "__main__":
    main()
