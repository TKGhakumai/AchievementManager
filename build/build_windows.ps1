$ErrorActionPreference = 'Stop'
Set-Location (Resolve-Path (Join-Path $PSScriptRoot '..'))
# Windows Python 3.12 is recommended for reproducible PyQt5/PyInstaller builds.
if (-not (Test-Path '.venv/Scripts/python.exe')) {
    py -3.12 -m venv .venv
    if ($LASTEXITCODE -ne 0) { throw 'Python 3.12 is required for the build. Install it or use GitHub Actions.' }
}
$python = '.venv/Scripts/python.exe'
& $python -m pip install --upgrade pip
if ($LASTEXITCODE -ne 0) { throw 'pip upgrade failed' }
& $python -m pip install -r requirements.txt
if ($LASTEXITCODE -ne 0) { throw 'dependency installation failed' }
& $python -m PyInstaller --noconfirm --clean --windowed --onedir --name AchievementManager `
    --collect-all PyQt5.QtMultimedia --collect-submodules achievement_core `
    --add-data "app_config.json;." --hidden-import keyring.backends.Windows main.py
if ($LASTEXITCODE -ne 0) { throw 'PyInstaller failed' }
if (-not (Test-Path 'dist/AchievementManager/AchievementManager.exe')) { throw 'EXE not found' }
Write-Host 'Built: dist/AchievementManager/AchievementManager.exe'
