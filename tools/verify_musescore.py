#!/usr/bin/env python3
"""Check the WettstaiFont package against MuseScore Studio's actual loading rules.

Every rule checked here was read off the MuseScore Studio source at tag
``v4.6.5`` rather than off documentation:

* ``src/notation/internal/engravingfontscontroller.cpp``
  - ``scanAllDirectories()`` scans ``<GenericDataLocation>/SMuFL/Fonts`` (on
    Windows: ``%LOCALAPPDATA%``) and ``%CommonProgramFiles%/SMuFL/Fonts``, and
    only then the private MusicFonts folder - and it skips that last one
    entirely when the setting is empty, which is its factory default
    (``setDefaultValue(USER_MUSIC_FONTS_PATH, Val(io::path_t {}))`` in
    ``src/notation/internal/notationconfiguration.cpp``).
  - ``scanDirectory()`` wants a sub-folder per font and picks *whatever*
    ``*.json`` its directory iterator yields last - so a font folder must
    contain exactly one JSON file. The font file must be ``<FolderName>.otf``
    or ``.ttf``. A folder whose name contains "Text" is skipped outright.
  - ``findFontPathGlobal()`` looks for ``<FolderName>.otf`` in the system font
    folders plus ``%LocalAppData%/Microsoft/Windows/Fonts``.
* ``src/engraving/internal/engravingfont.cpp``
  - ``ensureLoad()`` reads only ``glyphsWithAnchors``, ``glyphsWithAlternates``
    and ``engravingDefaults`` from the metadata. ``glyphBBoxes``,
    ``glyphAdvanceWidths`` and ``optionalGlyphs`` are never read.
  - ``computeMetrics()`` takes the bounding box and advance straight from the
    font file, by codepoint.
  - ``useFallbackFont()`` only kicks in when the symbol is *not* in the font
    (``Sym::isValid()`` is ``code != 0 && bbox.isValid()``). A glyph that exists
    but is wrong is drawn as-is; the fallback font is Bravura
    (``src/engraving/engravingmodule.cpp``).
* ``src/engraving/infrastructure/smufl.cpp`` + ``src/palette/widgets/symboldialog.cpp``
  - MuseScore's whole symbol universe comes from its own bundled
    ``fonts/smufl/glyphnames.json`` and ``ranges.json``, which stop at U+EF08.
    Anything a third-party font puts above that (the SMuFL optional range
    U+F400+) is unreachable from the UI.

Usage: python3 tools/verify_musescore.py
"""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
from pathlib import Path

from fontTools.pens.boundsPen import BoundsPen
from fontTools.pens.recordingPen import RecordingPen
from fontTools.ttLib import TTFont

sys.path.insert(0, str(Path(__file__).resolve().parent))
from wettstai_glyphs import (  # noqa: E402
    ALIAS_BLOCK_START,
    ALIAS_SMUFL_NAMES,
    FONT_NAME,
    STAFF_SPACE,
    WETTSTAI_GLYPHS,
    alias_codepoint,
)

HERE = Path(__file__).resolve().parent
REPO = HERE.parent
PACKAGE = REPO / "package"
ORIGINAL = HERE / "WettstaiFont-original.otf"

# MuseScore's SymId table is generated from its bundled glyphnames.json, which
# covers U+E000..U+EF08. A third-party font that maps anything in this window
# silently replaces a standard notation symbol.
MUSESCORE_SYMBOL_SPACE = range(0xE000, 0xEF09)

# The codepoints the original font squatted on, kept here so a regression is
# reported by name rather than as an anonymous number.
KNOWN_HIJACKS = {
    0xE000: "staff bracket / SMuFL basic area",
    0xE001: "staff bracket / SMuFL basic area",
    0xE002: "staff bracket / SMuFL basic area",
    0xE050: "gClef (treble clef)",
    0xE05C: "cClef (alto clef)",
    0xE062: "fClef (bass clef)",
    0xE080: "timeSig0",
    0xE081: "timeSig1",
    0xE082: "timeSig2",
    0xE0A4: "noteheadBlack",
    0xE240: "flag8thUp",
    0xE241: "flag8thDown",
    0xE242: "flag16thUp",
    0xE243: "flag16thDown",
    0xE244: "flag32ndUp",
    0xE245: "flag32ndDown",
}


