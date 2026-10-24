# VERIQ on Windows. Run from the veriq\ folder:  powershell -ExecutionPolicy Bypass -File app\run_app.ps1
#   -Phone   also serve on the hotspot so a phone can open it
param([switch]$Phone)
# Native commands (py, python, pip) report failure through $LASTEXITCODE; we check it ourselves.
$ErrorActionPreference = "Continue"
if (-not (Test-Path .venv)) {
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
    .\.venv\Scripts\python.exe -m pip install -r requirements.txt
    if ($LASTEXITCODE -ne 0) { Write-Host "pip install failed (internet needed the first time)"; exit 1 }
}
.\.venv\Scripts\python.exe -m pytest
if ($LASTEXITCODE -ne 0) { Write-Host "Some tests failed. Starting the app anyway; send the test output to Claude C." }
$extra = @()
if ($Phone) { $extra = @("--server.address", "0.0.0.0"); ipconfig | Select-String "IPv4" }
.\.venv\Scripts\python.exe -m streamlit run app\streamlit_app.py --browser.gatherUsageStats false --client.toolbarMode minimal @extra
