# WettstaiFont für MuseScore 4 – Installation & Benutzung

Diese Anleitung erklärt, wie du die `WettstaiFont` (Basler Trommel-Notation / „Hieroglyphen-Schrift") in MuseScore 4 unter Windows 11 installierst und benutzt.

---

## ⚠️ Wichtigste Voraussetzung

**Vollständige Drittanbieter-SMuFL-Unterstützung gibt es erst ab MuseScore 4.6** (Oktober 2025). Auf älteren 4.x-Versionen wird die Schrift im Style-Dialog möglicherweise gar nicht erscheinen oder die Glyphen werden falsch dargestellt.

Prüfe deine Version unter **Hilfe → Über MuseScore**. Wenn du eine ältere Version hast: Aktualisiere auf 4.6 oder neuer, bevor du weitermachst.

---

## 📦 Inhalt dieses Pakets

| Datei | Zweck |
|-------|-------|
| `WettstaiFont.otf` | Die eigentliche Schriftdatei (unverändert) |
| `WettstaiFont.json` | SMuFL-Metadaten mit korrigierten `engravingDefaults` |
| `glyphnames.json` | Glyph-Namen-Mapping (60 Wettstai-Symbole) |
| `Install-WettstaiFont.ps1` | Automatische Installation |
| `Uninstall-WettstaiFont.ps1` | Entfernt alles wieder |
| `README.md` | Diese Anleitung |

---

## 🚀 Installation (empfohlen: automatisch)

1. **Schließe MuseScore 4 komplett.** Auch im System-Tray rechtsklicken → Beenden.
2. **Rechtsklick** auf `Install-WettstaiFont.ps1` → **„Mit PowerShell ausführen"**.
3. Falls eine Sicherheitsabfrage kommt, „Ja" / „Trotzdem ausführen" anklicken.
4. Das Skript installiert die Schrift an drei Stellen:
   - Als Windows-Schriftart (User-Scope, kein Admin nötig)
   - In `Dokumente\MuseScore4\MusicFonts\WettstaiFont\` (für MuseScore)
   - In `%LOCALAPPDATA%\SMuFL\Fonts\WettstaiFont\` (für SMuFL-Standard)

Falls PowerShell die Skript-Ausführung blockiert:

```powershell
Set-ExecutionPolicy -Scope Process Bypass
.\Install-WettstaiFont.ps1
```

---

## 🛠 Installation (manuell, falls du es lieber selbst machen willst)

### Schritt 1: Schriftart in Windows installieren

Doppelklick auf `WettstaiFont.otf` → Button „Installieren". Damit ist die Schrift in jedem Programm verfügbar.

### Schritt 2: SMuFL-Metadaten für MuseScore ablegen

Lege diesen Ordner an:

```
C:\Users\<DEIN-NAME>\Documents\MuseScore4\MusicFonts\WettstaiFont\
```

Kopiere dort hinein:

```
WettstaiFont.otf
WettstaiFont.json
```

> **Wichtig:** Der Ordnername muss **exakt** `WettstaiFont` heißen (Groß-/Kleinschreibung beachten, gleicher Name wie die Schrift).

### Schritt 3 (optional): SMuFL-Systempfad

Damit auch andere Notationssoftware (z. B. Dorico, Finale 27) die Schrift findet, lege zusätzlich an:

```
C:\Users\<DEIN-NAME>\AppData\Local\SMuFL\Fonts\WettstaiFont\WettstaiFont.json
```

Den `AppData`-Ordner erreichst du über `Win+R` → `%LOCALAPPDATA%` eingeben.

---

## ✅ Prüfen, ob es geklappt hat

1. MuseScore 4 **neu starten** (vollständiger Neustart, kein Reload).
2. **Format → Stil… → Notensatz** (engl.: Format → Style → Score).
3. Im Dropdown **„Musiksymbol-Schriftart"** (engl. Musical Symbol Font) sollte `WettstaiFont` jetzt auftauchen.

Wenn `WettstaiFont` dort **nicht** erscheint:

- Hast du wirklich MuseScore 4.6 oder neuer?
- Ist die JSON-Datei im richtigen Ordner und heißt exakt `WettstaiFont.json` (nicht `WettstaiFont_metadata.json`)?
- Hast du MuseScore 4 komplett neu gestartet (inkl. Tray-Symbol)?

---

## 🥁 Wie du die Wettstai-Symbole im Score einfügst

Wichtig zu verstehen: Deine `WettstaiFont` enthält **76 Glyphen** – das sind v. a. die 60 Wettstai-Trommel-Symbole im SMuFL-Optional-Bereich (`U+F400` bis `U+F43B`). Es ist **keine vollständige Ersatz-Notenschrift** wie Bravura. Das heißt:

- Standard-Notation (Noten, Pausen, Vorzeichen, Schlüssel …) zeichnet MuseScore weiterhin mit Bravura (Fallback).
- Deine Wettstai-Symbole fügst du als **Einzel-Symbole** über die Master-Palette ein.

### Symbole einfügen – Schritt für Schritt

1. **Master-Palette öffnen:** `Ansicht → Master-Palette` oder `Umschalt + F9`.
2. Links auf **„Symbole"** klicken.
3. Oben im Dropdown **„Font"** die Schriftart **`WettstaiFont`** wählen.
4. Du siehst alle 60 Wettstai-Glyphen (im Bereich `U+F400+`).
5. Markiere im Score eine Note (oder eine Pause), und doppelklicke auf das gewünschte Symbol in der Palette. Das Symbol wird an die Note angeheftet.
6. **Mit Maus oder Pfeiltasten verschieben** zur exakten Positionierung.

### Eigene Palette anlegen (Tipp für intensive Nutzung)

Damit du nicht jedes Mal durch die Master-Palette navigieren musst:

1. **Ansicht → Paletten** öffnen (links).
2. Unten auf das **„+"** → „Neue Palette erstellen" → Name: z. B. „Wettstai".
3. Aus der Master-Palette (Symbole, `WettstaiFont`) die häufig genutzten Symbole per **Drag & Drop** in deine neue Palette ziehen.
4. Diese Palette bleibt dauerhaft sichtbar und steht in jedem Score sofort zur Verfügung.

---

## 📋 Liste der Wettstai-Glyphen

Die Schrift enthält folgende 60 Trommel-Symbole (Codepoint → Name):

| Codepoint | Glyph-Name | Bedeutung |
|-----------|-----------|-----------|
| U+F400 | bataflafla | Bataflafla |
| U+F401 / F402 | bataflaLinks / bataflaRechts | Batafla L/R |
| U+F403 | coupeDeCharge | Coupe de charge |
| U+F404 / F405 | doppelDWLinks / doppelDWRechts | Doppel-Doppelschlag L/R |
| U+F406 | double2 | Double (Variante 2) |
| U+F407 / F408 | doubleLinks / doubleRechts | Double L/R |
| U+F409 / F40A | dupfLinks / dupfRechts | Dupf L/R |
| U+F40B / F40C | endstraichLinks / endstraichRechts | Endstreich L/R |
| U+F40D / F40E | maermeliLinks / maermeliRechts | Märmeli L/R |
| U+F40F | muehlerad | Mühlerad |
| U+F410 / F411 | paradiddleLinks / paradiddleRechts | Paradiddle L/R |
| U+F412 – F427 | ruf3 … ruf21 (L/R) | Ruf 3, 4, 5, 7, 9, 11, 13, 15, 17, 19, 21 |
| U+F428 / F429 | schlepp3erliLinks / schlepp3erliRechts | Schlepp-3erli L/R |
| U+F42A | schlepp5er | Schlepp-5er |
| U+F42B | schlepp9er | Schlepp-9er |
| U+F42C / F42D | schleppLinks / schleppRechts | Schlepp L/R |
| U+F42E / F42F | straich3Links / straich3Rechts | Straich-3 L/R |
| U+F430 / F431 | udoppelDWLinks / uDoppelDWRechts | U-Doppel L/R |
| U+F432 / F433 | uEndstraichLinks / uEndstraichRechts | U-Endstreich L/R |
| U+F434 / F435 | ruf5PunktiertLinks / ruf5PunktiertRechts | Ruf 5 punktiert L/R |
| U+F436 / F437 | wert8el / wert8el2 | Notenwert Achtel (2 Varianten) |
| U+F438 / F439 | wert16tel / wert16tel2 | Notenwert Sechzehntel (2 Varianten) |
| U+F43A / F43B | wertQuintole / wertQuintole2 | Notenwert Quintole (2 Varianten) |

---

## 🧪 Bekannte Einschränkungen

1. **Keine vollständige SMuFL-Abdeckung.** Wenn du die Schrift unter `Format → Stil → Notensatz` als globale Music-Font wählst, werden die Standard-Glyphen (Notenköpfe, Schlüssel, Pausen …) automatisch aus Bravura nachgeladen (Fallback). Das ist normal und gewollt.

2. **`engravingDefaults`** sind auf Bravura-Standardwerte gesetzt. Falls deine Schrift optisch andere Linienstärken braucht, kannst du die Werte in `WettstaiFont.json` anpassen und das Install-Skript neu ausführen.

3. **Keine `glyphsWithAnchors`.** Wettstai-Symbole haben keine SMuFL-Anker (für Notenkopf-Cutouts, Stem-Connections etc.). Sie werden als freistehende Symbole eingefügt – das ist für deinen Use-Case (manuelles Anheften an Noten) genau richtig.

4. **Drumset-Definition als nächster Schritt:** Wenn du später ganze Stücke in Wettstai-Notation schreiben willst (statt nur einzelne Symbole einzufügen), wäre der nächste sinnvolle Schritt eine eigene **Drumset-Definition (.drm)** mit den Wettstai-Symbolen als Notenkopf-Ersatz. Sag mir Bescheid, wenn ich das auch noch bauen soll.

---

## 🐛 Troubleshooting

**Problem: Schrift erscheint nicht in MuseScore.**
- Version prüfen (muss ≥ 4.6 sein).
- MuseScore wirklich komplett geschlossen vor Installation?
- Tray-Symbol prüfen (Pfeil neben der Uhr) – manchmal läuft MuseScore dort weiter.
- `Documents\MuseScore4\MusicFonts\WettstaiFont\WettstaiFont.json` wirklich vorhanden?

**Problem: Glyphen werden als Rechtecke / leere Kästchen angezeigt.**
- Die OTF-Datei ist nicht als Windows-Schriftart installiert. Doppelklick auf die OTF → „Installieren".

**Problem: PowerShell-Skript wird blockiert.**
- Im PowerShell-Fenster ausführen: `Set-ExecutionPolicy -Scope Process Bypass`, dann das Skript starten.

**Problem: Glyphen werden in falscher Größe / Position angezeigt.**
- Beim ersten Test in einem leeren Score versuchen. Das Symbol per Mausklick auswählen und mit den Pfeiltasten korrekt positionieren. Bei systematisch falscher Größe müssen die `glyphAdvanceWidths` oder `glyphBBoxes` in der JSON neu kalibriert werden.

---

## 📚 Weiterführende Links

- SMuFL-Spezifikation: <https://w3c.github.io/smufl/latest/>
- MuseScore-Handbuch (Music Fonts): <https://handbook.musescore.org/appendix/music-fonts>
- Wettstai-Notation Basel-Trommel: Suche nach „Berger Notation" oder „Wettstai".

---

*Erstellt für MuseScore 4.6+ unter Windows 11.*
