# =====================================================================
#  Install-WettstaiFont.ps1
#  Installiert WettstaiFont fuer MuseScore Studio 4.6+ (Windows 10/11)
#
#  Bedienung:
#    Rechtsklick auf diese Datei -> "Mit PowerShell ausfuehren"
#    ODER in PowerShell:
#        Set-ExecutionPolicy -Scope Process Bypass
#        .\Install-WettstaiFont.ps1
#
#  Was das Skript macht und warum (geprueft am Quelltext von
#  MuseScore Studio v4.6.5):
#
#  [1] WettstaiFont.otf wird als Windows-Schriftart fuer den aktuellen
#      Benutzer installiert (kein Admin noetig).
#      EngravingFontsController::findFontPathGlobal() sucht die Datei
#      unter exakt dem Namen "<Ordnername>.otf" in den Schriftarten-
#      Ordnern inkl. %LocalAppData%\Microsoft\Windows\Fonts.
#
#  [2] WettstaiFont.json landet in
#      %LOCALAPPDATA%\SMuFL\Fonts\WettstaiFont\.
#      Das ist der Weg, der OHNE weitere Einstellung funktioniert:
#      EngravingFontsController::scanAllDirectories() durchsucht diesen
#      Ordner bei jedem Start.
#
#  [3] WettstaiFont.otf + .json landen zusaetzlich in
#      Dokumente\MuseScore4\MusicFonts\WettstaiFont\.
#      ACHTUNG: Diesen Ordner durchsucht MuseScore NUR, wenn er in
#      Bearbeiten -> Einstellungen -> Ordner -> "Musiksymbol-Schriftarten"
#      eingetragen ist. Die Einstellung ist ab Werk leer
#      (USER_MUSIC_FONTS_PATH, Standardwert = leerer Pfad). Deshalb ist
#      [2] der Hauptweg und [3] nur die Reserve.
#
#  In jeden Schriftart-Ordner kommt GENAU EINE .json-Datei: MuseScore
#  4.6 nimmt in scanDirectory() irgendeine *.json aus dem Ordner (die
#  letzte, die der Verzeichnis-Iterator liefert). Mehrere JSON-Dateien
#  nebeneinander sind darum ein Gluecksspiel.
# =====================================================================

$ErrorActionPreference = "Stop"

$FontName = "WettstaiFont"

function Write-Step($text)    { Write-Host $text -ForegroundColor Yellow }
function Write-Ok($text)      { Write-Host "   OK  $text" -ForegroundColor Green }
function Write-Info($text)    { Write-Host "   ->  $text" -ForegroundColor Gray }
function Write-Problem($text) { Write-Host "   !!  $text" -ForegroundColor Red }

Write-Host ""
Write-Host "==============================================" -ForegroundColor Cyan
Write-Host " $FontName - Installation fuer MuseScore 4.6+" -ForegroundColor Cyan
Write-Host "==============================================" -ForegroundColor Cyan
Write-Host ""

# ----- Quellen pruefen ------------------------------------------------
$srcDir   = $PSScriptRoot
$otfFile  = Join-Path $srcDir "$FontName.otf"
$jsonFile = Join-Path $srcDir "$FontName.json"

foreach ($f in @($otfFile, $jsonFile)) {
    if (-not (Test-Path $f)) {
        Write-Problem "Datei nicht gefunden: $f"
        Write-Problem "Bitte das ZIP vollstaendig entpacken und das Skript aus dem entpackten Ordner starten."
        Read-Host "Enter zum Beenden"
        exit 1
    }
}

# ----- Laeuft MuseScore noch? ----------------------------------------
$running = Get-Process -Name "MuseScore*" -ErrorAction SilentlyContinue
if ($running) {
    Write-Problem "MuseScore laeuft noch (PID: $($running.Id -join ', '))."
    Write-Problem "Bitte komplett beenden - MuseScore liest Schriftarten nur beim Start."
    $answer = Read-Host "Trotzdem fortfahren? (j/N)"
    if ($answer -ne "j" -and $answer -ne "J") { exit 1 }
    Write-Host ""
}

