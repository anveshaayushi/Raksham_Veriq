# Rubric map: each rubric row → evidence, command, live-demo step, status

Status words: **works** (runs and is tested), **partial** (runs, with a stated gap), **not run**. No self-scoring.
Demo minutes refer to DEMO_12MIN.md.

## Stage 1
| Rubric row (weight) | Evidence | Command | Live demo | Status |
|---|---|---|---|---|
| Working prototype (25) | app; `scripts/smoke.py`; C-24, C-33 | `app\run_app.ps1`; `python scripts/smoke.py` | 1-3 (judge's own chat) | works |
| Spot-check and measured accuracy (30) | RESULTS.md; Kit runner (C-32); blind sets C-36 + AI-generated set; ASVspoof C-29; names C-34 | `veriq-eval --input <kit> --out p.csv --report r.md`; `python -m bench.blind.run` | 10.5-11.5 | partial: kit and blind/AI-generated sets not run yet |
| Own engineering (15) | ENGINEERING_WALKTHROUGH.md; `git log v0-prebuilt..HEAD` | `git log --oneline v0-prebuilt..HEAD` | 9.5 (walk a module) | works |
| Alert and response, as built (15) | why-it-fired + four actions; `tests/completeness/test_safeguards_running.py`; review path C-21 | `python -m pytest tests/completeness/test_safeguards_running.py` | 1-3, 7-8.5 | works |
| Delivery vs Round 1 plan (15) | PLAN_VS_DELIVERED.md (also an app page) | `python scripts/plan_vs_delivered.py` | page in the sidebar | works |

## Stage 2
| Rubric row (weight) | Evidence | Command | Live demo | Status |
|---|---|---|---|---|
| Problem and user (20) | PROBLEM_USER.md (sourced figures; "needs source" where missing) | | 0-1 | works |
| Deployability and scale (15) | DEPLOYABILITY.md, DEPLOY.md, offline bundle, Dockerfile | `python scripts/smoke.py`; `install_offline.ps1` | 11.5-12 | partial: Docker and phone hotspot not verified |
| Communication and Q&A (10) | QA_SHEET.md, DEMO_12MIN.md (timed) | | whole slot | works |
| Live user journey (25) | scenario player A-D; `results/live_journey.json` (5 varied inputs incl. a miss) | `python scripts/live_journey.py` | 3-6 | works |
| Adversarial robustness (20) | EVASION_LAB.md, red-team set, evasion lab page | `python -m bench.adversarial` | 9.5-10.5 | works (with named gaps) |
| Responsible AI and mistakes (10) | scenario D; `results/mistake_path.json`; privacy proof page | `python scripts/mistake_path.py` | 7-8.5, 11.5-12 | works |
