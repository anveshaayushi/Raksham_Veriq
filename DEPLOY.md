# DEPLOY: how to run VERIQ in each setting

Verification status (25 Oct 2026): laptop demo and offline install **tested** (Linux sandbox: clean venv, offline
wheelhouse install, `scripts/smoke.py` 7/7; Windows laptop: Q0/Q1 runs, user-reported). Phone over hotspot: **not
verified by Claude** (needs a phone). Docker: **not verified** (Docker Hub is blocked in Claude's sandbox; run it on a
machine with Docker and paste the output). Pilot setup: **not done**; the list of what a pilot needs is below.

## 1. Laptop demo (Windows 11)

```powershell
winget install Gyan.FFmpeg                                   # once, then open a new terminal
cd veriq
powershell -ExecutionPolicy Bypass -File app\run_app.ps1      # creates .venv, installs pinned packages, runs tests, starts the app
```
Expected: the tests end with "passed", then a browser opens at http://localhost:8501 showing "VERIQ".
Faster restart: `app\run_app.ps1 -SkipTests`. Without the voice model: `-NoVoice`.
Check an install at any time: `python scripts\smoke.py` → last line `SMOKE: PASS (7/7 steps)`.

## 2. Offline install (no internet at the venue)

On a computer WITH internet (same OS family as the target):
```
python scripts/make_offline_bundle.py --platform win_amd64 --python 3.11 --out veriq_offline.zip     # add --voice for torch
```
Copy `veriq_offline.zip` (and the ffmpeg installer zip) by USB. On the offline computer:
```powershell
Expand-Archive veriq_offline.zip . ; cd veriq
powershell -ExecutionPolicy Bypass -File install_offline.ps1    # ends with SMOKE: PASS (7/7 steps)
```
Tested in the sandbox for Linux / Python 3.13 (41 wheels, install with `--no-index`, smoke 7/7).

## 3. Phone demo over the laptop's hotspot

1. Turn on Windows Mobile Hotspot; connect the phone to it.
2. `powershell -ExecutionPolicy Bypass -File app\run_app.ps1 -Phone -SkipTests` (prints the laptop's IPv4 addresses).
3. On the phone open `http://<the 192.168.137.x address>:8501`. If it does not load, allow Python through Windows
   Defender Firewall (private networks). Nothing leaves the laptop: the phone talks only to it.

## 4. Docker on a server

```bash
mkdir -p secrets && python3 -c "import secrets; print(secrets.token_urlsafe(32))" > secrets/registry_secret.txt
# optional voice model: git clone https://github.com/clovaai/aasist external/aasist ; set VOICE: "1" in docker-compose.yml
docker compose build && docker compose up -d
docker compose ps                     # STATUS should become "healthy" within about a minute
curl http://localhost:8501/_stcore/health     # -> ok
docker compose exec veriq python scripts/smoke.py --no-app
```
The container runs as a non-root user (uid 10001) with a read-only filesystem, `/tmp` in memory (voice notes are
written there for a moment and deleted), the registry database on the `veriq_data` volume, the HMAC key from a mounted
secret file (never in the image or the repo), `VERIQ_OFFLINE=1`, and a health check on `/_stcore/health`.
Put it behind HTTPS (a reverse proxy such as Caddy or nginx) before any real user touches it.

## 5. Pilot reviewer desk (bank fraud-ops team or state cyber cell): what it would look like

- One container as above, reachable only on the organisation's network; reviewers use the app's **Reviewer view**
  toggle to see review requests and uphold or overturn them (audit trail kept, no raw identifiers in it).
- The registry (`VERIQ_REGISTRY_DB` on the volume) collects reports from the desk's own cases; it links a payee only
  after two independent reporters or a reviewer's confirmation.
- Settings (environment variables, see `app/config.py`): `VERIQ_DATA_DIR`, `VERIQ_REGISTRY_DB`,
  `VERIQ_REGISTRY_SECRET_FILE`, `VERIQ_MAX_UPLOAD_MB`, `VERIQ_LANG` (en/hi), `VERIQ_OFFLINE`.

## 6. What a pilot still needs (honest list; none of this is done)

- A security review and penetration test of the web app and container; HTTPS; user authentication for reviewers.
- A DPDP Act 2023 review (purpose, consent text, retention, data-principal rights) by the partner's privacy officer.
- A data-sharing agreement for the registry (who may report, who may see links, how long hashes are kept, how a
  wrongly linked payee is cleared) and key management for the HMAC secret (rotation, custody).
- A fresh, dated SEBI intermediary list (the repo's snapshot is synthetic) and a process to refresh it.
- Monitoring (health, error rate, review queue time) and backups of the registry volume.
- A labelled evaluation on the partner's own (consented) cases before any number is quoted to users.
- A voice detector that holds its false-alarm rate on the partner's own recordings; until then voice is a weak review cue only (pretrained AASIST with an ASVspoof-dev threshold), and `VERIQ_VOICE_CALIBRATION=none` turns it off.
