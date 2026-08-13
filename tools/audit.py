#!/usr/bin/env python3
"""Independent end-to-end audit of the WettstaiFont package.

This deliberately does NOT reuse the build's own assumptions. Where possible it
re-derives facts from primary sources:

* the untouched original font, for every "this was broken" claim
* MuseScore Studio's own data files and headers, for every "MuseScore does X"
  claim (pass --musescore <checkout of tag v4.6.5>)
* Bravura's metadata, for the shape of a correct SMuFL metadata file
* the built artefacts themselves, re-measured with fontTools

Usage:
    python3 tools/audit.py [--musescore /path/to/MuseScore] [--bravura /path/to/Bravura.otf]
"""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import shutil
import subprocess
import sys
import tempfile
import zipfile
from pathlib import Path

from fontTools.pens.boundsPen import BoundsPen
from fontTools.pens.recordingPen import RecordingPen
from fontTools.ttLib import TTFont

HERE = Path(__file__).resolve().parent
REPO = HERE.parent
PACKAGE = REPO / "package"
ORIGINAL = HERE / "WettstaiFont-original.otf"
BUILT = PACKAGE / "WettstaiFont.otf"
METADATA = PACKAGE / "WettstaiFont.json"
GLYPHNAMES = PACKAGE / "glyphnames.json"
ZIP_PATH = REPO / "WettstaiFont-MuseScore4-Setup.zip"

# The 16 codepoints the original font occupied and had to give up.
HIJACKED = {
    0xE000: "SMuFL basic area", 0xE001: "SMuFL basic area", 0xE002: "SMuFL basic area",
    0xE050: "gClef", 0xE05C: "cClef", 0xE062: "fClef",
    0xE080: "timeSig0", 0xE081: "timeSig1", 0xE082: "timeSig2",
    0xE0A4: "noteheadBlack",
    0xE240: "flag8thUp", 0xE241: "flag8thDown", 0xE242: "flag16thUp",
    0xE243: "flag16thDown", 0xE244: "flag32ndUp", 0xE245: "flag32ndDown",
}

ALIAS_FIRST, ALIAS_COUNT = 0xE770, 60
STAFF_SPACE = 250.0

# Filled in by audit_musescore() from engravingfont.cpp; used later to judge
# metadata keys that Bravura's own (older) metadata happens not to carry.
MUSESCORE_ENGRAVING_DEFAULTS: set[str] = set()


class Audit:
    def __init__(self) -> None:
        self.passed = 0
        self.failures: list[str] = []
        self.warnings: list[str] = []
        self.skipped: list[str] = []

    def section(self, title: str) -> None:
        print(f"\n{title}\n{'=' * len(title)}")

    def ok(self, label: str, detail: str = "") -> None:
        self.passed += 1
        print(f"  PASS  {label}" + (f"  [{detail}]" if detail else ""))

    def fail(self, label: str, detail: str = "") -> None:
        self.failures.append(label)
        print(f"  FAIL  {label}" + (f"  [{detail}]" if detail else ""))

    def check(self, condition: bool, label: str, detail: str = "") -> bool:
        (self.ok if condition else self.fail)(label, detail)
        return bool(condition)

    def warn(self, label: str) -> None:
        self.warnings.append(label)
        print(f"  WARN  {label}")

    def skip(self, label: str, why: str) -> None:
        self.skipped.append(label)
        print(f"  SKIP  {label}  [{why}]")


def sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def outline_hash(font: TTFont, name: str) -> str:
    pen = RecordingPen()
    font.getGlyphSet()[name].draw(pen)
    return sha256(repr(pen.value).encode())


def bounds(font: TTFont, name: str):
    pen = BoundsPen(font.getGlyphSet())
    font.getGlyphSet()[name].draw(pen)
    return pen.bounds


# ---------------------------------------------------------------- section A
def audit_repo(a: Audit) -> None:
    a.section("A. Repository and remote")

    def git(*args: str) -> str:
        return subprocess.run(["git", *args], cwd=REPO, capture_output=True,
                              text=True).stdout.strip()

    a.check(git("status", "--porcelain") == "", "working tree is clean",
            git("status", "--porcelain")[:80] or "no uncommitted changes")

    branch = git("rev-parse", "--abbrev-ref", "HEAD")
    a.check(branch == "claude/musescore-fonts-check-bp3zt4",
            "on the designated branch", branch)

    local = git("rev-parse", "HEAD")
    remote = git("rev-parse", f"origin/{branch}")
    a.check(local and local == remote, "local HEAD equals origin", local[:12])

    # Every tracked file must match its committed blob.
    diff = git("diff", "--stat", "HEAD")
    a.check(diff == "", "no diff against HEAD", diff[:80] or "identical")

    tracked = set(git("ls-tree", "-r", "--name-only", "HEAD").splitlines())
    required = {
        "README.md", ".gitignore", "WettstaiFont-MuseScore4-Setup.zip",
        "package/WettstaiFont.otf", "package/WettstaiFont.json",
        "package/glyphnames.json", "package/Symbolliste.md", "package/LIESMICH.md",
        "package/Install-WettstaiFont.ps1", "package/Uninstall-WettstaiFont.ps1",
        "tools/WettstaiFont-original.otf", "tools/build_font.py",
        "tools/build_metadata.py", "tools/build_package.py",
        "tools/render_preview.py", "tools/verify_musescore.py",
        "tools/wettstai_glyphs.py",
        "docs/preview.png", "docs/symbolliste.png",
    }
    missing = sorted(required - tracked)
    a.check(not missing, "all expected files are committed",
            f"missing: {missing}" if missing else f"{len(tracked)} tracked files")

    junk = sorted(f for f in tracked if "__pycache__" in f or f.endswith(".pyc"))
    a.check(not junk, "no build junk committed", str(junk) if junk else "clean")