class Report:
    def __init__(self) -> None:
        self.failures: list[str] = []
        self.warnings: list[str] = []

    def check(self, ok: bool, label: str, detail: str = "") -> bool:
        mark = "PASS" if ok else "FAIL"
        print(f"  [{mark}] {label}" + (f" - {detail}" if detail else ""))
        if not ok:
            self.failures.append(label)
        return ok

    def warn(self, label: str) -> None:
        print(f"  [WARN] {label}")
        self.warnings.append(label)

    def section(self, title: str) -> None:
        print(f"\n{title}")
        print("-" * len(title))


def outline_signature(font: TTFont, glyph_name: str) -> str:
    pen = RecordingPen()
    font.getGlyphSet()[glyph_name].draw(pen)
    return hashlib.sha256(repr(pen.value).encode()).hexdigest()


def bounds_of(font: TTFont, glyph_name: str):
    pen = BoundsPen(font.getGlyphSet())
    font.getGlyphSet()[glyph_name].draw(pen)
    return pen.bounds


# Files the installer puts into each MuseScore font folder. Kept in sync with
# the Set-FontFolder calls in Install-WettstaiFont.ps1, which this module checks.
INSTALLED_FONT_FOLDER_FILES = [f"{FONT_NAME}.otf", f"{FONT_NAME}.json"]


def check_package_layout(report: Report, package: Path) -> None:
    report.section("1. Folder layout (EngravingFontsController::scanDirectory)")

    report.check(
        "Text" not in FONT_NAME,
        "font/folder name does not contain 'Text'",
        f"'{FONT_NAME}' would otherwise be skipped as a text companion font",
    )
    for filename in INSTALLED_FONT_FOLDER_FILES:
        report.check((package / filename).is_file(), f"{filename} present in the package")

    # scanDirectory() takes whatever *.json the iterator yields last, so the
    # installed font folder must contain exactly one.
    installed_json = [f for f in INSTALLED_FONT_FOLDER_FILES if f.endswith(".json")]
    report.check(
        len(installed_json) == 1,
        "installed font folder holds exactly one *.json",
        f"{installed_json} - MuseScore 4.6 picks an arbitrary one otherwise",
    )

    script = package / "Install-WettstaiFont.ps1"
    if not report.check(script.is_file(), "Install-WettstaiFont.ps1 present"):
        return
    text = script.read_text(encoding="utf-8")

    # The installer must place only those two files, and must clear out the
    # stray metadata.json / glyphnames.json that earlier versions left behind.
    report.check(
        '-Files @($jsonFile)' in text and '-Files @($otfFile, $jsonFile)' in text,
        "installer copies only the OTF and the one metadata JSON",
    )
    report.check(
        'Filter "*.json"' in text and "Remove-Item" in text,
        "installer clears stale *.json from the font folders",
        "otherwise an old metadata.json/glyphnames.json can win the scan",
    )
    report.check(
        "SMuFL\\Fonts" in text,
        "installer writes the global SMuFL folder",
        "the only route that works without changing MuseScore preferences",
    )
    report.check(
        "Microsoft\\Windows\\Fonts" in text,
        "installer registers the OTF where findFontPathGlobal() looks",
    )


