$ErrorActionPreference = 'Stop'
Set-Location (Resolve-Path (Join-Path $PSScriptRoot '..'))
if (-not (Test-Path '.venv/Scripts/python.exe')) { py -3 -m venv .venv }
$python = '.venv/Scripts/python.exe'
& $python -m pip install --upgrade pip
& $python -m pip install -r requirements.txt
& $python -m PyInstaller --noconfirm --clean --windowed --onedir --name AchievementManager --collect-all PyQt5.QtMultimedia --add-data "app_config.json;." --hidden-import keyring.backends.Windows main.py
if ($LASTEXITCODE -ne 0) { throw 'PyInstaller failed' }
Write-Host 'Built: dist/AchievementManager/AchievementManager.exe'
