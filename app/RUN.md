# Running the VERIQ v0 app (Claude C)

## One command
- Windows: `powershell -ExecutionPolicy Bypass -File app\run_app.ps1` (add `-Phone` for the hotspot demo)
- macOS/Linux: `bash app/run_app.sh` (add `--phone`)

Each creates `.venv` on first run, installs, runs the tests, then starts the app.

## Windows 11 (PowerShell) by hand, from the `veriq` folder

```powershell
py -3.11 --version                      # if missing: winget install Python.Python.3.11, then open a new terminal
py -3.11 -m venv .venv
.\.venv\Scripts\Activate.ps1            # if blocked: Set-ExecutionPolicy -Scope CurrentUser RemoteSigned
python -m pip install -r app\requirements.txt
python -m pytest   # expect: 988 passed (with ffmpeg) or 967 passed + 21 skipped (without ffmpeg)
python -m streamlit run app\streamlit_app.py --browser.gatherUsageStats false --client.toolbarMode minimal
```
Then open http://localhost:8501. Ctrl+C stops it, and stopping it clears every case from memory.

## macOS / Linux

```bash
python3 -m venv .venv && source .venv/bin/activate
pip install -r app/requirements.txt
python -m pytest
python -m streamlit run app/streamlit_app.py --browser.gatherUsageStats false --client.toolbarMode minimal
```

`--browser.gatherUsageStats false` stops Streamlit's own usage telemetry, so the app makes no outside requests.

## Phone demo (laptop runs the app, phone is the screen)
1. Connect the laptop to the **phone's hotspot** (venue Wi-Fi may block device-to-device traffic).
2. Start the app with `--server.address 0.0.0.0`; Windows Firewall will ask: allow on **private** networks.
3. Run `ipconfig` and find the laptop's IPv4 address on the hotspot adapter, e.g. 192.168.43.20.
4. On the phone open `http://192.168.43.20:8501`.

## Quick demo path
Consent → Upload → tab **Try a synthetic demo** → Scenario A → **Load this demo** → Continue → Continue →
**Get the answer** → turn on **I have already sent money** → **Make the reports** → download the four files.

## What is real and what is a stub (v0)
| Part | Status |
|---|---|
| Consent, upload checks (.txt/.zip/voice), SHA-256, safe ZIP reading | real, tested |
| Android, iPhone and plain (no-time) exports; day/month order per file | stub parser, tested |
| WhatsApp parsing and payee extraction | **stub** in `app/adapters/extract.py` until Claude A's `parsing/`, `extract/` exist |
| Decision per payee | **stub**: Claude A's `rules/` when present; demos show Claude A's golden-fixture expected values (dropped if you edit the demo); uploads get `INCONCLUSIVE · INCONCL` |
| Voice check | **stub**: demos use Claude B's `voice.stub.stub_result` when `voice/` is present (else the fixture's stub values); uploads are `cant_assess` until B confirms an entry point. No voice score is ever shown while there is no calibrated threshold |
| Registry | **stub** fixture table; unknown payees are `unavailable`, never `clean` |
| Money-already-sent toggle, filing sheet, redacted summary | real, tested |

## Voice model and measured results (FINALE)
- The trained voice head is used automatically when torch and the AASIST weights load
  (`$env:VERIQ_AASIST_REPO = "<path>\external\aasist"`). Turn it off with `$env:VERIQ_VOICE_HEAD = "0"`.
- Reproduce the numbers: `python -m bench.run test`, `python -m bench.adversarial`, and (needs the data tools in
  `bench/voice/requirements.txt`) `python -m bench.voice.make_set ...` then `python -m bench.voice.train_eval ...`.
- In the app: left menu, "How accurate is VERIQ?".
