#!/usr/bin/env python3
"""Generate the SMuFL metadata files for WettstaiFont from the built OTF.

The metadata shipped with the original package was not usable:

* ``glyphBBoxes`` used a flat ``[a, b, c, d]`` array instead of the SMuFL
  ``{"bBoxNE": [...], "bBoxSW": [...]}`` shape, the numbers were in font design
  units instead of staff spaces, and for several glyphs the x and y values had
  been transposed (``ruf21Rechts`` was listed as 0.8 units wide and 4007 tall,
  the real glyph is 4199 wide and 397 tall).
* ``glyphAdvanceWidths`` was in font units too.
* It carried ``glyphs``, ``glyphClasses`` and ``ranges`` keys, none of which
  exist in the SMuFL metadata format.
* ``glyphnames.json`` wrote codepoints as ``"F400"`` instead of ``"U+F400"``,
  so every consumer that strips the ``U+`` prefix read the wrong value.

Everything here is derived from the actual font file, so the numbers cannot
drift away from the outlines again.

Usage: python3 tools/build_metadata.py
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from fontTools.pens.boundsPen import BoundsPen
from fontTools.ttLib import TTFont

sys.path.insert(0, str(Path(__file__).resolve().parent))
from wettstai_glyphs import (  # noqa: E402
    ALIAS_SMUFL_NAMES,
    FONT_NAME,
    FONT_VERSION,
    STAFF_SPACE,
    WETTSTAI_GLYPHS,
    alias_codepoint,
)

HERE = Path(__file__).resolve().parent
REPO = HERE.parent
DEFAULT_FONT = REPO / "package" / "WettstaiFont.otf"

# Bravura's engraving defaults. WettstaiFont deliberately contains no standard
# notation glyphs, so MuseScore draws staves, stems, beams and barlines with its
# fallback font (Bravura); using Bravura's line weights keeps them consistent.
ENGRAVING_DEFAULTS = {
    "arrowShaftThickness": 0.16,
    "barlineSeparation": 0.4,
    "beamSpacing": 0.25,
    "beamThickness": 0.5,
    "bracketThickness": 0.5,
    "dashedBarlineDashLength": 0.5,
    "dashedBarlineGapLength": 0.25,
    "dashedBarlineThickness": 0.16,
    "hBarThickness": 1.0,
    "hairpinThickness": 0.16,
    "legerLineExtension": 0.4,
    "legerLineThickness": 0.16,
    "lyricLineThickness": 0.16,
    "octaveLineThickness": 0.16,
    "pedalLineThickness": 0.16,
    "repeatBarlineDotSeparation": 0.16,
    "repeatEndingLineThickness": 0.16,
    "slurEndpointThickness": 0.1,
    "slurMidpointThickness": 0.22,
    "staffLineThickness": 0.13,
    "stemThickness": 0.12,
    "subBracketThickness": 0.16,
    "textEnclosureThickness": 0.16,
    "textFontFamily": ["Edwin", "Academico", "Century Schoolbook", "serif"],
    "thickBarlineThickness": 0.5,
    "thinBarlineThickness": 0.16,
    "thinThickBarlineSeparation": 0.4,
    "tieEndpointThickness": 0.1,
    "tieMidpointThickness": 0.22,
    "tupletBracketThickness": 0.16,
}


def sp(units: float) -> float:
    """Font design units -> staff spaces, as SMuFL metadata requires."""
    return round(units / STAFF_SPACE, 4)


def collect(font: TTFont):
    glyph_set = font.getGlyphSet()
    hmtx = font["hmtx"]
    advances, bboxes = {}, {}

    for index, (_cp, name, _desc) in enumerate(WETTSTAI_GLYPHS):
        pen = BoundsPen(glyph_set)
        glyph_set[name].draw(pen)
        bounds = pen.bounds or (0, 0, 0, 0)
        advance = hmtx[name][0]

        entry_bbox = {
            "bBoxNE": [sp(bounds[2]), sp(bounds[3])],
            "bBoxSW": [sp(bounds[0]), sp(bounds[1])],
        }
        # Every glyph is reachable under two names: the Wettstai optional-glyph
        # name (U+F4xx) and the SMuFL name of its MuseScore alias slot.
        for key in (name, ALIAS_SMUFL_NAMES[index]):
            advances[key] = sp(advance)
            bboxes[key] = dict(entry_bbox)

    return advances, bboxes


def build(font_path: Path) -> None:
    font = TTFont(str(font_path))
    advances, bboxes = collect(font)
    font.close()

    metadata = {
        "fontName": FONT_NAME,
        "fontVersion": float(".".join(FONT_VERSION.split(".")[:2])),
        "engravingDefaults": ENGRAVING_DEFAULTS,
        "glyphAdvanceWidths": advances,
        "glyphBBoxes": bboxes,
        "glyphsWithAnchors": {},
        "glyphsWithAlternates": {},
        "ligatures": {},
        "sets": {},
        "optionalGlyphs": {
            name: {
                "codepoint": f"U+{cp:04X}",
                "description": desc,
                "classes": ["wettstai"],
            }
            for cp, name, desc in WETTSTAI_GLYPHS
        },
    }

    glyphnames = {
        name: {
            "codepoint": f"U+{cp:04X}",
            "alternateCodepoint": f"U+{alias_codepoint(index):04X}",
            "description": desc,
        }
        for index, (cp, name, desc) in enumerate(WETTSTAI_GLYPHS)
    }

    out_dir = font_path.parent
    (out_dir / f"{FONT_NAME}.json").write_text(
        json.dumps(metadata, indent=2, ensure_ascii=False) + "\n", encoding="utf-8"
    )
    (out_dir / "glyphnames.json").write_text(
        json.dumps(glyphnames, indent=2, ensure_ascii=False) + "\n", encoding="utf-8"
    )

    write_symbol_table(out_dir / "Symbolliste.md")

    print(f"  {FONT_NAME}.json : {len(advances)} advance widths, {len(bboxes)} bboxes,"
          f" {len(metadata['optionalGlyphs'])} optional glyphs")
    print(f"  glyphnames.json  : {len(glyphnames)} entries")
    print(f"  Symbolliste.md   : {len(WETTSTAI_GLYPHS)} rows")


def write_symbol_table(path: Path) -> None:
    """Markdown table of all symbols, generated so it cannot drift from the font."""
    lines = [
        "# WettstaiFont - Symbolliste",
        "",
        "Alle 60 Wettstai-Symbole. Die Spalte **MuseScore** ist der Codepoint, unter",
        "dem MuseScore das Symbol kennt; der Name daneben ist die Beschriftung, die",
        "in der Master-Palette unter *Symbole -> Beaters pictograms* erscheint.",
        "Die Spalte **SMuFL** ist der offizielle Codepoint im SMuFL-Optional-Bereich,",
        "den Programme wie Dorico oder Finale benutzen.",
        "",
        "| # | Symbol | Glyphenname | MuseScore | Beschriftung in der Palette | SMuFL |",
        "|---|--------|-------------|-----------|------------------------------|-------|",
    ]
    for index, (cp, name, desc) in enumerate(WETTSTAI_GLYPHS, start=0):
        lines.append(
            f"| {index + 1} | {desc} | `{name}` | `U+{alias_codepoint(index):04X}` "
            f"| {ALIAS_SMUFL_NAMES[index]} | `U+{cp:04X}` |"
        )
    lines.append("")
    path.write_text("\n".join(lines), encoding="utf-8")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("-f", "--font", type=Path, default=DEFAULT_FONT)
    args = parser.parse_args()
    print(f"Generating SMuFL metadata from {args.font.name}")
    build(args.font)
    print("OK")


if __name__ == "__main__":
    main()
