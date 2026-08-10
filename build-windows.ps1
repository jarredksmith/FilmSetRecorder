$ErrorActionPreference = "Stop"
Set-Location $PSScriptRoot

Write-Host "=== FilmSet Recorder 0.3 Windows Builder ===" -ForegroundColor Cyan

if (-not (Get-Command py -ErrorAction SilentlyContinue) -and -not (Get-Command python -ErrorAction SilentlyContinue)) {
    throw "Python was not found. Install Python 3.12 (64-bit) and rerun this script. GitHub Actions users do not need Python locally."
}

$python = if (Get-Command py -ErrorAction SilentlyContinue) { "py" } else { "python" }

if (Test-Path .buildvenv) {
    Remove-Item .buildvenv -Recurse -Force
}

if ($python -eq "py") {
    & py -3.12 -m venv .buildvenv
} else {
    & python -m venv .buildvenv
}

$venvPython = Join-Path $PSScriptRoot ".buildvenv\Scripts\python.exe"

& $venvPython -m pip install --upgrade pip
& $venvPython -m pip install -r requirements.txt
& $venvPython -m pip install "pyinstaller>=6.10,<7"
& $venvPython -m unittest discover -s tests -v

Remove-Item build, dist, release -Recurse -Force -ErrorAction SilentlyContinue
New-Item -ItemType Directory -Force release | Out-Null

& $venvPython -m PyInstaller --noconfirm --clean packaging\FilmSetRecorder.spec

$possibleIscc = @(
    "$env:ProgramFiles(x86)\Inno Setup 6\ISCC.exe",
    "$env:ProgramFiles\Inno Setup 6\ISCC.exe"
)
$iscc = $possibleIscc | Where-Object { Test-Path $_ } | Select-Object -First 1

if (-not $iscc) {
    Write-Host ""
    Write-Host "PyInstaller build completed successfully." -ForegroundColor Green
    Write-Host "The portable app is in: dist\FilmSetRecorder\" -ForegroundColor Green
    Write-Host ""
    Write-Host "To create the installer EXE, install Inno Setup 6, then rerun this script." -ForegroundColor Yellow
    exit 0
}

& $iscc packaging\FilmSetRecorder.iss

Write-Host ""
Write-Host "Build complete." -ForegroundColor Green
Write-Host "Installer: release\FilmSetRecorder_Setup_0.6.1.exe" -ForegroundColor Green