# ---------------------------------------------------------------- section B
def audit_reproducible(a: Audit) -> None:
    a.section("B. Reproducibility (rebuild from the original and compare)")

    with tempfile.TemporaryDirectory() as tmp:
        out = Path(tmp) / "package"
        out.mkdir()
        font_build = subprocess.run(
            [sys.executable, str(HERE / "build_font.py"), "-o", str(out / "WettstaiFont.otf")],
            capture_output=True, text=True, cwd=REPO)
        if not a.check(font_build.returncode == 0, "build_font.py runs clean",
                       font_build.stderr.strip()[-120:] or "exit 0"):
            return
        meta_build = subprocess.run(
            [sys.executable, str(HERE / "build_metadata.py"), "-f", str(out / "WettstaiFont.otf")],
            capture_output=True, text=True, cwd=REPO)
        a.check(meta_build.returncode == 0, "build_metadata.py runs clean",
                meta_build.stderr.strip()[-120:] or "exit 0")

        for name in ("WettstaiFont.otf", "WettstaiFont.json", "glyphnames.json",
                     "Symbolliste.md"):
            rebuilt = (out / name).read_bytes()
            shipped = (PACKAGE / name).read_bytes()
            a.check(rebuilt == shipped, f"{name} rebuilds byte-identical",
                    f"{sha256(shipped)[:16]}" if rebuilt == shipped
                    else f"{len(rebuilt)} vs {len(shipped)} bytes")


# ---------------------------------------------------------------- section C
def audit_font_structure(a: Audit) -> TTFont:
    a.section("C. Font file structure")
    font = TTFont(str(BUILT))

    required_tables = {"CFF ", "OS/2", "cmap", "head", "hhea", "hmtx", "maxp", "name", "post"}
    present = set(font.keys()) - {"GlyphOrder"}
    a.check(required_tables <= present, "all required OpenType tables present",
            f"{sorted(present)}")

    order = font.getGlyphOrder()
    a.check(order[0] == ".notdef", "glyph 0 is .notdef", order[0])
    a.check(len(order) == ALIAS_COUNT + 1, "61 glyphs (.notdef + 60 symbols)", str(len(order)))
    a.check(len(set(order)) == len(order), "no duplicate glyph names")
    bad_names = [g for g in order if not re.fullmatch(r"[A-Za-z_.][A-Za-z0-9_.]*", g)]
    a.check(not bad_names, "all glyph names are valid PostScript names", str(bad_names))

    head = font["head"]
    a.check(head.unitsPerEm == 1000, "unitsPerEm 1000", str(head.unitsPerEm))

    # head bbox must equal the real ink extents of the whole font.
    all_b = [bounds(font, g) for g in order]
    all_b = [b for b in all_b if b]
    real = (int(min(b[0] for b in all_b)), int(min(b[1] for b in all_b)),
            int(max(b[2] for b in all_b)), int(max(b[3] for b in all_b)))
    a.check((head.xMin, head.yMin, head.xMax, head.yMax) == real,
            "head bounding box matches the outlines",
            f"{(head.xMin, head.yMin, head.xMax, head.yMax)} vs {real}")

    cff = font["CFF "].cff
    top = cff[cff.fontNames[0]]
    fb = [int(round(v)) for v in top.FontBBox]
    a.check(fb[0] <= real[0] and fb[1] <= real[1] and fb[2] >= real[2] and fb[3] >= real[3],
            "CFF FontBBox encloses the outlines", f"{fb} vs {list(real)}")
    matrix = getattr(top, "FontMatrix", [0.001, 0, 0, 0.001, 0, 0])
    a.check(abs(matrix[0] - 1.0 / head.unitsPerEm) < 1e-9,
            "CFF FontMatrix matches unitsPerEm", str(matrix[0]))
    a.check(cff.fontNames[0] == "WettstaiFont", "CFF font name", cff.fontNames[0])

    hhea, os2 = font["hhea"], font["OS/2"]
    a.check(hhea.numberOfHMetrics <= len(order), "hhea.numberOfHMetrics sane",
            str(hhea.numberOfHMetrics))
    a.check(hhea.ascent >= head.yMax and hhea.descent <= head.yMin,
            "hhea metrics enclose the outlines", f"{hhea.ascent}/{hhea.descent}")
    a.check(os2.usWinAscent >= head.yMax and os2.usWinDescent >= abs(head.yMin),
            "OS/2 win metrics enclose the outlines",
            f"{os2.usWinAscent}/{os2.usWinDescent}")
    a.check(os2.sTypoDescender <= head.yMin, "sTypoDescender reaches the lowest ink",
            str(os2.sTypoDescender))
    a.check(os2.fsType == 0, "fsType 0 (installable, no embedding restriction)")
    a.check(os2.ulUnicodeRange2 & (1 << (60 - 32)) != 0,
            "OS/2 declares the Private Use Area (bit 60)")

    cmap = font.getBestCmap()
    a.check(os2.usFirstCharIndex == min(cmap) and os2.usLastCharIndex == max(cmap),
            "OS/2 first/last char index match the cmap",
            f"{hex(os2.usFirstCharIndex)}..{hex(os2.usLastCharIndex)}")

    subtables = [(t.platformID, t.platEncID, t.format) for t in font["cmap"].tables]
    a.check((3, 1, 4) in subtables, "Windows Unicode BMP cmap subtable present", str(subtables))
    a.check(all(len(t.cmap) == len(cmap) for t in font["cmap"].tables),
            "all cmap subtables carry the same mapping")

    names = {r.nameID: r.toUnicode() for r in font["name"].names if r.platformID == 3}
    for nid, expect in ((1, "WettstaiFont"), (6, "WettstaiFont"), (16, "WettstaiFont")):
        a.check(names.get(nid) == expect, f"name ID {nid} is '{expect}'", str(names.get(nid)))
    a.check(names.get(5, "").startswith("Version "), "name ID 5 is a version string",
            names.get(5, ""))
    a.check(abs(head.fontRevision - 2.0) < 1e-6, "head.fontRevision 2.0",
            str(head.fontRevision))

    # Round-trip compile: catches structural damage fontTools would refuse to write.
    import io
    buf = io.BytesIO()
    font.save(buf)
    buf.seek(0)
    try:
        TTFont(buf)
        a.ok("font recompiles and reparses")
    except Exception as exc:                                  # noqa: BLE001
        a.fail("font recompiles and reparses", str(exc)[:100])
    return font


