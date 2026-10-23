# VERIQ v0 on Windows. Run from the veriq\ folder:  powershell -ExecutionPolicy Bypass -File app\run_app.ps1
#   -Phone   also serve on the hotspot so a phone can open it
param([switch]$Phone)
$ErrorActionPreference = "Stop"
if (-not (Test-Path .venv)) {
    py -3.11 -m venv .venv
    .\.venv\Scripts\python.exe -m pip install -r app\requirements.txt
}
.\.venv\Scripts\python.exe -m pytest -q
$extra = @()
if ($Phone) { $extra = @("--server.address", "0.0.0.0"); ipconfig | Select-String "IPv4" }
.\.venv\Scripts\python.exe -m streamlit run app\streamlit_app.py --browser.gatherUsageStats false --client.toolbarMode minimal @extra
