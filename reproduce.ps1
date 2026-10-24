# VERIQ: reproduce every reported number on Windows (same as `make reproduce`). Run from the veriq\ folder:
#   powershell -ExecutionPolicy Bypass -File reproduce.ps1            (data, tests, coverage, random order, benchmarks)
#   powershell -ExecutionPolicy Bypass -File reproduce.ps1 -Mutation  (also the mutation check; slow)
# Uses .venv if it exists, otherwise creates it from requirements-dev.txt (pinned). Results go to results\.
param([switch]$Mutation, [switch]$Quick, [string]$VoiceData = "", [string]$Aasist = "")
$ErrorActionPreference = "Continue"
if (-not (Test-Path .\.venv\Scripts\python.exe)) {
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
.\.venv\Scripts\python.exe -m pip install -r requirements-dev.txt
if ($LASTEXITCODE -ne 0) { Write-Host "pip install failed (internet is needed the first time)"; exit 1 }
$args2 = @()
if ($Mutation) { $args2 += "--mutation" }
if ($Quick) { $args2 += "--quick" }
if ($VoiceData -ne "") { $args2 += @("--voice-data", $VoiceData, "--aasist", $Aasist) }
.\.venv\Scripts\python.exe scripts\reproduce.py @args2
exit $LASTEXITCODE
