"""Shared glyph inventory for the WettstaiFont build tools.

The Wettstai symbols live in the SMuFL "optional glyph" range (U+F400+).
MuseScore Studio cannot reach that range at all: its symbol universe is baked
into the binary (``fonts/smufl/glyphnames.json`` + ``fonts/smufl/ranges.json``,
which stop at U+EF08), and it ignores the ``optionalGlyphs`` block of a
third-party font's metadata file. Every Wettstai symbol therefore also gets an
alias inside a codepoint block MuseScore does know, so the symbols show up in
Master Palette -> Symbols and can be inserted into a score.

The alias block is "Beaters pictograms" (U+E770-U+E7EF, 128 slots in MuseScore's
own symbol table). It is percussion-adjacent, big enough, and its glyphs
(timpani/xylophone/bass-drum mallets) are never needed in a Basel drum score.
"""

# (codepoint in the SMuFL optional range, glyph name, German description)
# Order is the canonical order of the font and drives the alias assignment.
WETTSTAI_GLYPHS = [
    (0xF400, "bataflafla",          "Bataflafla"),
    (0xF401, "bataflaLinks",        "Batafla links"),
    (0xF402, "bataflaRechts",       "Batafla rechts"),
    (0xF403, "coupeDeCharge",       "Coupe de charge"),
    (0xF404, "doppelDWLinks",       "Doppel-Doppelschlag links"),
    (0xF405, "doppelDWRechts",      "Doppel-Doppelschlag rechts"),
    (0xF406, "double2",             "Double (Variante 2)"),
    (0xF407, "doubleLinks",         "Double links"),
    (0xF408, "doubleRechts",        "Double rechts"),
    (0xF409, "dupfLinks",           "Dupf links"),
    (0xF40A, "dupfRechts",          "Dupf rechts"),
    (0xF40B, "endstraichLinks",     "Endstraich links"),
    (0xF40C, "endstraichRechts",    "Endstraich rechts"),
    (0xF40D, "maermeliLinks",       "Maermeli links"),
    (0xF40E, "maermeliRechts",      "Maermeli rechts"),
    (0xF40F, "muehlerad",           "Muehlerad"),
    (0xF410, "paradiddleLinks",     "Paradiddle links"),
    (0xF411, "paradiddleRechts",    "Paradiddle rechts"),
    (0xF412, "ruf3Links",           "Ruf 3 links"),
    (0xF413, "ruf3Rechts",          "Ruf 3 rechts"),
    (0xF414, "ruf4Links",           "Ruf 4 links"),
    (0xF415, "ruf4Rechts",          "Ruf 4 rechts"),
    (0xF416, "ruf5Links",           "Ruf 5 links"),
    (0xF417, "ruf5Rechts",          "Ruf 5 rechts"),
    (0xF418, "ruf7Links",           "Ruf 7 links"),
    (0xF419, "ruf7Rechts",          "Ruf 7 rechts"),
    (0xF41A, "ruf9Links",           "Ruf 9 links"),
    (0xF41B, "ruf9Rechts",          "Ruf 9 rechts"),
    (0xF41C, "ruf11Links",          "Ruf 11 links"),
    (0xF41D, "ruf11Rechts",         "Ruf 11 rechts"),
    (0xF41E, "ruf13Links",          "Ruf 13 links"),
    (0xF41F, "ruf13Rechts",         "Ruf 13 rechts"),
    (0xF420, "ruf15Links",          "Ruf 15 links"),
    (0xF421, "ruf15Rechts",         "Ruf 15 rechts"),
    (0xF422, "ruf17Links",          "Ruf 17 links"),
    (0xF423, "ruf17Rechts",         "Ruf 17 rechts"),
    (0xF424, "ruf19Links",          "Ruf 19 links"),
    (0xF425, "ruf19Rechts",         "Ruf 19 rechts"),
    (0xF426, "ruf21Rechts",         "Ruf 21 rechts"),
    (0xF427, "ruf21Links",          "Ruf 21 links"),
    (0xF428, "schlepp3erliLinks",   "Schlepp-3erli links"),
    (0xF429, "schlepp3erliRechts",  "Schlepp-3erli rechts"),
    (0xF42A, "schlepp5er",          "Schlepp-5er"),
    (0xF42B, "schlepp9er",          "Schlepp-9er"),
    (0xF42C, "schleppLinks",        "Schlepp links"),
    (0xF42D, "schleppRechts",       "Schlepp rechts"),
    (0xF42E, "straich3Links",       "Straich-3 links"),
    (0xF42F, "straich3Rechts",      "Straich-3 rechts"),
    (0xF430, "udoppelDWLinks",      "U-Doppel-Doppelschlag links"),
    (0xF431, "uDoppelDWRechts",     "U-Doppel-Doppelschlag rechts"),
    (0xF432, "uEndstraichLinks",    "U-Endstraich links"),
    (0xF433, "uEndstraichRechts",   "U-Endstraich rechts"),
    (0xF434, "ruf5PunktiertLinks",  "Ruf 5 punktiert links"),
    (0xF435, "ruf5PunktiertRechts", "Ruf 5 punktiert rechts"),
    (0xF436, "wert8el",             "Notenwert Achtel"),
    (0xF437, "wert8el2",            "Notenwert Achtel (Variante 2)"),
    (0xF438, "wert16tel",           "Notenwert Sechzehntel"),
    (0xF439, "wert16tel2",          "Notenwert Sechzehntel (Variante 2)"),
    (0xF43A, "wertQuintole",        "Notenwert Quintole"),
    (0xF43B, "wertQuintole2",       "Notenwert Quintole (Variante 2)"),
]