def check_font(report: Report, font_path: Path, original_path: Path) -> TTFont:
    report.section("2. Font file (EngravingFont::computeMetrics / useFallbackFont)")
    font = TTFont(str(font_path))
    cmap = font.getBestCmap()

    # 2a. Nothing may squat on MuseScore's standard symbol space except the
    #     alias block we deliberately use.
    expected_aliases = {alias_codepoint(i) for i in range(len(WETTSTAI_GLYPHS))}
    occupied = {cp for cp in cmap if cp in MUSESCORE_SYMBOL_SPACE}
    unexpected = sorted(occupied - expected_aliases)
    detail = ", ".join(
        f"U+{cp:04X} ({KNOWN_HIJACKS.get(cp, 'standard symbol')})" for cp in unexpected
    )
    report.check(
        not unexpected,
        "no standard MuseScore symbol is overridden",
        detail or "clefs, time signatures, noteheads and flags fall back to Bravura",
    )

    # 2b. All 60 Wettstai symbols reachable from the MuseScore UI.
    missing_alias = [
        f"U+{alias_codepoint(i):04X}"
        for i, (_cp, name, _d) in enumerate(WETTSTAI_GLYPHS)
        if cmap.get(alias_codepoint(i)) != name
    ]
    report.check(
        not missing_alias,
        f"all {len(WETTSTAI_GLYPHS)} symbols mapped into MuseScore's symbol space",
        f"U+{ALIAS_BLOCK_START:04X}..U+{alias_codepoint(len(WETTSTAI_GLYPHS) - 1):04X}"
        if not missing_alias else f"missing: {missing_alias}",
    )

    # 2c. The SMuFL optional codepoints are still there for spec-compliant hosts.
    missing_optional = [
        f"U+{cp:04X}" for cp, name, _d in WETTSTAI_GLYPHS if cmap.get(cp) != name
    ]
    report.check(
        not missing_optional,
        "SMuFL optional codepoints U+F400..U+F43B intact",
        f"missing: {missing_optional}" if missing_optional else "for Dorico/Finale/spec tools",
    )

    # 2d. Advance widths must cover the ink, otherwise symbols collide.
    hmtx = font["hmtx"]
    too_narrow = []
    for _cp, name, _d in WETTSTAI_GLYPHS:
        bounds = bounds_of(font, name)
        if bounds is None:
            continue
        advance = hmtx[name][0]
        if advance < bounds[2]:
            too_narrow.append(f"{name} (adv {advance} < ink {int(bounds[2])})")
    report.check(
        not too_narrow,
        "advance widths cover the ink of every glyph",
        f"{len(too_narrow)} glyph(s) too narrow: {too_narrow[:3]}" if too_narrow else "",
    )

    # 2e. Vertical metrics must not clip.
    head, hhea, os2 = font["head"], font["hhea"], font["OS/2"]
    report.check(head.unitsPerEm == 1000, "unitsPerEm is 1000",
                 "SMuFL staff space = 250 units")
    report.check(
        hhea.ascent >= head.yMax and abs(hhea.descent) >= abs(head.yMin),
        "hhea ascent/descent enclose every glyph",
        f"ascent {hhea.ascent} >= yMax {head.yMax}, descent {hhea.descent} <= yMin {head.yMin}",
    )
    report.check(
        os2.usWinAscent >= head.yMax and os2.usWinDescent >= abs(head.yMin),
        "OS/2 win metrics enclose every glyph",
        f"winAscent {os2.usWinAscent}, winDescent {os2.usWinDescent}",
    )
    report.check(
        os2.sTypoDescender <= head.yMin,
        "OS/2 sTypoDescender reaches the lowest glyph",
        f"sTypoDescender {os2.sTypoDescender} <= yMin {head.yMin}",
    )

    # 2f. Family name must match the folder name MuseScore registers.
    family = next(
        (r.toUnicode() for r in font["name"].names if r.nameID == 1 and r.platformID == 3),
        None,
    )
    report.check(family == FONT_NAME, "family name matches the folder name",
                 f"name ID 1 = '{family}'")

    # 2g. Outlines must be byte-identical to the artwork the user supplied.
    if original_path.is_file():
        original = TTFont(str(original_path))
        changed = [
            name for _cp, name, _d in WETTSTAI_GLYPHS
            if outline_signature(original, name) != outline_signature(font, name)
        ]
        original.close()
        report.check(not changed, "all 60 outlines identical to the original artwork",
                     f"changed: {changed}" if changed else "no drawing was touched")
    else:
        report.warn(f"original font not found at {original_path}, skipping outline diff")

    return font


