# FINALE_LOG (one line per phase; times IST; commits are made by the human with the prefix FINALE:)

| Phase | Finished | What changed | Test result | Commit |
|---|---|---|---|---|
| Q0 clean-install fix | 2026-10-24 21:29 IST | `app/tests/test_voice_head.py` writes its WAV with the standard-library `wave` module (no `soundfile`); `pyproject.toml` runs every test folder with `python -m pytest` and shows skip reasons; `make test`; root `requirements.txt`; run scripts use it; STATUS.md rewritten | fresh venv from `requirements.txt`: 988 passed; same venv without ffmpeg on PATH: 967 passed, 21 skipped (reason: "ffmpeg not installed") | human: `FINALE: Q0 clean-install fix` |
| Q0 laptop check | 2026-10-24 21:47 | user-reported Windows run | 967 passed, 21 skipped (ffmpeg missing), Python 3.14.5 global | — |
| Q0 laptop venv | 2026-10-24 22:03 | user-reported, Py 3.11.9 venv + ffmpeg | 987 passed, 1 failed (AppTest 30 s timeout); patch 1 raises timeout to 180 s, stringifies results table | re-run pending |
