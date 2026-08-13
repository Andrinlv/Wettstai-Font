# WettstaiFont für MuseScore Studio – Kurzanleitung

Basler Trommel-Notation („Wettstai“ / Hieroglyphen-Schrift) als Musiksymbol-Schriftart.

**Voraussetzung: MuseScore Studio 4.6 oder neuer.** Ältere 4.x-Versionen können
gar keine fremden SMuFL-Schriften laden. Version prüfen unter *Hilfe → Über MuseScore*.

---

## 1. Installieren

1. MuseScore **komplett beenden** (auch im Infobereich neben der Uhr nachschauen).
2. Dieses ZIP vollständig entpacken.
3. Rechtsklick auf `Install-WettstaiFont.ps1` → **„Mit PowerShell ausführen“**.

Falls PowerShell blockiert:

```powershell
Set-ExecutionPolicy -Scope Process Bypass
.\Install-WettstaiFont.ps1
```

4. MuseScore neu starten.

Rückgängig machen: `Uninstall-WettstaiFont.ps1` auf dieselbe Weise starten.

---

## 2. Symbole einfügen

1. **Ansicht → Master-Palette** (`Umschalt + F9`).
2. Links **„Symbole“** wählen.
3. Oben im Auswahlfeld **Font: `WettstaiFont`** einstellen.
4. Links in der Liste die Gruppe **„Beaters pictograms“** anklicken.
   **Dort stehen alle 60 Wettstai-Symbole.** Der Eintrag heisst auch in einer deutschen
   Oberfläche englisch – MuseScore übersetzt die Symbolgruppen nicht.
5. Im Notenblatt eine Note anklicken, dann in der Palette auf das Symbol
   doppelklicken. Mit den Pfeiltasten fein positionieren.

> **Warum „Beaters pictograms“?** MuseScore kennt nur seine eigene, fest
> eingebaute Symbolliste. Der SMuFL-Bereich ab `U+F400`, in dem eigene Symbole
> laut Standard liegen, kommt darin nicht vor – Symbole dort sind für MuseScore
> unsichtbar. Damit die Wettstai-Zeichen überhaupt benutzbar sind, liegen sie
> zusätzlich auf `U+E770`–`U+E7AB`, einem Bereich, den MuseScore kennt. Welches
> Feld welches Symbol ist, steht in `Symbolliste.md` – du siehst in der Palette
> aber ohnehin direkt die Wettstai-Zeichen.

**Die Musiksymbol-Schriftart des Notenblatts muss dafür nicht umgestellt werden.**
Noten, Schlüssel und Pausen kommen weiter aus Leland bzw. Bravura; jedes
eingefügte Symbol merkt sich selbst, dass es aus `WettstaiFont` stammt.

### Eigene Palette anlegen

Damit du nicht jedes Mal durch die Master-Palette navigieren musst:

1. **Ansicht → Paletten**, unten auf **„+“ → Neue Palette erstellen**, Name z. B. „Wettstai“.
2. Symbole aus der Master-Palette per **Drag & Drop** hineinziehen.

---

## 3. Wenn `WettstaiFont` nicht im Auswahlfeld auftaucht

| Prüfen | |
|---|---|
| Version | MuseScore Studio **4.6+**? |
| Neustart | MuseScore wirklich komplett beendet und neu gestartet? |
| Metadaten | Gibt es `%LOCALAPPDATA%\SMuFL\Fonts\WettstaiFont\WettstaiFont.json`? |
| Schriftdatei | Gibt es `%LOCALAPPDATA%\Microsoft\Windows\Fonts\WettstaiFont.otf`? |

Beide Dateien müssen **exakt** so heißen – MuseScore sucht die Schriftdatei unter
dem Namen des Ordners, in dem die Metadaten liegen.

Werden Symbole als leere Rechtecke gezeigt, ist die OTF nicht als Windows-Schriftart
installiert: Doppelklick auf `WettstaiFont.otf` → *Installieren*.

---

## 4. Inhalt

| Datei | Zweck |
|---|---|
| `WettstaiFont.otf` | Schriftdatei (60 Symbole, Zeichnungen unverändert) |
| `WettstaiFont.json` | SMuFL-Metadaten |
| `glyphnames.json` | Namen und Codepoints, für andere Programme und zum Nachschlagen |
| `Symbolliste.md` | Tabelle aller 60 Symbole mit Codepoints |
| `Install-WettstaiFont.ps1` | Installation |
| `Uninstall-WettstaiFont.ps1` | Deinstallation |

Ausführliche Hintergründe, was am ursprünglichen Paket nicht funktioniert hat:
siehe `README.md` im Projekt-Repository.