# First codepoint of the MuseScore-visible alias block ("Beaters pictograms").
ALIAS_BLOCK_START = 0xE770
ALIAS_BLOCK_END = 0xE7EF  # inclusive, per SMuFL / MuseScore ranges.json

# SMuFL glyph names of the alias slots, in codepoint order starting at E770.
# These are the names MuseScore shows in the Master Palette, so the docs need
# them to let the user identify a symbol without counting cells.
ALIAS_SMUFL_NAMES = [
    "pictBeaterSoftXylophoneUp", "pictBeaterSoftXylophoneDown",
    "pictBeaterSoftXylophoneRight", "pictBeaterSoftXylophoneLeft",
    "pictBeaterMediumXylophoneUp", "pictBeaterMediumXylophoneDown",
    "pictBeaterMediumXylophoneRight", "pictBeaterMediumXylophoneLeft",
    "pictBeaterHardXylophoneUp", "pictBeaterHardXylophoneDown",
    "pictBeaterHardXylophoneRight", "pictBeaterHardXylophoneLeft",
    "pictBeaterWoodXylophoneUp", "pictBeaterWoodXylophoneDown",
    "pictBeaterWoodXylophoneRight", "pictBeaterWoodXylophoneLeft",
    "pictBeaterSoftGlockenspielUp", "pictBeaterSoftGlockenspielDown",
    "pictBeaterSoftGlockenspielRight", "pictBeaterSoftGlockenspielLeft",
    "pictBeaterHardGlockenspielUp", "pictBeaterHardGlockenspielDown",
    "pictBeaterHardGlockenspielRight", "pictBeaterHardGlockenspielLeft",
    "pictBeaterSoftTimpaniUp", "pictBeaterSoftTimpaniDown",
    "pictBeaterSoftTimpaniRight", "pictBeaterSoftTimpaniLeft",
    "pictBeaterMediumTimpaniUp", "pictBeaterMediumTimpaniDown",
    "pictBeaterMediumTimpaniRight", "pictBeaterMediumTimpaniLeft",
    "pictBeaterHardTimpaniUp", "pictBeaterHardTimpaniDown",
    "pictBeaterHardTimpaniRight", "pictBeaterHardTimpaniLeft",
    "pictBeaterWoodTimpaniUp", "pictBeaterWoodTimpaniDown",
    "pictBeaterWoodTimpaniRight", "pictBeaterWoodTimpaniLeft",
    "pictBeaterSoftBassDrumUp", "pictBeaterSoftBassDrumDown",
    "pictBeaterMediumBassDrumUp", "pictBeaterMediumBassDrumDown",
    "pictBeaterHardBassDrumUp", "pictBeaterHardBassDrumDown",
    "pictBeaterMetalBassDrumUp", "pictBeaterMetalBassDrumDown",
    "pictBeaterDoubleBassDrumUp", "pictBeaterDoubleBassDrumDown",
    "pictBeaterSoftYarnUp", "pictBeaterSoftYarnDown",
    "pictBeaterSoftYarnRight", "pictBeaterSoftYarnLeft",
    "pictBeaterMediumYarnUp", "pictBeaterMediumYarnDown",
    "pictBeaterMediumYarnRight", "pictBeaterMediumYarnLeft",
    "pictBeaterHardYarnUp", "pictBeaterHardYarnDown",
]

# Placeholder glyphs in the original font: ten identical filled rectangles
# sitting on real SMuFL codepoints (clefs, time signatures, black notehead).
# Because the glyphs *exist*, MuseScore never falls back to Bravura for them and
# renders black boxes instead of clefs/noteheads. They are dropped.
PLACEHOLDER_GLYPHS = [
    "uniE000", "uniE001", "uniE002",
    "gClef", "cClef", "fClef",
    "timeSig0", "timeSig1", "timeSig2",
    "noteheadBlack",
]

# The original font also mapped the six "Wert" (note value) marks onto the SMuFL
# flag slots U+E240-U+E245 (flag8thUp/Down, flag16thUp/Down, flag32ndUp/Down).
# They are byte-identical copies of wert8el/wert16tel/wertQuintole, just shifted
# vertically. Keeping them replaces every eighth/sixteenth/thirty-second flag in
# a score with a thin dotted vertical line as soon as WettstaiFont is chosen as
# the score's musical symbol font. They are dropped; the same shapes stay
# reachable as regular Wettstai symbols.
FLAG_OVERRIDE_GLYPHS = [
    "uniE240", "uniE241", "uniE242", "uniE243", "uniE244", "uniE245",
]

FONT_NAME = "WettstaiFont"
FONT_VERSION = "2.0.0"
UNITS_PER_EM = 1000
# SMuFL: one staff space is a quarter of the em.
STAFF_SPACE = UNITS_PER_EM / 4.0
# Right sidebearing added to the ink extent when repairing advance widths.
RIGHT_SIDEBEARING = 30


def alias_codepoint(index: int) -> int:
    """Alias codepoint for the index-th Wettstai glyph."""
    cp = ALIAS_BLOCK_START + index
    if cp > ALIAS_BLOCK_END:
        raise ValueError(f"alias block overflow at index {index}")
    return cp


def glyph_rows():
    """Yield (index, optional_codepoint, alias_codepoint, name, description, smufl_alias_name)."""
    for i, (cp, name, desc) in enumerate(WETTSTAI_GLYPHS):
        yield i, cp, alias_codepoint(i), name, desc, ALIAS_SMUFL_NAMES[i]
