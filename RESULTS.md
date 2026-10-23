# RESULTS

Every number here must come from a command that can be re-run. Format: result, command, date, commit, dataset version.
If it was not run, it says "not run". Numbers from the Round 1 deck (EER 0.37, "53 tests", etc.) must never be reused.

| Metric | Result | Command | Date | Commit | Data |
|---|---|---|---|---|---|
| Golden + schema tests | 45 passed (sandbox run) | `python3 -m pytest tests/golden` | 2026-10-23 | not committed yet | 3 synthetic fixtures |
| Golden + schema tests, re-run by C after merge | 45 passed | `python -m pytest -q tests` | 2026-10-23 16:16 IST | `4a113b18fd` | 3 synthetic fixtures |
| Fixture validator | ALL VALID (3 fixtures + 1 reference file) | `python3 -m core.validate` | 2026-10-23 | not committed yet | 3 synthetic fixtures |
| Payee-extraction precision/recall | not run | | | | |
| Name-matching false-discrepancy rate | not run | | | | |
| Truth-table pass rate | not run | | | | |
| Voice EER / AUC / false-alarm / miss | not run (Claude B) | | | | |
| Time per chat | not run | | | | |

## Claude C: app, registry, report runs

| Date / time | Commit | Command | Outcome |
|---|---|---|---|
| 2026-10-23 15:07 IST | none (before Git) | `python -m pytest -q` (from `veriq/`, Python 3.13.16, Streamlit 1.65.0, pytest 9.1.1, Linux) | 48 passed in 6.6 s |
| 2026-10-23 15:35 IST | 19a52177ec | `python -m pytest -q` after plain-export and date-order support | **51 passed** in 7.0 s |
| 2026-10-23 15:38 IST | 19a52177ec | `bash app/run_app.sh` in a clean copy (new venv, pip install, tests, start) | 51 passed; app served on :8501 |
| 2026-10-23 ~15:05 IST | none | `python -m streamlit run app/streamlit_app.py --server.headless true` | started; `/_stcore/health` returned `ok` |
| 2026-10-23 ~15:05 IST | none | Playwright browser check, phone 390×844: consent → demo A → answer → money toggle → reports | horizontal overflow 0 px; 1930 next step shown for all 3 payees; summary and filing sheet HTML downloaded |
| 2026-10-23 ~15:05 IST | none | Playwright browser check, desktop: real `.txt` upload containing `<script>` and a Markdown link | script not executed, no clickable link (URLs defanged), result `INCONCLUSIVE · STUB-NO-ENGINE` |
| 2026-10-23 16:15 IST | see git log | `python -m pytest -q` after Claude B integration | **55 passed** in 7.3 s |
| 2026-10-23 16:16 IST | `4a113b18fd` | `python -m pytest -q tests app registry report` after merging Claude A (Python 3.13, Streamlit 1.65, Linux) | **113 passed** (45 A golden/schema + 68 C) |
| 2026-10-23 22:55 IST | see git log | `python -m pytest -q tests app registry report` after merging voice transcripts before A's extractor | **114 passed** |
| — | — | Windows 11: `app\run_app.ps1` on the team laptop | **not run** |

The 113/114 are code tests, not accuracy numbers. Demo results are Claude A's *expected* fixture values, not a rules engine.
No detector, extraction or decision metrics exist yet. Do not quote any voice number in the deck.
