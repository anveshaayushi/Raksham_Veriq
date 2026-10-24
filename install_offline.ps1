# Install VERIQ with NO internet, from the wheelhouse\ made by scripts\make_offline_bundle.py. Run in the veriq\ folder:
#   powershell -ExecutionPolicy Bypass -File install_offline.ps1
$ErrorActionPreference = "Continue"
if (Get-Command py -ErrorAction SilentlyContinue) { py -3.11 -m venv .venv; if ($LASTEXITCODE -ne 0) { python -m venv .venv } } else { python -m venv .venv }
.\.venv\Scripts\python.exe -m pip install --no-index --find-links wheelhouse -r requirements.txt
if ($LASTEXITCODE -ne 0) { Write-Host "Offline install failed: was the wheelhouse made for Windows and this Python version?"; exit 1 }
if (Get-ChildItem wheelhouse -Filter "torch-*" -ErrorAction SilentlyContinue) {
  .\.venv\Scripts\python.exe -m pip install --no-index --find-links wheelhouse torch torchaudio soundfile scikit-learn
}
.\.venv\Scripts\python.exe scripts\smoke.py
Write-Host "Installed. Start with: powershell -ExecutionPolicy Bypass -File app\run_app.ps1"
