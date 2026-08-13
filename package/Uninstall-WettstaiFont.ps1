# =====================================================================
#  Uninstall-WettstaiFont.ps1
#  Entfernt alles, was Install-WettstaiFont.ps1 angelegt hat.
#
#  Bedienung:
#    Rechtsklick -> "Mit PowerShell ausfuehren"
#    ODER:  Set-ExecutionPolicy -Scope Process Bypass
#           .\Uninstall-WettstaiFont.ps1
# =====================================================================

$ErrorActionPreference = "Stop"

$FontName = "WettstaiFont"

Write-Host ""
Write-Host "==============================================" -ForegroundColor Cyan
Write-Host " $FontName - Deinstallation"                    -ForegroundColor Cyan
Write-Host "==============================================" -ForegroundColor Cyan
Write-Host ""

$running = Get-Process -Name "MuseScore*" -ErrorAction SilentlyContinue
if ($running) {
    Write-Host "   !!  MuseScore laeuft noch - bitte erst beenden." -ForegroundColor Red
    $answer = Read-Host "Trotzdem fortfahren? (j/N)"
    if ($answer -ne "j" -and $answer -ne "J") { exit 1 }
}

$userFontTarget = Join-Path $env:LOCALAPPDATA "Microsoft\Windows\Fonts\$FontName.otf"
$smuflDir       = Join-Path $env:LOCALAPPDATA "SMuFL\Fonts\$FontName"
$musicFontsDir  = Join-Path ([Environment]::GetFolderPath('MyDocuments')) "MuseScore4\MusicFonts\$FontName"
$regPath        = "HKCU:\SOFTWARE\Microsoft\Windows NT\CurrentVersion\Fonts"

# Schrift aus dem laufenden System abmelden, sonst bleibt die Datei gesperrt.
try {
    Add-Type -Name FontApiUninstall -Namespace Win32 -MemberDefinition @'
        [DllImport("gdi32.dll", CharSet = CharSet.Unicode)]
        public static extern bool RemoveFontResourceW(string lpFileName);
'@ -ErrorAction Stop
    if (Test-Path $userFontTarget) {
        [void][Win32.FontApiUninstall]::RemoveFontResourceW($userFontTarget)
    }
} catch { }

foreach ($path in @($userFontTarget, $smuflDir, $musicFontsDir)) {
    if (Test-Path $path) {
        try {
            Remove-Item -Path $path -Recurse -Force
            Write-Host "   OK  entfernt: $path" -ForegroundColor Green
        } catch {
            Write-Host "   !!  nicht entfernt (evtl. noch in Benutzung): $path" -ForegroundColor Red
        }
    } else {
        Write-Host "   --  nicht vorhanden: $path" -ForegroundColor Gray
    }
}

if (Test-Path $regPath) {
    $entry = "$FontName (OpenType)"
    if (Get-ItemProperty -Path $regPath -Name $entry -ErrorAction SilentlyContinue) {
        Remove-ItemProperty -Path $regPath -Name $entry -Force
        Write-Host "   OK  Registry-Eintrag entfernt: $entry" -ForegroundColor Green
    } else {
        Write-Host "   --  kein Registry-Eintrag vorhanden" -ForegroundColor Gray
    }
}

Write-Host ""
Write-Host "Fertig. MuseScore neu starten, damit die Aenderung greift." -ForegroundColor Green
Write-Host ""
Read-Host "Enter zum Beenden"