def check_metadata(report: Report, font: TTFont, metadata_path: Path) -> None:
    report.section("3. SMuFL metadata (EngravingFont::ensureLoad)")
    try:
        metadata = json.loads(metadata_path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        report.check(False, "metadata parses as JSON", str(exc))
        return

    report.check(metadata.get("fontName") == FONT_NAME, "fontName matches",
                 f"'{metadata.get('fontName')}'")

    # The three blocks MuseScore actually reads.
    for key in ("engravingDefaults", "glyphsWithAnchors", "glyphsWithAlternates"):
        report.check(isinstance(metadata.get(key), dict), f"'{key}' present and an object")

    # Keys that do not exist in the SMuFL metadata format at all.
    bogus = [k for k in ("glyphs", "glyphClasses", "ranges", "smuflVersion") if k in metadata]
    report.check(not bogus, "no non-SMuFL keys in the metadata",
                 f"found: {bogus}" if bogus else "")

    # engravingDefaults are applied to the score style, so they must be plausible
    # staff-space values, not font units.
    numeric = {k: v for k, v in metadata.get("engravingDefaults", {}).items()
               if isinstance(v, (int, float))}
    out_of_range = {k: v for k, v in numeric.items() if not 0 < v <= 5}
    report.check(not out_of_range, "engravingDefaults are in staff spaces",
                 f"suspicious: {out_of_range}" if out_of_range else f"{len(numeric)} values")

    # glyphBBoxes / glyphAdvanceWidths must match the font, in staff spaces.
    hmtx = font["hmtx"]
    bbox_errors, adv_errors = [], []
    for index, (_cp, name, _d) in enumerate(WETTSTAI_GLYPHS):
        bounds = bounds_of(font, name) or (0, 0, 0, 0)
        for key in (name, ALIAS_SMUFL_NAMES[index]):
            entry = metadata.get("glyphBBoxes", {}).get(key)
            if not isinstance(entry, dict) or "bBoxNE" not in entry or "bBoxSW" not in entry:
                bbox_errors.append(f"{key}: missing or wrong shape")
                continue
            expected_ne = [round(bounds[2] / STAFF_SPACE, 4), round(bounds[3] / STAFF_SPACE, 4)]
            expected_sw = [round(bounds[0] / STAFF_SPACE, 4), round(bounds[1] / STAFF_SPACE, 4)]
            if entry["bBoxNE"] != expected_ne or entry["bBoxSW"] != expected_sw:
                bbox_errors.append(f"{key}: {entry} != NE {expected_ne} SW {expected_sw}")
            expected_adv = round(hmtx[name][0] / STAFF_SPACE, 4)
            if metadata.get("glyphAdvanceWidths", {}).get(key) != expected_adv:
                adv_errors.append(key)

    report.check(not bbox_errors, "glyphBBoxes match the font, in staff spaces",
                 f"{len(bbox_errors)} problem(s), e.g. {bbox_errors[:2]}" if bbox_errors else "")
    report.check(not adv_errors, "glyphAdvanceWidths match the font, in staff spaces",
                 f"{len(adv_errors)} mismatch(es)" if adv_errors else "")

    # optionalGlyphs must carry U+-prefixed codepoints.
    optional = metadata.get("optionalGlyphs", {})
    bad_cp = [k for k, v in optional.items()
              if not str(v.get("codepoint", "")).startswith("U+")]
    report.check(
        len(optional) == len(WETTSTAI_GLYPHS) and not bad_cp,
        "optionalGlyphs lists all 60 symbols with U+ codepoints",
        f"{len(optional)} entries, {len(bad_cp)} malformed" if bad_cp else f"{len(optional)} entries",
    )


def print_resolution_table(font: TTFont) -> None:
    print("\n4. What MuseScore draws with WettstaiFont selected")
    print("-" * 50)
    cmap = font.getBestCmap()
    samples = [
        (0xE050, "gClef"), (0xE062, "fClef"), (0xE0A4, "noteheadBlack"),
        (0xE080, "timeSig0"), (0xE240, "flag8thUp"), (0xE4E5, "rest8th"),
    ]
    for cp, label in samples:
        source = f"WettstaiFont ({cmap[cp]})" if cp in cmap else "Bravura (fallback)"
        print(f"  U+{cp:04X} {label:<16} -> {source}")
    first, last = alias_codepoint(0), alias_codepoint(len(WETTSTAI_GLYPHS) - 1)
    print(f"  U+{first:04X}..U+{last:04X} {'Wettstai symbols':<16} -> WettstaiFont"
          f" ({len(WETTSTAI_GLYPHS)} glyphs, Master Palette -> Beaters pictograms)")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("-p", "--package", type=Path, default=PACKAGE)
    args = parser.parse_args()

    print(f"Verifying {args.package} against MuseScore Studio 4.6 loading rules")
    report = Report()
    check_package_layout(report, args.package)
    font = check_font(report, args.package / f"{FONT_NAME}.otf", ORIGINAL)
    check_metadata(report, font, args.package / f"{FONT_NAME}.json")
    print_resolution_table(font)
    font.close()

    print()
    if report.failures:
        print(f"FAILED: {len(report.failures)} check(s) - {report.failures}")
        return 1
    print(f"All checks passed ({len(report.warnings)} warning(s)).")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