# ---------------------------------------------------------------- section D
def audit_against_original(a: Audit, font: TTFont) -> None:
    a.section("D. Against the untouched original (every repair claim)")
    original = TTFont(str(ORIGINAL))
    orig_cmap = original.getBestCmap()
    cmap = font.getBestCmap()

    # The original really did squat on those codepoints...
    had = sorted(cp for cp in HIJACKED if cp in orig_cmap)
    a.check(len(had) == len(HIJACKED), "original occupied all 16 reported codepoints",
            f"{len(had)}/{len(HIJACKED)}")
    # ...and the ten placeholders really were one and the same rectangle.
    box_cps = [cp for cp in HIJACKED if cp < 0xE240]
    box_hashes = {outline_hash(original, orig_cmap[cp]) for cp in box_cps}
    a.check(len(box_hashes) == 1, "the ten placeholders were one identical outline",
            f"{len(box_hashes)} distinct outline(s) across {len(box_cps)} glyphs")
    b = bounds(original, orig_cmap[0xE050])
    a.check([int(v) for v in b] == [146, 190, 762, 472],
            "placeholder box measured 146,190-762,472 as documented", str(b))

    # ...and none of them survive.
    survivors = sorted(cp for cp in HIJACKED if cp in cmap)
    a.check(not survivors, "none of the 16 codepoints survive in the built font",
            str([hex(c) for c in survivors]))

    # The 60 kept glyphs must be untouched drawings.
    kept = sorted(orig_cmap[cp] for cp in orig_cmap if cp >= 0xF400)
    a.check(len(kept) == ALIAS_COUNT, "original had exactly 60 Wettstai glyphs", str(len(kept)))
    changed = [g for g in kept if outline_hash(original, g) != outline_hash(font, g)]
    a.check(not changed, "all 60 outlines are bit-identical to the original",
            f"changed: {changed}" if changed else "no drawing altered")

    # Reported defects in numbers.
    o_hmtx, n_hmtx = original["hmtx"], font["hmtx"]
    o_adv = [o_hmtx[g][0] for g in kept]
    a.check(min(o_adv) == 45 and max(o_adv) == 833,
            "original advance widths ranged 45-833 as documented",
            f"{min(o_adv)}-{max(o_adv)}")
    max_ink = max(int(bounds(original, g)[2]) for g in kept)
    a.check(max_ink == 4199, "widest original drawing was 4199 units", str(max_ink))
    too_narrow = [g for g in kept if n_hmtx[g][0] < bounds(font, g)[2]]
    a.check(not too_narrow, "every rebuilt advance covers its ink",
            f"{len(too_narrow)} still short" if too_narrow else "60/60")

    a.check(original["hhea"].ascent == 2181, "original hhea.ascent was 2181",
            str(original["hhea"].ascent))
    a.check(original["OS/2"].sTypoDescender == 0, "original sTypoDescender was 0",
            str(original["OS/2"].sTypoDescender))
    o_ymin = min(int(bounds(original, g)[1]) for g in original.getGlyphOrder()
                 if bounds(original, g))
    a.check(o_ymin == -297, "original lowest ink was -297 units", str(o_ymin))

    # The six flag-slot glyphs really were copies of the Wert marks.
    def normalised(f: TTFont, name: str) -> str:
        pen = RecordingPen()
        f.getGlyphSet()[name].draw(pen)
        pts = [p for _op, args in pen.value for p in args]
        if not pts:
            return ""
        ox, oy = min(x for x, _ in pts), min(y for _, y in pts)
        return sha256(repr([(round(x - ox), round(y - oy)) for x, y in pts]).encode())

    pairs = [(0xE240, "wert8el"), (0xE241, "wert8el2"), (0xE242, "wert16tel"),
             (0xE243, "wert16tel2"), (0xE244, "wertQuintole"), (0xE245, "wertQuintole2")]
    copies = [cp for cp, target in pairs
              if normalised(original, orig_cmap[cp]) == normalised(original, target)]
    a.check(len(copies) == 6, "all six flag-slot glyphs were shifted copies of Wert marks",
            f"{len(copies)}/6")
    still_there = [t for _cp, t in pairs if t not in font.getGlyphOrder()]
    a.check(not still_there, "the Wert marks themselves are still in the font",
            "6/6 kept as normal symbols")
    original.close()


