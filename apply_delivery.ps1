# Apply a VERIQ delivery on the laptop WITHOUT rewriting history. Run from the repo folder (veriq\), (.venv) active:
#   powershell -ExecutionPolicy Bypass -File <unzipped delivery>\veriq\apply_delivery.ps1 -From <unzipped delivery>\veriq
# Steps: check branch -> copy the delivery's files over the repo -> tidy (git mv internal notes to docs\history) ->
# run the tests -> stage -> commit (FINALE:). It never rebases, resets, amends or force-pushes, and never touches
# tag v0-prebuilt. It does NOT push: you run the printed push command yourself.
param([Parameter(Mandatory=$true)][string]$From,
      [string]$Message = "FINALE: rubric evidence (RUBRIC_MAP, walkthrough, problem/user, evasion lab, Q&A, 12-min demo), voice weak cue, safeguard tests, tidy repo")
$ErrorActionPreference = "Stop"
if (-not (Test-Path .git)) { Write-Host "Run this from the repo folder (the one with .git)"; exit 1 }
$branch = (git rev-parse --abbrev-ref HEAD).Trim()
if ($branch -ne "claude-c") { Write-Host "You are on '$branch'. Run: git checkout claude-c"; exit 1 }
$src = (Resolve-Path $From).Path
if ($src -eq (Resolve-Path .).Path) { Write-Host "-From must be the UNZIPPED DELIVERY folder, not the repo"; exit 1 }
Write-Host "1/5 copying files from $src"
Copy-Item -Recurse -Force (Join-Path $src "*") .
Write-Host "2/5 tidying (git mv only, no history rewrite)"
$py = ".\.venv\Scripts\python.exe"; if (-not (Test-Path $py)) { $py = "python" }
& $py scripts\tidy_repo.py
Write-Host "3/5 running the tests (2-3 min)"
$ErrorActionPreference = "Continue"
& $py -m pytest -q -o addopts="" 2>&1 | Select-Object -Last 3
if ($LASTEXITCODE -ne 0) { Write-Host "TESTS FAILED: nothing committed. Send the output to Claude C."; exit 1 }
Write-Host "4/5 staging"
git add -A
git status --short | Measure-Object | ForEach-Object { Write-Host "   $($_.Count) changed paths" }
Write-Host "5/5 committing"
git commit -m $Message
git log -1 --format="%h %s"
Write-Host "Now push (normal push, never --force):   git push origin claude-c"
