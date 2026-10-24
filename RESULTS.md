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
| 2026-10-24 11:43 IST | `704c9f5` | FINALE: `python -m pytest -q tests app registry report` after the SQLite registry (C3) | **127 passed** (incl. 17 registry tests: poisoning by one token x20 and 5 tokens in one minute does not link) |
| 2026-10-24 15:24 IST | see git log | FINALE: `python -m pytest -q tests app registry report` after the engine port (CR-C13) | **918 passed** (768 of them are the property grid: 384 input combinations x 2 properties) |
| 2026-10-24 15:27 IST | see git log | FINALE: `python -m bench.run dev` (120 synthetic chats, used for fixing) | first run 79.0% decisions; after the personal-name fix 100% (not reported as a result) |
| 2026-10-24 15:27 IST | see git log | FINALE: `python -m bench.run test` (300 synthetic chats, 399 payees, run once) | extraction 399/399, 0 false pickups; decisions 96.2% (384/399); false alarms on genuine payees 0/178; scam payees marked "no major issue" 0/221; median 0.37 ms per chat. Failure: "KRISHNA DAIRY FARM" read as a personal name (15 misses, safe direction). See bench/README.md |
| 2026-10-24 17:09 IST | see git log | FINALE: `python -m bench.run test` run 2, after the look-alike and cue changes (made for the red-team brief, not from test failures) | unchanged: 399/399 payees, 96.2% decisions, 0/178 false alarms, 0/221 scams cleared; same 15 misses ("KRISHNA DAIRY FARM") |
| 2026-10-24 17:09 IST | see git log | FINALE: `python -m bench.adversarial` (red-team set, written by us knowing our defences) | defended attacks 31/31 passed; known gaps still failing 4/4 (listed below) |
| 2026-10-24 17:09 IST | see git log | FINALE: `python -m pytest -q tests app registry report voice` | **983 passed** |
| — | — | Windows 11: `app\run_app.ps1` on the team laptop | **not run** |

The 113/114 are code tests, not accuracy numbers. Demo results are Claude A's *expected* fixture values, not a rules engine.
Chat-side numbers above are on SYNTHETIC chats written by the team (bench/README.md); say so whenever they are shown. No voice detector numbers exist yet. Do not quote any voice number in the deck.

## Claude B: voice runs (pasted from voice/B_RESULTS_ROWS.md; nothing here is an accuracy number)