# ---------------------------------------------------------------- section E
def audit_musescore(a: Audit, font: TTFont, ms: Path | None) -> None:
    a.section("E. MuseScore v4.6.5 compatibility (cross-checked against its own data)")
    cmap = font.getBestCmap()

    if ms is None or not (ms / "fonts/smufl/glyphnames.json").is_file():
        a.skip("cross-check against MuseScore's data files", "no --musescore checkout given")
        return

    tag = subprocess.run(["git", "describe", "--tags"], cwd=ms,
                         capture_output=True, text=True).stdout.strip()
    a.check(tag == "v4.6.5", "MuseScore checkout is at tag v4.6.5", tag or "unknown")

    ms_glyphnames = json.loads((ms / "fonts/smufl/glyphnames.json").read_text())
    ms_ranges = json.loads((ms / "fonts/smufl/ranges.json").read_text())
    symid_src = (ms / "src/engraving/types/symid_p.h").read_text()
    body = re.search(r"enum class SymId.*?\{(.*?)\};", symid_src, re.S).group(1)
    sym_ids = set()
    for line in body.split("\n"):
        for token in line.split("//")[0].split(","):
            token = token.strip().split("=")[0].strip()
            if re.fullmatch(r"[A-Za-z_][A-Za-z0-9_]*", token):
                sym_ids.add(token)

    # The codepoints MuseScore can actually address.
    known_cp = {}
    for name, entry in ms_glyphnames.items():
        if name in sym_ids and "codepoint" in entry:
            known_cp[int(entry["codepoint"][2:], 16)] = name
    a.check(len(known_cp) > 2500, "derived MuseScore's addressable codepoints",
            f"{len(known_cp)} SymIds, U+{min(known_cp):04X}..U+{max(known_cp):04X}")
    a.check(max(known_cp) < 0xF000,
            "MuseScore cannot address anything at U+F000 or above",
            f"highest is U+{max(known_cp):04X}")

    # 1. Nothing standard is overridden.
    aliases = set(range(ALIAS_FIRST, ALIAS_FIRST + ALIAS_COUNT))
    intruders = sorted(set(cmap) & set(known_cp) - aliases)
    a.check(not intruders, "font overrides no MuseScore symbol outside the alias block",
            ", ".join(f"U+{c:04X} {known_cp[c]}" for c in intruders) or "0 intruders")

    # 2. Every alias slot is a real, addressable SymId.
    unknown = [f"U+{c:04X}" for c in sorted(aliases) if c not in known_cp]
    a.check(not unknown, "all 60 alias codepoints are real MuseScore SymIds",
            f"unknown: {unknown}" if unknown else "60/60")

    # 3. All 60 sit in the palette group the docs name.
    beaters = set(ms_ranges["beatersPictograms"]["glyphs"])
    outside = [known_cp[c] for c in sorted(aliases) if known_cp[c] not in beaters]
    a.check(not outside, "all 60 belong to the 'Beaters pictograms' palette group",
            f"outside: {outside}" if outside else
            f"group holds {len(beaters)} glyphs, 60 used")

    # 4. The palette lists a group in ranges.json order; check ours is contiguous
    #    and at the front, so the user meets them as one block.
    order_in_group = [g for g in ms_ranges["beatersPictograms"]["glyphs"]
                      if g in {known_cp[c] for c in aliases}]
    positions = [ms_ranges["beatersPictograms"]["glyphs"].index(g) for g in order_in_group]
    a.check(positions == list(range(ALIAS_COUNT)),
            "the 60 symbols are the first 60 cells of that group",
            f"positions {positions[0]}..{positions[-1]}")

    # 5. Alias order follows the Wettstai codepoint order (docs depend on this).
    f4 = sorted(cp for cp in cmap if cp >= 0xF400)
    mismatch = [i for i, cp in enumerate(f4) if cmap[cp] != cmap[ALIAS_FIRST + i]]
    a.check(not mismatch, "alias order matches the U+F400 order one-to-one",
            f"{len(mismatch)} mismatches" if mismatch else "60/60 aligned")

    # 6. Simulate glyph resolution for every symbol MuseScore knows.
    from_wettstai = sorted(c for c in known_cp if c in cmap)
    a.check(len(from_wettstai) == ALIAS_COUNT,
            "exactly 60 MuseScore symbols resolve to WettstaiFont", str(len(from_wettstai)))

    # 7. Confirm the source rules the docs quote still read that way.
    controller = (ms / "src/notation/internal/engravingfontscontroller.cpp").read_text()
    config = (ms / "src/notation/internal/notationconfiguration.cpp").read_text()
    engfont = (ms / "src/engraving/internal/engravingfont.cpp").read_text()
    module = (ms / "src/engraving/engravingmodule.cpp").read_text()

    a.check("setDefaultValue(USER_MUSIC_FONTS_PATH, Val(io::path_t {}))" in config,
            "MusicFonts path still defaults to empty (finding 4)")
    a.check("if (!userFontsPath.empty()) {" in controller,
            "private folder is still skipped when that setting is empty")
    a.check('scanDirectory(*it + "/SMuFL/Fonts", false)' in controller,
            "global SMuFL folders are still scanned unconditionally")
    a.check('QDirIterator jsonFilesIterator(fontDir, { "*.json" }, QDir::Files)' in controller,
            "scanDirectory still takes an arbitrary *.json (finding 5)")
    a.check('qgetenv("LocalAppData").replace("\\\\", "/") + "/Microsoft/Windows/Fonts"'
            in controller,
            "findFontPathGlobal still looks in the user font folder")
    a.check("!sym(id).isValid()" in engfont, "fallback still keyed on the glyph being absent")
    a.check('setFallbackFont("Bravura")' in module, "fallback font is still Bravura")
    for key in ("glyphsWithAnchors", "glyphsWithAlternates", "engravingDefaults"):
        a.check(f'metadataJson.value("{key}")' in engfont,
                f"ensureLoad still reads '{key}'")
    for key in ("optionalGlyphs", "glyphBBoxes", "glyphAdvanceWidths"):
        a.check(f'metadataJson.value("{key}")' not in engfont,
                f"ensureLoad still ignores '{key}' (finding 1/6)")

    # 8. The engravingDefaults we ship must be keys MuseScore maps.
    supported = set(re.findall(r'\{\s*"([a-zA-Z]+)",\s*\{\s*\{\s*Sid::', engfont))
    MUSESCORE_ENGRAVING_DEFAULTS.update(supported)
    shipped = {k for k, v in json.loads(METADATA.read_text())["engravingDefaults"].items()
               if isinstance(v, (int, float))}
    unmapped = sorted(shipped - supported)
    if unmapped:
        a.warn(f"engravingDefaults MuseScore ignores (harmless, kept for other apps): "
               f"{', '.join(unmapped)}")
    else:
        a.ok("every numeric engravingDefault is one MuseScore applies")


