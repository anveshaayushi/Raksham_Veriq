# VERIQ on Windows. Run from the veriq\ folder:  powershell -ExecutionPolicy Bypass -File app\run_app.ps1
#   -Phone     also serve on the hotspot so a phone can open it (see DEPLOY.md)
#   -NoVoice   skip installing the voice-model extras (torch etc.); voice notes then always say "can't assess"
#   -SkipTests start faster (the test suite takes about 2-3 minutes on the laptop)
param([switch]$Phone, [switch]$NoVoice, [switch]$SkipTests)
# Native commands (py, python, pip) report failure through $LASTEXITCODE; we check it ourselves.
$ErrorActionPreference = "Continue"
if (-not (Test-Path .\.venv\Scripts\python.exe)) {
    # Any Python 3.11+: try the py launcher (3.13, 3.12, 3.11), then python on PATH.
    $made = $false
    if (Get-Command py -ErrorAction SilentlyContinue) {
        foreach ($v in @("-3.13", "-3.12", "-3.11")) {
            if (-not $made) {
                cmd /c "py $v -c ""import sys"" >nul 2>nul"
                if ($LASTEXITCODE -eq 0) { py $v -m venv .venv; $made = ($LASTEXITCODE -eq 0) }
            }
        }
    }
    if (-not $made) { python -m venv .venv }
    if (-not (Test-Path .\.venv\Scripts\python.exe)) { Write-Host "Could not create .venv: install Python 3.11+ from python.org"; exit 1 }
}
# Pinned versions (requirements.txt); pip skips what is already installed, so this is quick after the first time.
.\.venv\Scripts\python.exe -m pip install -q -r requirements.txt
if ($LASTEXITCODE -ne 0) { Write-Host "pip install failed (internet needed the first time; or use install_offline.ps1)"; exit 1 }
if (-not $NoVoice) {
    .\.venv\Scripts\python.exe -m pip install -q -r requirements-voice.txt
    if ($LASTEXITCODE -ne 0) { Write-Host "Voice extras not installed: voice notes will say 'can't assess'. The rest works." }
}
if (-not (Get-Command ffmpeg -ErrorAction SilentlyContinue)) { Write-Host "ffmpeg not found: run  winget install Gyan.FFmpeg  then open a new terminal." }
if (-not $SkipTests) {
    .\.venv\Scripts\python.exe -m pytest
    if ($LASTEXITCODE -ne 0) { Write-Host "Some tests failed. Starting the app anyway; send the test output to Claude C." }
}
$extra = @()
if ($Phone) { $extra = @("--server.address", "0.0.0.0"); ipconfig | Select-String "IPv4" }
.\.venv\Scripts\python.exe -m streamlit run app\streamlit_app.py --browser.gatherUsageStats false --client.toolbarMode minimal @extra