# ----- Hilfsfunktion: Schriftart-Ordner sauber befuellen --------------
# Legt den Ordner an, entfernt alte JSON-Reste (siehe Kopfkommentar) und
# kopiert die uebergebenen Dateien hinein.
function Set-FontFolder {
    param(
        [string]   $TargetDir,
        [string[]] $Files
    )

    if (-not (Test-Path $TargetDir)) {
        New-Item -ItemType Directory -Path $TargetDir -Force | Out-Null
    }

    $keep = $Files | ForEach-Object { Split-Path $_ -Leaf }
    Get-ChildItem -Path $TargetDir -Filter "*.json" -File -ErrorAction SilentlyContinue |
        Where-Object { $keep -notcontains $_.Name } |
        ForEach-Object {
            Remove-Item $_.FullName -Force
            Write-Info "alte Datei entfernt: $($_.Name)"
        }

    foreach ($f in $Files) {
        Copy-Item -Path $f -Destination (Join-Path $TargetDir (Split-Path $f -Leaf)) -Force
    }
}

# ----- Schritt 0: alte systemweite Installation aufspueren ------------
# Wer die alte Anleitung befolgt und WettstaiFont.otf per Doppelklick mit
# "Fuer alle Benutzer installieren" eingerichtet hat, hat eine Kopie in
# C:\Windows\Fonts. MuseScore findet die ZUERST:
# findFontPathGlobal() geht QStandardPaths::FontsLocation durch (das ist
# C:\Windows\Fonts) und haengt den Benutzer-Ordner erst danach an - der
# erste Treffer gewinnt. Die alte, kaputte Schrift wuerde also weiter
# geladen, egal was dieses Skript in den Benutzer-Ordner schreibt.
Write-Step "[0/3] Nach einer alten systemweiten Installation suchen..."

$systemFont   = Join-Path $env:WINDIR "Fonts\$FontName.otf"
$hklmFontsKey = "HKLM:\SOFTWARE\Microsoft\Windows NT\CurrentVersion\Fonts"
$staleWarning = $false