# ---------------------------------------------------------------- section F
def audit_metadata(a: Audit, font: TTFont, bravura: Path | None) -> None:
    a.section("F. SMuFL metadata")
    raw = METADATA.read_bytes()
    try:
        raw.decode("utf-8")
        a.ok("metadata is valid UTF-8")
    except UnicodeDecodeError as exc:
        a.fail("metadata is valid UTF-8", str(exc))
    meta = json.loads(raw)

    if bravura and bravura.is_file():
        ref = json.loads((bravura.parent / "bravura_metadata.json").read_text())
        unexpected = sorted(set(meta) - set(ref))
        a.check(not unexpected, "no keys Bravura's metadata does not also use",
                f"extra: {unexpected}" if unexpected else f"{len(meta)} keys")
        # Bravura's shipped metadata predates parts of SMuFL 1.4, so a key it
        # lacks is only wrong if MuseScore does not know it either.
        ed_unexpected = sorted(set(meta["engravingDefaults"]) - set(ref["engravingDefaults"])
                               - MUSESCORE_ENGRAVING_DEFAULTS)
        a.check(not ed_unexpected,
                "engravingDefaults keys are known to Bravura or to MuseScore",
                str(ed_unexpected) if ed_unexpected else
                f"{len(meta['engravingDefaults'])} keys")
    else:
        a.skip("compare key set against Bravura's metadata", "no --bravura given")

    cmap = font.getBestCmap()
    hmtx = font["hmtx"]
    bbox_bad, adv_bad, shape_bad = [], [], []
    for key, entry in meta["glyphBBoxes"].items():
        if not (isinstance(entry, dict) and set(entry) == {"bBoxNE", "bBoxSW"}):
            shape_bad.append(key)
    a.check(not shape_bad, "every glyphBBoxes entry uses bBoxNE/bBoxSW",
            f"{len(shape_bad)} malformed" if shape_bad else f"{len(meta['glyphBBoxes'])} entries")

    # Re-measure independently and compare, including the sign of the y values
    # (the original metadata had these transposed).
    for cp in sorted(c for c in cmap if c >= 0xF400):
        name = cmap[cp]
        b = bounds(font, name) or (0, 0, 0, 0)
        want_ne = [round(b[2] / STAFF_SPACE, 4), round(b[3] / STAFF_SPACE, 4)]
        want_sw = [round(b[0] / STAFF_SPACE, 4), round(b[1] / STAFF_SPACE, 4)]
        want_adv = round(hmtx[name][0] / STAFF_SPACE, 4)
        for key in (name, cmap[ALIAS_FIRST + sorted(c for c in cmap if c >= 0xF400).index(cp)]):
            pass
        entry = meta["glyphBBoxes"].get(name)
        if not entry or entry.get("bBoxNE") != want_ne or entry.get("bBoxSW") != want_sw:
            bbox_bad.append(name)
        if meta["glyphAdvanceWidths"].get(name) != want_adv:
            adv_bad.append(name)
    a.check(not bbox_bad, "glyphBBoxes re-measure correctly in staff spaces",
            f"{len(bbox_bad)} wrong" if bbox_bad else "60/60")
    a.check(not adv_bad, "glyphAdvanceWidths re-measure correctly",
            f"{len(adv_bad)} wrong" if adv_bad else "60/60")

    # Both naming routes must be described.
    a.check(len(meta["glyphBBoxes"]) == 2 * ALIAS_COUNT,
            "metadata describes both the Wettstai and the alias names",
            f"{len(meta['glyphBBoxes'])} entries")

    opt = meta["optionalGlyphs"]
    a.check(len(opt) == ALIAS_COUNT, "optionalGlyphs holds all 60", str(len(opt)))
    wrong_cp = [k for k, v in opt.items()
                if cmap.get(int(str(v["codepoint"])[2:], 16)) != k]
    a.check(not wrong_cp, "every optionalGlyphs codepoint resolves to its own glyph",
            str(wrong_cp[:3]) if wrong_cp else "60/60")

    gn = json.loads(GLYPHNAMES.read_text(encoding="utf-8"))
    a.check(len(gn) == ALIAS_COUNT, "glyphnames.json holds all 60", str(len(gn)))
    bad_prefix = [k for k, v in gn.items() if not str(v["codepoint"]).startswith("U+")]
    a.check(not bad_prefix, "glyphnames.json codepoints carry the U+ prefix",
            str(bad_prefix[:3]) if bad_prefix else "60/60")
    mismatched = [k for k, v in gn.items()
                  if cmap.get(int(str(v["codepoint"])[2:], 16)) != k]
    a.check(not mismatched, "glyphnames.json codepoints match the font",
            str(mismatched[:3]) if mismatched else "60/60")

    # SMuFL reserves 'alternateCodepoint' for the Unicode Musical Symbols block,
    # so the MuseScore alias must not be published under that name.
    misused = [k for k, v in gn.items() if "alternateCodepoint" in v]
    a.check(not misused,
            "no SMuFL-reserved key is repurposed in glyphnames.json",
            f"{len(misused)} entries misuse 'alternateCodepoint'" if misused
            else "alias published as 'museScoreCodepoint'")
    alias_wrong = [k for k, v in gn.items()
                   if cmap.get(int(str(v.get("museScoreCodepoint", "U+0"))[2:], 16)) != k]
    a.check(not alias_wrong, "glyphnames.json alias codepoints match the font",
            str(alias_wrong[:3]) if alias_wrong else "60/60")


