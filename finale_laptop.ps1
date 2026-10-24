# VERIQ: everything the team laptop still has to run, in one go (Q2-Q5). From the veriq\ folder:
#   powershell -ExecutionPolicy Bypass -File finale_laptop.ps1
# Takes about 15-25 minutes. Every step logs to results\laptop\finale_laptop.log; a failed step is reported and the
# script carries on. At the end it makes results\laptop_final.zip: send that ONE file to Claude C.
$ErrorActionPreference = "Continue"
New-Item -ItemType Directory -Force results\laptop, results\q2 | Out-Null
$log = "results\laptop\finale_laptop.log"
function Say($m) { $t = Get-Date -Format "yyyy-MM-dd HH:mm:ss"; "$t  $m" | Tee-Object -FilePath $log -Append }
function Step($name, [scriptblock]$body) {
    Say "=== $name"
    try { & $body 2>&1 | Tee-Object -FilePath $log -Append; Say "--- $($name): exit $LASTEXITCODE" }
    catch { Say "--- $($name): ERROR $($_.Exception.Message)" }
}
if (-not (Test-Path .\.venv\Scripts\python.exe)) { Say "No .venv: run reproduce.ps1 once first"; exit 1 }
$py = ".\.venv\Scripts\python.exe"

Step "1 install pinned test tools" { & $py -m pip install -q -r requirements-dev.txt }
Step "2 versions (for the voice pins)" { & $py -m pip freeze | Out-File -Encoding utf8 results\laptop\pip_freeze.txt; & $py --version; ffmpeg -version | Select-Object -First 1 }

Step "3 UCI SMS Spam Collection: download, checksum, cue check" {
    if (-not (Test-Path data\raw\sms_spam\SMSSpamCollection)) {
        New-Item -ItemType Directory -Force data\raw\sms_spam | Out-Null
        Invoke-WebRequest -Uri "https://archive.ics.uci.edu/static/public/228/sms+spam+collection.zip" -OutFile data\raw\sms_spam\sms.zip
        Expand-Archive -Force data\raw\sms_spam\sms.zip data\raw\sms_spam
    }
    Get-FileHash data\raw\sms_spam\sms.zip -Algorithm SHA256 | Format-List | Out-File -Encoding utf8 results\laptop\sms_zip_sha256.txt
    Get-Content results\laptop\sms_zip_sha256.txt
    if (Test-Path data\raw\sms_spam\readme) { Copy-Item data\raw\sms_spam\readme results\laptop\sms_readme.txt }
    & $py -m bench.sms.run --data data\raw\sms_spam\SMSSpamCollection --out results\q2\sms.json
}

Step "4 blind chats (run once)" {
    if (Test-Path data\blind\labels.csv) { & $py -m bench.blind.run }
    else { "data\blind\labels.csv not found: blind set not provided (stays 'not run')" }
}

Step "5 time per chat with voice notes (needs torch + AASIST)" {
    if (-not $env:VERIQ_AASIST_REPO -and -not (Test-Path external\aasist\models\weights\AASIST.pth)) {
        git clone --depth 1 https://github.com/clovaai/aasist external\aasist
    }
    & $py scripts\time_chat_with_voice.py
}

Step "6 Docker (optional)" {
    if (Get-Command docker -ErrorAction SilentlyContinue) {
        New-Item -ItemType Directory -Force secrets | Out-Null
        if (-not (Test-Path secrets\registry_secret.txt)) { & $py -c "import secrets; print(secrets.token_urlsafe(32))" | Out-File -Encoding ascii secrets\registry_secret.txt }
        docker compose build; docker compose up -d; Start-Sleep -Seconds 60; docker compose ps
        try { (Invoke-WebRequest -UseBasicParsing http://localhost:8501/_stcore/health).Content } catch { "health check failed: $($_.Exception.Message)" }
        docker compose exec -T veriq python scripts/smoke.py --no-app; docker compose down
    } else { "Docker not installed: container path stays 'not verified'" }
}

Step "7 plan versus delivered + finale slide" { & $py scripts\plan_vs_delivered.py | Select-Object -Last 8; & $py scripts\make_slide.py | Out-Null }
Step "8 acceptance list (runs reproduction, tests, smoke)" { & $py scripts\acceptance.py }

Copy-Item results\REPRODUCE_REPORT.md, results\ACCEPTANCE.md, results\reproduce.json, results\tests.json, results\random_order.json -Destination results\laptop -ErrorAction SilentlyContinue
Copy-Item results\timing_chat_with_voice.json -Destination results\laptop -ErrorAction SilentlyContinue
Copy-Item results\q2\* -Destination results\laptop -ErrorAction SilentlyContinue
Compress-Archive -Force -Path results\laptop\* -DestinationPath results\laptop_final.zip
Say "DONE. Send results\laptop_final.zip to Claude C."
