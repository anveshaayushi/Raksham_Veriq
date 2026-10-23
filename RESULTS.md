# RESULTS: every number with its command

| Date / time | Commit | Command | Outcome |
|---|---|---|---|
| 2026-10-23 15:07 IST | none (before Git) | `python -m pytest -q` (from `veriq/`, Python 3.13.16, Streamlit 1.65.0, pytest 9.1.1, Linux) | 48 passed in 6.6 s |
| 2026-10-23 15:35 IST | see PREBUILT.md | `python -m pytest -q` after plain-export and date-order support | **51 passed** in 7.0 s |
| 2026-10-23 15:38 IST | see PREBUILT.md | `bash app/run_app.sh` in a clean copy (new venv, pip install, tests, start) | 51 passed; app served on :8501 |
| 2026-10-23 ~15:05 IST | none | `python -m streamlit run app/streamlit_app.py --server.headless true` | started; `/_stcore/health` returned `ok` |
| 2026-10-23 ~15:05 IST | none | Playwright browser check, phone 390×844: consent → demo A → answer → money toggle → reports | horizontal overflow 0 px; 1930 next step shown for all 3 payees; summary and filing sheet HTML downloaded |
| 2026-10-23 ~15:05 IST | none | Playwright browser check, desktop: real `.txt` upload containing `<script>` and a Markdown link | script not executed, no clickable link (URLs defanged), result `INCONCLUSIVE · STUB-NO-ENGINE` |
| — | — | `pytest tests/golden` | **not run** (no golden fixtures from Claude A yet) |
| — | — | Windows 11: `app\run_app.ps1` on the team laptop | **not run** |

No detector, extraction or decision metrics exist yet: those modules are stubs in this v0.