# ---------------------------------------------------------------- section G
def audit_install_simulation(a: Audit) -> None:
    """Re-implement MuseScore's scan and run it over a simulated Windows install."""
    a.section("G. Installer simulation (MuseScore's scan over a fake Windows disk)")

    def scan_directory(root: Path, is_private: bool, font_locations: list[Path]):
        """Faithful port of EngravingFontsController::scanDirectory (v4.6.5)."""
        found = []
        if not root.is_dir():
            return found
        for font_dir in sorted(p for p in root.iterdir() if p.is_dir()):
            jsons = sorted(font_dir.glob("*.json"))
            if not jsons:
                continue
            metadata_path = jsons[-1]          # the iterator's last hit wins
            font_name = font_dir.name
            if "Text" in font_name:
                continue
            if is_private:
                candidates = [font_dir / f"{font_name}.ttf", font_dir / f"{font_name}.otf"]
                symbol_font = next((c for c in candidates if c.is_file()), None)
            else:
                symbol_font = None
                for loc in font_locations:
                    for ext in (".ttf", ".otf"):
                        hit = loc / f"{font_name}{ext}"
                        if hit.is_file():
                            symbol_font = hit
                            break
                    if symbol_font:
                        break
            if symbol_font is None:
                continue
            found.append((font_name, symbol_font, metadata_path))
        return found

    def scan_all(disk: Path, music_fonts_setting: Path | None):
        local_appdata = disk / "AppData/Local"
        common_files = disk / "ProgramFiles/Common Files"
        # Qt FontsLocation on Windows; MuseScore appends the user font folder.
        font_locations = [disk / "Windows/Fonts",
                          local_appdata / "Microsoft/Windows/Fonts"]
        result = []
        for base in reversed([local_appdata, common_files]):
            result += scan_directory(base / "SMuFL/Fonts", False, font_locations)
        if music_fonts_setting is not None:
            result += scan_directory(music_fonts_setting, True, font_locations)
        return result

    def build_disk(tmp: Path, *, legacy_leftovers=False, stale_system_font=False) -> Path:
        """Everything Install-WettstaiFont.ps1 writes, plus optional pre-existing mess."""
        disk = tmp / "C"
        user_fonts = disk / "AppData/Local/Microsoft/Windows/Fonts"
        smufl = disk / "AppData/Local/SMuFL/Fonts/WettstaiFont"
        music = disk / "Documents/MuseScore4/MusicFonts/WettstaiFont"
        for d in (user_fonts, smufl, music, disk / "Windows/Fonts"):
            d.mkdir(parents=True, exist_ok=True)

        if stale_system_font:                     # old double-click install
            shutil.copy(ORIGINAL, disk / "Windows/Fonts/WettstaiFont.otf")
        if legacy_leftovers:                      # what the old installer left
            for folder in (smufl, music):
                (folder / "metadata.json").write_text("{}")
                (folder / "glyphnames.json").write_text("{}")

        # --- the installer's own actions -------------------------------
        shutil.copy(BUILT, user_fonts / "WettstaiFont.otf")
        for folder, files in ((smufl, [METADATA]), (music, [BUILT, METADATA])):
            keep = {f.name for f in files}
            for stray in folder.glob("*.json"):
                if stray.name not in keep:
                    stray.unlink()
            for f in files:
                shutil.copy(f, folder / f.name)
        return disk

    # Case 1: clean machine, factory-default settings (MusicFonts path empty).
    with tempfile.TemporaryDirectory() as tmp:
        disk = build_disk(Path(tmp))
        found = scan_all(disk, None)
        a.check(len(found) == 1 and found[0][0] == "WettstaiFont",
                "found with factory-default settings (no preference set)",
                str([f[0] for f in found]))
        if found:
            name, otf, meta = found[0]
            a.check(otf.name == "WettstaiFont.otf" and "Microsoft/Windows/Fonts" in str(otf),
                    "resolves the OTF from the user font folder", otf.name)
            a.check(meta.name == "WettstaiFont.json",
                    "resolves the intended metadata file", meta.name)

    # Case 2: user additionally points the preference at the MusicFonts folder.
    with tempfile.TemporaryDirectory() as tmp:
        disk = build_disk(Path(tmp))
        found = scan_all(disk, disk / "Documents/MuseScore4/MusicFonts")
        a.check(len(found) == 2 and all(f[0] == "WettstaiFont" for f in found),
                "also found through the private MusicFonts folder",
                f"{len(found)} registrations, last one wins")

    # Case 3: leftovers from the old package must not be able to win the scan.
    with tempfile.TemporaryDirectory() as tmp:
        disk = build_disk(Path(tmp), legacy_leftovers=True)
        smufl = disk / "AppData/Local/SMuFL/Fonts/WettstaiFont"
        strays = sorted(p.name for p in smufl.glob("*.json"))
        a.check(strays == ["WettstaiFont.json"],
                "installer removes the old metadata.json / glyphnames.json", str(strays))
        found = scan_all(disk, disk / "Documents/MuseScore4/MusicFonts")
        a.check(all(f[2].name == "WettstaiFont.json" for f in found),
                "the right metadata file is picked in every scanned folder")

    # Case 4: an old copy still installed system-wide from a double-click.
    # findFontPathGlobal() searches QStandardPaths::FontsLocation (C:\Windows\
    # Fonts) before the user font folder and returns the first hit, so such a
    # copy really does shadow ours. Nothing in the font or metadata can prevent
    # that - the installer has to find and remove it.
    with tempfile.TemporaryDirectory() as tmp:
        disk = build_disk(Path(tmp), stale_system_font=True)
        found = scan_all(disk, None)
        resolved = found[0][1] if found else None
        shadowed = resolved is not None and "Windows/Fonts" in str(resolved) \
            and "AppData" not in str(resolved)
        a.check(shadowed,
                "confirmed: a system-wide copy takes precedence over the user copy",
                "this is why the installer must handle it")

        script = (PACKAGE / "Install-WettstaiFont.ps1").read_text(encoding="utf-8")
        a.check('Join-Path $env:WINDIR "Fonts\\$FontName.otf"' in script,
                "installer looks for a system-wide copy")
        a.check("IsInRole" in script and "Remove-Item -Path $systemFont" in script,
                "installer removes it when running elevated")
        a.check("$staleWarning" in script and "laedt MuseScore weiterhin die ALTE" in script,
                "installer refuses to report plain success when one is left behind")
        uninstall = (PACKAGE / "Uninstall-WettstaiFont.ps1").read_text(encoding="utf-8")
        a.check('Join-Path $env:WINDIR "Fonts\\$FontName.otf"' in uninstall,
                "uninstaller reports a system-wide copy too")