| What | Command | Date / where | Commit | Result |
|---|---|---|---|---|
| Unmodified shared repo (before B's code) | `python -m pytest tests app registry report -o addopts="" -q` | 2026-10-24, B's sandbox, Python 3.13, streamlit installed | 8718c9c (as in the zip) | 114 passed |
| Shared repo + B's voice/eval/scripts/tests | `python -m pytest tests app registry report voice -o addopts="" -q` | 2026-10-24, B's sandbox | not committed (human commits) | 156 passed, 3 failed. All 3 failures are in app/tests (C): see CR-B1. Not hidden or skipped. |
| B's own tests only | `python -m pytest voice tests/voice_eval -o addopts="" -q` | 2026-10-24, B's sandbox (ffmpeg present, no torch, no model) | not committed | 45 passed. Uses synthetic noise and a fake detector: proves the code paths, not detection accuracy. |
| Same, on a scratch copy with C's 2 test edits from CR-B1 applied | same command | 2026-10-24, B's sandbox | scratch, not committed | 159 passed (that was before B added 2 more adapter tests and removed a duplicate; same two edits are all that is needed) |
| B's own suite on team laptop (older drafts) | `python -m pytest tests/voice_eval -q` | 2026-10-23 15:15 IST, team laptop, Windows, Python 3.13, ffmpeg 9.0.2 (user-reported output) | not committed | 25 passed |
| AASIST plumbing check | `python -m voice.detector --selfcheck` | 2026-10-23 15:20 IST, team laptop (user-reported output) | not committed | "loaded. model_version=aasist-pretrained@51d2d9cf0738" (this is a hash of the weights file; says nothing about accuracy) |
| Detector on 14 own clips (6 Windows-TTS, 8 mic recordings) | `python -m eval --input dev --out out\run1.csv --infer-labels-from-dirs` | 2026-10-23 evening, team laptop (user-reported output) | not committed | INVALID AS EVIDENCE: 6 of 8 real clips had 0.00 s detected speech (near-silent recordings). No AUC from this run may be quoted. 0.38 to 0.92 s per clip observed, tiny clips, one machine. |
| Seconds per clip on CPU for the real model (target < 2 s) | not run in a controlled way | n/a | n/a | not run |
| Calibrated threshold, EER, AUC, false-alarm, miss, per codec / language | not run | n/a | n/a | not run (ASVspoof LA download was still in progress: 3.2 of 7.1 GB at 24 Oct 09:55) |
| Speaker consistency, speech-to-text | not built | n/a | n/a | not run |
| Full suite after C merged B (C's sandbox, Linux, Python 3.13, ffmpeg present) | `python -m pytest -q tests app registry report voice` | 2026-10-24 15:38 IST | see git log | **963 passed** |


## Red-team log (2026-10-24 17:09 IST, `python -m bench.adversarial`)

| Group | Attack | Expected | Got | Result |
|---|---|---|---|---|
| look-alike payee name | NAVYUG ONLINE TRADERS | HUMAN_REVIEW | HUMAN_REVIEW | pass |
| look-alike payee name | Navyug Broking Services | HUMAN_REVIEW | HUMAN_REVIEW | pass |
| look-alike payee name | NAVYUG CAPITAL MARKETS | HUMAN_REVIEW | HUMAN_REVIEW | pass |
| look-alike payee name | NAVYUG PAYMENTS | HUMAN_REVIEW | HUMAN_REVIEW | pass |
| look-alike payee name | NAVYUG BROKING SOLUTIONS | HUMAN_REVIEW | HUMAN_REVIEW | pass |
| look-alike payee name | NAVYUG TECH SERVICES | HUMAN_REVIEW | HUMAN_REVIEW | pass |
| look-alike payee name | identical name on a mule account (NAVYUG BROKING PVT LTD) | not NO_MAJOR_ISSUE | NO_MAJOR_ISSUE | KNOWN GAP |
| genuine name variant | NAVYUG BROKING PRIVATE LIMITED | NO_MAJOR_ISSUE | NO_MAJOR_ISSUE | pass |
| genuine name variant | NAVYUG BROKING LTD | NO_MAJOR_ISSUE | NO_MAJOR_ISSUE | pass |
| genuine name variant | M/S NAVYUG BROKING PVT LTD | NO_MAJOR_ISSUE | NO_MAJOR_ISSUE | pass |
| genuine name variant | Navyug Broking | NO_MAJOR_ISSUE | NO_MAJOR_ISSUE | pass |
| unrelated payee name | SHREE GANESH TRADERS | NAME_DISCREPANCY | NAME_DISCREPANCY | pass |
| unrelated payee name | BALAJI GARMENTS | NAME_DISCREPANCY | NAME_DISCREPANCY | pass |
| unrelated payee name | RK MOBILE POINT | NAME_DISCREPANCY | NAME_DISCREPANCY | pass |
| unrelated payee name | KRISHNA DAIRY FARM (contains a given name) | NAME_DISCREPANCY | INCONCLUSIVE | KNOWN GAP |
| obfuscated pressure phrase | gu@r@nteed 3x returns | guaranteed_return | guaranteed_return | pass |
| obfuscated pressure phrase | 100% guaranteed profit | guaranteed_return | guaranteed_return | pass |
| obfuscated pressure phrase | P.a.y 18% t@x to withdraw | fee_to_withdraw | fee_to_withdraw | pass |
| obfuscated pressure phrase | pay unfreeze account fee | fee_to_withdraw | fee_to_withdraw | pass |
| obfuscated pressure phrase | u_r_g_e_n_t | urgency | urgency | pass |
| obfuscated pressure phrase | send in 5 mins | urgency | urgency | pass |
| obfuscated pressure phrase | no loss pakka double | guaranteed_return | guaranteed_return | pass |
| obfuscated pressure phrase | sure-shot gain | guaranteed_return | guaranteed_return | pass |
| obfuscated pressure phrase | slot cancel ho jayega | urgency | urgency | pass |
| obfuscated pressure phrase | share the OTP you got | otp_pin_request | otp_pin_request | pass |
| obfuscated pressure phrase | install AnyDesk | remote_access | remote_access | pass |
| obfuscated pressure phrase | your chance closes soon, act fast (reworded, no keyword) | urgency | missed | KNOWN GAP |
| obfuscated pressure phrase | profit is fixed, you cannot lose (reworded, no keyword) | guaranteed_return | missed | KNOWN GAP |
| benign sentence (false cue check) | Please confirm the payee name on your app before paying. | no hard cue | no hard cue | pass |
| benign sentence (false cue check) | Onboarding fee ₹10,000 | no hard cue | no hard cue | pass |
| benign sentence (false cue check) | Markets are volatile; returns are not guaranteed. | no hard cue | no hard cue | pass |
| benign sentence (false cue check) | Thanks, received. | no hard cue | no hard cue | pass |
| payee hidden in a QR image | QR names SUNITA TRADERS, no name check yet | found + HUMAN_REVIEW | found + HUMAN_REVIEW | pass |
| payee hidden in a QR image | QR copies the firm's name (pn is sender-typed); no name check | not NO_MAJOR_ISSUE | not NO_MAJOR_ISSUE | pass |
| short voice note + pressure | 0.3 s 'pay now' note, urgency in text | INCONCLUSIVE + HIGH PRESSURE | INCONCLUSIVE + HIGH PRESSURE | pass |

Already covered by unit tests (not repeated above): registry poisoning (one token x20, five tokens in one minute: not
linked), `<script>` and Markdown links in a chat (escaped, defanged), zip bomb / zip-slip / encrypted zip (rejected).

## System dashboard (only measured numbers; everything else says "not run")

```
VERIQ SYSTEM RESULTS · 2026-10-24 17:09 IST · synthetic data written by the team unless stated
LANE 1 VOICE (Claude B: ffmpeg -> quality gate -> pretrained AASIST)
  - EER / AUC / false alarms / misses on any dataset ......... NOT RUN (no calibrated threshold yet)
  - Short / unclear audio ..................................... returns cant_assess by design (code tests only)
  - Seconds per clip ........................................... NOT RUN (controlled timing not done)
LANE 2 RECIPIENT, QR & NAME MATCHING (rules, no trained model)
  - Payee extraction, 300 held-out synthetic chats ............ 399/399 found, 0 false pickups
  - Decisions as expected ...................................... 96.2% (384/399); named failure: given-name shop names
  - False alarms on genuine payees ............................. 0/178
  - Scam payees given "No major issue" ......................... 0/221
  - Red-team: look-alike names 6/6, genuine variants 4/4, obfuscated cues 11/11, QR payees 2/2, benign sentences 4/4
  - Known gaps: identical-name mule account, "KRISHNA DAIRY FARM", 2 reworded phrases with no keyword
LANE 3 DECISION ENGINE
  - Rules time per chat (laptop-class CPU, Linux sandbox) ...... median 0.4 ms, max ~1 ms (excludes voice)
  - End-to-end time with voice ................................. NOT RUN
```
