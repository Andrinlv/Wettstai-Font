#!/usr/bin/env python3
"""Render what MuseScore Studio draws, before and after the repair.

This is a simulation, not a screenshot: it applies MuseScore's own glyph
resolution rule (``EngravingFont::useFallbackFont()`` - use the selected music
font when it has the codepoint, otherwise Bravura) to the original font and to
the rebuilt one, and draws the result.

Bravura is only needed to stand in for MuseScore's fallback font. Point
``--bravura`` at any copy of Bravura.otf (MuseScore ships one in
``fonts/bravura/Bravura.otf``); without it the standard notation glyphs are
drawn as light grey outlines instead.

Usage:
    python3 tools/render_preview.py --bravura /path/to/Bravura.otf
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from fontTools.pens.boundsPen import BoundsPen
from fontTools.pens.svgPathPen import SVGPathPen
from fontTools.ttLib import TTFont

sys.path.insert(0, str(Path(__file__).resolve().parent))
from wettstai_glyphs import WETTSTAI_GLYPHS, alias_codepoint  # noqa: E402

HERE = Path(__file__).resolve().parent
REPO = HERE.parent

SPATIUM = 26.0          # pixels per staff space
STAFF_LINE = 0.13       # staff spaces, Bravura engraving default
STEM_WIDTH = 0.12

# SMuFL codepoints used by the mock score.
GCLEF, TIMESIG2, TIMESIG4 = 0xE050, 0xE082, 0xE084
NOTEHEAD_BLACK, FLAG8TH_UP, BARLINE = 0xE0A4, 0xE240, 0xE030


class GlyphSource:
    """Resolve a codepoint the way MuseScore does: music font first, then Bravura."""

    def __init__(self, music_font: Path, fallback: Path | None):
        self.music = TTFont(str(music_font))
        self.music_cmap = self.music.getBestCmap()
        self.music_upem = self.music["head"].unitsPerEm
        self.fallback = TTFont(str(fallback)) if fallback else None
        self.fallback_cmap = self.fallback.getBestCmap() if self.fallback else {}
        self.fallback_upem = self.fallback["head"].unitsPerEm if self.fallback else 1000

    def resolve(self, codepoint: int):
        """Return (svg_path_d, units_per_em, bounds, from_music_font) or None."""
        if codepoint in self.music_cmap:
            font, cmap, upem, own = self.music, self.music_cmap, self.music_upem, True
        elif codepoint in self.fallback_cmap:
            font, cmap, upem, own = self.fallback, self.fallback_cmap, self.fallback_upem, False
        else:
            return None
        name = cmap[codepoint]
        glyph_set = font.getGlyphSet()
        pen = SVGPathPen(glyph_set)
        glyph_set[name].draw(pen)
        bounds_pen = BoundsPen(glyph_set)
        glyph_set[name].draw(bounds_pen)
        return pen.getCommands(), upem, bounds_pen.bounds, own


class Canvas:
    def __init__(self, width: float, height: float):
        self.width, self.height = width, height
        self.parts: list[str] = []

    def glyph(self, source: GlyphSource, codepoint: int, x: float, y: float,
              scale_sp: float = 1.0, colour: str | None = None):
        """Place a glyph with its SMuFL origin at (x, y). Returns advance-ish width."""
        resolved = source.resolve(codepoint)
        if resolved is None:
            return 0.0
        commands, upem, bounds, own = resolved
        unit = SPATIUM * 4.0 / upem * scale_sp   # SMuFL: 1 em = 4 staff spaces
        fill = colour or ("#1a1a1a" if not own else "#1a1a1a")
        if commands:
            self.parts.append(
                f'<g transform="translate({x:.2f},{y:.2f}) scale({unit:.5f},{-unit:.5f})">'
                f'<path d="{commands}" fill="{fill}"/></g>'
            )
        return (bounds[2] if bounds else 0) * unit

    def line(self, x1, y1, x2, y2, width, colour="#1a1a1a"):
        self.parts.append(
            f'<line x1="{x1:.2f}" y1="{y1:.2f}" x2="{x2:.2f}" y2="{y2:.2f}" '
            f'stroke="{colour}" stroke-width="{width:.2f}" stroke-linecap="butt"/>'
        )

    def text(self, x, y, content, size=13, colour="#555", weight="normal", anchor="start"):
        safe = content.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
        self.parts.append(
            f'<text x="{x:.2f}" y="{y:.2f}" font-family="DejaVu Sans, Helvetica, sans-serif" '
            f'font-size="{size}" font-weight="{weight}" fill="{colour}" '
            f'text-anchor="{anchor}">{safe}</text>'
        )

    def rect(self, x, y, w, h, fill="none", stroke="none", width=1.0):
        self.parts.append(
            f'<rect x="{x:.2f}" y="{y:.2f}" width="{w:.2f}" height="{h:.2f}" '
            f'fill="{fill}" stroke="{stroke}" stroke-width="{width}"/>'
        )

    def to_svg(self) -> str:
        return (
            f'<svg xmlns="http://www.w3.org/2000/svg" width="{self.width:.0f}" '
            f'height="{self.height:.0f}" viewBox="0 0 {self.width:.0f} {self.height:.0f}">'
            f'<rect width="100%" height="100%" fill="#ffffff"/>'
            + "".join(self.parts) + "</svg>"
        )


def draw_mock_score(canvas: Canvas, source: GlyphSource, top: float, label: str,
                    caption: str, wettstai_codepoints: list[int] | None):
    """One system: clef, 2/4, four eighth notes, optional Wettstai marks above."""
    left, right = 42.0, canvas.width - 42.0
    middle = top + 2 * SPATIUM          # y of the middle staff line

    canvas.text(left, top - 154, label, size=16, weight="bold", colour="#111")
    canvas.text(left, top - 134, caption, size=12, colour="#666")

    for i in range(5):
        y = top + i * SPATIUM
        canvas.line(left, y, right, y, STAFF_LINE * SPATIUM)

    x = left + 14
    # Treble clef: SMuFL origin sits on the G line = 2nd line from the bottom.
    canvas.glyph(source, GCLEF, x, top + 3 * SPATIUM)
    x += 3.2 * SPATIUM

    # 2/4: numerator centred one staff space above the middle line, denominator below.
    canvas.glyph(source, TIMESIG2, x, middle - SPATIUM)
    canvas.glyph(source, TIMESIG4, x, middle + SPATIUM)
    x += 2.4 * SPATIUM

    # Four eighth notes on the middle line, stems up, with flags.
    note_x = x + 0.6 * SPATIUM
    spacing = (right - note_x - 1.2 * SPATIUM) / 4.0
    for index in range(4):
        nx = note_x + index * spacing
        head_width = canvas.glyph(source, NOTEHEAD_BLACK, nx, middle)
        head_width = head_width or 1.18 * SPATIUM
        stem_x = nx + head_width - STEM_WIDTH * SPATIUM / 2
        stem_top = middle - 3.5 * SPATIUM
        canvas.line(stem_x, middle, stem_x, stem_top, STEM_WIDTH * SPATIUM)
        canvas.glyph(source, FLAG8TH_UP, stem_x - STEM_WIDTH * SPATIUM / 2, stem_top)

        if wettstai_codepoints:
            canvas.glyph(source, wettstai_codepoints[index % len(wettstai_codepoints)],
                         nx - 0.2 * SPATIUM, top - 0.8 * SPATIUM)

    canvas.line(right, top, right, top + 4 * SPATIUM, 0.16 * SPATIUM)


def render(original: Path, fixed: Path, bravura: Path | None, out_dir: Path) -> None:
    out_dir.mkdir(parents=True, exist_ok=True)
    # Four representative symbols: bataflafla, ruf3Links, muehlerad, schleppLinks.
    picks = [0, 18, 15, 44]
    alias_cps = [alias_codepoint(i) for i in picks]
    names = ", ".join(WETTSTAI_GLYPHS[i][1] for i in picks)

    canvas = Canvas(960, 660)
    before = GlyphSource(original, bravura)
    draw_mock_score(
        canvas, before, 190,
        "VORHER - Originalpaket",
        "Notenschluessel, Taktzahl 2 und Notenkoepfe sind schwarze Kaesten, "
        "die Faehnchen gepunktete Striche. Wettstai-Symbole: gar nicht einfuegbar.",
        None,
    )
    canvas.line(42, 300, canvas.width - 42, 300, 1.0, "#dddddd")
    after = GlyphSource(fixed, bravura)
    draw_mock_score(
        canvas, after, 500,
        "NACHHER - repariertes Paket",
        f"Normale Notation kommt aus Bravura, die Wettstai-Symbole stehen ueber den Noten "
        f"({names}).",
        alias_cps,
    )
    (out_dir / "preview.svg").write_text(canvas.to_svg(), encoding="utf-8")
    print(f"  wrote {out_dir / 'preview.svg'}")

    try:
        import cairosvg
        cairosvg.svg2png(url=str(out_dir / "preview.svg"),
                         write_to=str(out_dir / "preview.png"), output_width=1440)
        print(f"  wrote {out_dir / 'preview.png'}")
    except ImportError:
        print("  cairosvg not installed - PNG skipped")


def render_symbol_sheet(fixed: Path, out_dir: Path) -> None:
    """Specimen of all 60 symbols with the codepoint MuseScore addresses them by."""
    font = TTFont(str(fixed))
    glyph_set = font.getGlyphSet()

    cols, cell_w, cell_h = 5, 260, 150
    rows = (len(WETTSTAI_GLYPHS) + cols - 1) // cols
    canvas = Canvas(cols * cell_w, rows * cell_h + 56)
    canvas.text(16, 32, "WettstaiFont - alle 60 Symbole", size=20, weight="bold", colour="#111")

    for index, (optional_cp, name, desc) in enumerate(WETTSTAI_GLYPHS):
        row, col = divmod(index, cols)
        ox, oy = col * cell_w, row * cell_h + 56
        canvas.rect(ox, oy, cell_w, cell_h, stroke="#e4e4e4")

        pen = SVGPathPen(glyph_set)
        glyph_set[name].draw(pen)
        bounds_pen = BoundsPen(glyph_set)
        glyph_set[name].draw(bounds_pen)
        bounds = bounds_pen.bounds or (0, 0, 1, 1)

        avail_w, avail_h = cell_w - 28, cell_h - 74
        scale = min(avail_w / max(bounds[2] - bounds[0], 1),
                    avail_h / max(bounds[3] - bounds[1], 1), 0.14)
        x = ox + 14 - bounds[0] * scale
        y = oy + 18 + bounds[3] * scale
        canvas.parts.append(
            f'<g transform="translate({x:.2f},{y:.2f}) scale({scale:.5f},{-scale:.5f})">'
            f'<path d="{pen.getCommands()}" fill="#1a1a1a"/></g>'
        )
        canvas.text(ox + 14, oy + cell_h - 32, desc, size=12, colour="#222", weight="bold")
        canvas.text(ox + 14, oy + cell_h - 17, name, size=10, colour="#8a8a8a")
        canvas.text(ox + 14, oy + cell_h - 5,
                    f"MuseScore U+{alias_codepoint(index):04X}  -  SMuFL U+{optional_cp:04X}",
                    size=10, colour="#8a8a8a")

    font.close()
    (out_dir / "symbolliste.svg").write_text(canvas.to_svg(), encoding="utf-8")
    print(f"  wrote {out_dir / 'symbolliste.svg'}")
    try:
        import cairosvg
        cairosvg.svg2png(url=str(out_dir / "symbolliste.svg"),
                         write_to=str(out_dir / "symbolliste.png"), output_width=1500)
        print(f"  wrote {out_dir / 'symbolliste.png'}")
    except ImportError:
        print("  cairosvg not installed - PNG skipped")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--original", type=Path, default=HERE / "WettstaiFont-original.otf")
    parser.add_argument("--fixed", type=Path, default=REPO / "package" / "WettstaiFont.otf")
    parser.add_argument("--bravura", type=Path, default=None,
                        help="path to Bravura.otf (MuseScore's fallback font)")
    parser.add_argument("-o", "--out", type=Path, default=REPO / "docs")
    args = parser.parse_args()

    if args.bravura and not args.bravura.is_file():
        raise SystemExit(f"Bravura not found: {args.bravura}")
    render(args.original, args.fixed, args.bravura, args.out)
    render_symbol_sheet(args.fixed, args.out)


if __name__ == "__main__":
    main()