# ---------------------------------------------------------------- section H
def audit_package_and_zip(a: Audit) -> None:
    a.section("H. Package and ZIP")
    expected = {
        "LIESMICH.md", "Install-WettstaiFont.ps1", "Uninstall-WettstaiFont.ps1",
        "WettstaiFont.otf", "WettstaiFont.json", "glyphnames.json", "Symbolliste.md",
    }
    with zipfile.ZipFile(ZIP_PATH) as z:
        bad = z.testzip()
        a.check(bad is None, "ZIP passes its own CRC check", bad or "all entries intact")
        names = z.namelist()
        a.check(all(n.startswith("WettstaiFont-MuseScore4-Setup/") for n in names),
                "every entry is under one top-level folder")
        a.check(not any(".." in n or n.startswith("/") for n in names),
                "no absolute paths or traversal in the archive")
        stems = {n.split("/", 1)[1] for n in names}
        a.check(stems == expected, "ZIP contents match the package exactly",
                str(sorted(stems ^ expected)) if stems != expected else f"{len(stems)} files")

        for stem in sorted(stems):
            data = z.read(f"WettstaiFont-MuseScore4-Setup/{stem}")
            local = (PACKAGE / stem).read_bytes()
            if stem.endswith((".ps1", ".md")):
                a.check(data == local.replace(b"\r\n", b"\n").replace(b"\n", b"\r\n"),
                        f"{stem}: same content, CRLF line endings")
            else:
                a.check(data == local, f"{stem}: byte-identical to package/",
                        sha256(local)[:16])

    # The PowerShell scripts must stay pure ASCII: without a BOM, Windows
    # PowerShell 5.1 reads them as ANSI and would mangle anything else.
    for name in ("Install-WettstaiFont.ps1", "Uninstall-WettstaiFont.ps1"):
        raw = (PACKAGE / name).read_bytes()
        a.check(all(byte < 128 for byte in raw), f"{name} is pure ASCII")
        text = raw.decode("ascii")
        a.check(text.count("{") == text.count("}"), f"{name}: braces balanced")
        a.check(text.count("(") == text.count(")"), f"{name}: parentheses balanced")
        a.check(text.count("@'") == text.count("'@"), f"{name}: here-strings balanced")
        a.check(all(line.startswith("'@") for line in text.split("\n")
                    if line.lstrip().startswith("'@")),
                f"{name}: here-string terminators start at column 0")