if (Test-Path $systemFont) {
    $isAdmin = ([Security.Principal.WindowsPrincipal] `
                [Security.Principal.WindowsIdentity]::GetCurrent()
               ).IsInRole([Security.Principal.WindowsBuiltInRole]::Administrator)

    if ($isAdmin) {
        try {
            Add-Type -Name FontApiStale -Namespace Win32 -MemberDefinition @'
                [DllImport("gdi32.dll", CharSet = CharSet.Unicode)]
                public static extern bool RemoveFontResourceW(string lpFileName);
'@ -ErrorAction SilentlyContinue
            [void][Win32.FontApiStale]::RemoveFontResourceW($systemFont)
        } catch { }

        try {
            Remove-Item -Path $systemFont -Force
            if (Test-Path $hklmFontsKey) {
                Get-Item $hklmFontsKey | Select-Object -ExpandProperty Property |
                    Where-Object { $_ -like "$FontName*" } |
                    ForEach-Object { Remove-ItemProperty -Path $hklmFontsKey -Name $_ -Force }
            }
            Write-Ok "alte systemweite Schrift entfernt: $systemFont"
        } catch {
            $staleWarning = $true
            Write-Problem "Alte systemweite Schrift liess sich nicht entfernen: $systemFont"
        }
    } else {
        $staleWarning = $true
        Write-Problem "GEFUNDEN: eine alte Kopie unter $systemFont"
        Write-Problem "MuseScore wuerde DIESE laden, nicht die neue - bitte entfernen:"
        Write-Problem "  Einstellungen -> Personalisierung -> Schriftarten ->"
        Write-Problem "  'WettstaiFont' anklicken -> Deinstallieren"
        Write-Problem "(oder dieses Skript als Administrator erneut ausfuehren)"
        Write-Host ""
    }
} else {
    Write-Ok "keine alte systemweite Installation vorhanden"
}

# ----- Schritt 1: Windows-Schriftart ----------------------------------
Write-Step "[1/3] Schriftart fuer den aktuellen Benutzer installieren..."

$userFontDir = Join-Path $env:LOCALAPPDATA "Microsoft\Windows\Fonts"
if (-not (Test-Path $userFontDir)) {
    New-Item -ItemType Directory -Path $userFontDir -Force | Out-Null
}

$userFontTarget = Join-Path $userFontDir "$FontName.otf"
Copy-Item -Path $otfFile -Destination $userFontTarget -Force

$regPath = "HKCU:\SOFTWARE\Microsoft\Windows NT\CurrentVersion\Fonts"
if (-not (Test-Path $regPath)) {
    New-Item -Path $regPath -Force | Out-Null
}
Set-ItemProperty -Path $regPath -Name "$FontName (OpenType)" -Value $userFontTarget -Type String -Force

# Schrift sofort bekannt machen, damit kein Ab-/Anmelden noetig ist.
try {
    Add-Type -Name FontApi -Namespace Win32 -MemberDefinition @'
        [DllImport("gdi32.dll", CharSet = CharSet.Unicode)]
        public static extern int AddFontResourceW(string lpFileName);
        [DllImport("user32.dll", CharSet = CharSet.Auto)]
        public static extern IntPtr SendMessageTimeout(IntPtr hWnd, uint Msg, IntPtr wParam,
            IntPtr lParam, uint fuFlags, uint uTimeout, out IntPtr lpdwResult);
'@ -ErrorAction Stop
    [void][Win32.FontApi]::AddFontResourceW($userFontTarget)
    $result = [IntPtr]::Zero
    # HWND_BROADCAST = 0xFFFF, WM_FONTCHANGE = 0x001D, SMTO_ABORTIFHUNG = 0x0002
    [void][Win32.FontApi]::SendMessageTimeout([IntPtr]0xFFFF, 0x001D, [IntPtr]::Zero,
        [IntPtr]::Zero, 0x0002, 1000, [ref]$result)
} catch {
    Write-Info "Schrift-Cache konnte nicht sofort aktualisiert werden - notfalls neu anmelden."
}

Write-Ok "$FontName.otf -> $userFontTarget"

# ----- Schritt 2: globaler SMuFL-Ordner (Hauptweg) --------------------
Write-Step "[2/3] SMuFL-Metadaten ablegen (dieser Weg braucht keine Einstellung)..."

$smuflDir = Join-Path $env:LOCALAPPDATA "SMuFL\Fonts\$FontName"
Set-FontFolder -TargetDir $smuflDir -Files @($jsonFile)
Write-Ok "$FontName.json -> $smuflDir"

# ----- Schritt 3: privater MusicFonts-Ordner (Reserve) ----------------
Write-Step "[3/3] Kopie im MuseScore-MusicFonts-Ordner anlegen..."

$musicFontsRoot = Join-Path ([Environment]::GetFolderPath('MyDocuments')) "MuseScore4\MusicFonts"
$musicFontsDir  = Join-Path $musicFontsRoot $FontName
Set-FontFolder -TargetDir $musicFontsDir -Files @($otfFile, $jsonFile)
Write-Ok "$FontName.otf + .json -> $musicFontsDir"

Write-Host ""
if ($staleWarning) {
    Write-Host "==============================================" -ForegroundColor Red
    Write-Host " Installation abgeschlossen - ABER:"           -ForegroundColor Red
    Write-Host "==============================================" -ForegroundColor Red
    Write-Host ""
    Write-Problem "Unter $systemFont liegt noch die alte Schrift."
    Write-Problem "Solange sie dort liegt, laedt MuseScore weiterhin die ALTE"
    Write-Problem "Version und nichts von dieser Reparatur ist sichtbar."
    Write-Problem "Bitte zuerst entfernen (siehe oben), dann MuseScore starten."
    Write-Host ""
} else {
    Write-Host "==============================================" -ForegroundColor Green
    Write-Host " Installation abgeschlossen"                    -ForegroundColor Green
    Write-Host "==============================================" -ForegroundColor Green
    Write-Host ""
}
Write-Host "So geht es weiter:" -ForegroundColor Cyan
Write-Host "  1. MuseScore Studio KOMPLETT beenden (auch im Infobereich"
Write-Host "     neben der Uhr nachsehen) und neu starten."
Write-Host "  2. Ansicht -> Master-Palette (Umschalt+F9) -> Symbole."
Write-Host "  3. Oben im Auswahlfeld 'WettstaiFont' waehlen."
Write-Host "  4. Links die Gruppe 'Beaters pictograms' anklicken."
Write-Host "     Dort stehen alle 60 Wettstai-Symbole. Der Eintrag heisst"
Write-Host "     auch auf Deutsch englisch - MuseScore uebersetzt ihn nicht."
Write-Host ""
Write-Host "  Die Musiksymbol-Schriftart des Notenblatts muss dafuer NICHT"
Write-Host "  umgestellt werden - Leland/Bravura bleibt fuer die normale"
Write-Host "  Notation zustaendig."
Write-Host ""
Write-Host "  Optional (Reserve-Weg aus Schritt 3 aktivieren):" -ForegroundColor Gray
Write-Host "  Bearbeiten -> Einstellungen -> Ordner ->" -ForegroundColor Gray
Write-Host "  'Musiksymbol-Schriftarten' auf diesen Pfad setzen:" -ForegroundColor Gray
Write-Host "  $musicFontsRoot" -ForegroundColor Gray
Write-Host ""
Read-Host "Enter zum Beenden"
