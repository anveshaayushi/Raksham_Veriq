# VERIQ: check who you are paying, before you pay

Team The Outliers · RAKSHAM Grand Finale, IIT Delhi (24-25 Oct 2026). VERIQ reads a suspicious money chat
(WhatsApp export, voice notes, QR screenshots), lists every place it asks you to pay, compares the name YOUR bank
app shows with the firm the chat claims, checks the quoted SEBI number against a dated list, looks for pressure
tactics and other victims' reports, and gives one answer per payee with its evidence and your next step. Voice is
only a review cue. It blocks nothing and contacts no one. It can be fooled (EVASION_LAB.md).

**Run:** Windows `powershell -ExecutionPolicy Bypass -File app\run_app.ps1` · macOS/Linux `bash app/run_app.sh`
**Check an install:** `python scripts/smoke.py` · **Reproduce every number:** `reproduce.ps1` or `make reproduce`
**Judges' own files:** `veriq-eval --input <folder> --out preds.csv --report report.md` (or the app's Kit tab)

| Read | For |
|---|---|
| SUBMISSION.md | the index: what, how to run, reproduce, data and licences, limits |
| RUBRIC_MAP.md | every rubric row → evidence, command, demo step |
| DEMO_12MIN.md | the live slot and the answers |
| RESULTS.md, CLAIMS.md, TESTPLAN.md | every number with its command; every claim with its test |
| PROBLEM_USER.md, DEPLOYABILITY.md, DEPLOY.md | user, scenarios, sources; who runs it, cost estimates, pilot needs |
| ENGINEERING_WALKTHROUGH.md, PLAN_VS_DELIVERED.md | what we built in the finale vs the Round 1 plan |
| PREBUILT.md, FINALE_LOG.md, DISCLOSURE.md | prototype boundary (tag `v0-prebuilt`), phase log, every model/dataset/library and AI use |
| docs/walkthrough/ | one plain-words card per module |

Claude (Anthropic) was used to write code and documents under the team's direction. All chat data is synthetic or
written by the team; voice data is public (ASVspoof 2019 LA, FSDD) or synthetic (Kokoro TTS).