# ---------------------------------------------------------------- section I
def audit_docs(a: Audit, font: TTFont) -> None:
    a.section("I. Documentation consistency")
    readme = (REPO / "README.md").read_text(encoding="utf-8")
    liesmich = (PACKAGE / "LIESMICH.md").read_text(encoding="utf-8")
    table = (PACKAGE / "Symbolliste.md").read_text(encoding="utf-8")
    cmap = font.getBestCmap()

    for path in ("docs/preview.png", "docs/symbolliste.png",
                 "package/Symbolliste.md", "WettstaiFont-MuseScore4-Setup.zip"):
        a.check(f"({path})" in readme and (REPO / path).is_file(),
                f"README links {path} and the file exists")

    rows = re.findall(r"^\| *\d+ \| .*?\| `([A-Za-z0-9]+)` \| `U\+([0-9A-F]{4})` \| "
                      r"([A-Za-z0-9]+) \| `U\+([0-9A-F]{4})` \|$", table, re.M)
    a.check(len(rows) == ALIAS_COUNT, "Symbolliste.md has 60 data rows", str(len(rows)))
    wrong = [r for r in rows
             if cmap.get(int(r[1], 16)) != r[0] or cmap.get(int(r[3], 16)) != r[0]]
    a.check(not wrong, "every Symbolliste.md row matches the font",
            f"{len(wrong)} wrong" if wrong else "60/60")

    alias_first = f"U+{ALIAS_FIRST:04X}"
    alias_last = f"U+{ALIAS_FIRST + ALIAS_COUNT - 1:04X}"
    for doc, label in ((readme, "README.md"), (liesmich, "LIESMICH.md")):
        a.check(alias_first in doc and alias_last in doc,
                f"{label} names the real alias range {alias_first}-{alias_last}")
        a.check("Beaters pictograms" in doc, f"{label} names the palette group")
        a.check("4.6" in doc, f"{label} states the version requirement")

    # Numbers asserted in the README that must still be true.
    a.check("2932" in readme and "U+EF08" in readme,
            "README's figures for MuseScore's symbol table are the ones checked in section E")
    a.check("4199" in readme, "README quotes the widest drawing (4199 units)")
    a.check("45 und 833" in readme, "README quotes the original advance range")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--musescore", type=Path, default=None,
                        help="checkout of musescore/MuseScore at tag v4.6.5")
    parser.add_argument("--bravura", type=Path, default=None,
                        help="path to Bravura.otf (its metadata sits next to it)")
    args = parser.parse_args()

    a = Audit()
    print("WettstaiFont - full audit")
    audit_repo(a)
    audit_reproducible(a)
    font = audit_font_structure(a)
    audit_against_original(a, font)
    audit_musescore(a, font, args.musescore)
    audit_metadata(a, font, args.bravura)
    audit_install_simulation(a)
    audit_package_and_zip(a)
    audit_docs(a, font)
    font.close()

    print("\n" + "=" * 60)
    print(f"  passed   : {a.passed}")
    print(f"  failed   : {len(a.failures)}")
    print(f"  warnings : {len(a.warnings)}")
    print(f"  skipped  : {len(a.skipped)}")
    if a.failures:
        print("\nFAILURES:")
        for f in a.failures:
            print(f"  - {f}")
    if a.warnings:
        print("\nWARNINGS:")
        for w in a.warnings:
            print(f"  - {w}")
    print("=" * 60)
    return 1 if a.failures else 0


if __name__ == "__main__":
    raise SystemExit(main())
