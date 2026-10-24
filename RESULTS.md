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

## Voice on open data: ASVspoof 2019 LA (Q2, 25 Oct 2026)

**Read first.** Pretrained AASIST was TRAINED on ASVspoof 2019 LA (its train split), so every pretrained-AASIST
number below is **in-distribution** and flatters the model. The LA eval split has speakers and attack types (A07-A19)
that were not in LA train/dev, but it is the same dataset. Nothing here measures other generators, Hindi, or real
WhatsApp voice notes. Voice stays a review cue: it never clears or accuses a payee.

**Run by Claude B on the team laptop** (user-reported; Windows, Python 3.13.1, CPU), started 25 Oct 00:01 IST, on
commit 844fdd0 + B's patch (B's commit e8b4a47). Command: `python scripts/b_run_all.py --zip LA.zip --n-dev 60
--n-eval 100 --far 0.05` (seeds 1234 dev, 4321 eval). Subsets: dev 60 real + 60 spoof, eval 100 real + 100 spoof,
each base clip also as an mp3 and an Opus copy. Threshold fitted on DEV only (-4.241993, raw AASIST logit, target 5%
genuine flagged) and **not installed in the app** (`results/asvspoof/calibration_asvspoof_dev.json`). Re-computed
by Claude C from B's prediction CSVs with `scripts/make_results_rows.py`: identical. Files: `results/asvspoof/`.
Contains information from ASVspoof 2019 (https://doi.org/10.7488/ds/2555), made available under the ODC
Attribution License (https://opendatacommons.org/licenses/by/1.0/).

| Model / split (all in-distribution for AASIST) | n (real/fake) | AUC | EER | genuine flagged [95% Wilson] | synthetic missed [95% Wilson] | abstained |
|---|---|---|---|---|---|---|
| pretrained AASIST, LA dev (no threshold; AUC/EER only) | 180/180 | 0.948 | 0.150 | n/a | n/a | n/a |
| pretrained AASIST, LA eval, all codecs | 300/300 | **0.766** | **0.317** | **0.157** [0.120, 0.202] | **0.563** [0.507, 0.618] | 57 |
| LA eval, clean | 100/100 | 0.817 | 0.270 | 0.110 [0.063, 0.186] | 0.570 [0.472, 0.663] | 19 |
| LA eval, mp3 | 100/100 | 0.782 | 0.300 | 0.090 [0.048, 0.162] | 0.580 [0.482, 0.672] | 19 |
| LA eval, Opus | 100/100 | 0.701 | 0.370 | 0.270 [0.193, 0.364] | 0.540 [0.443, 0.634] | 19 |
| first 1 s of 120 clean dev clips | 60/60 | 0.752 | 0.383 | 0.150 [0.081, 0.261] | 0.533 [0.409, 0.654] | 120 |
| first 2 s | 60/60 | 0.704 | 0.300 | 0.483 [0.362, 0.607] | 0.200 [0.118, 0.318] | 70 |
| first 4 s | 60/60 | 0.945 | 0.150 | 0.067 [0.026, 0.159] | 0.233 [0.144, 0.354] | 13 |

The dev threshold did not transfer even inside LA (5% target, 15.7% genuine flagged on eval; 27% on Opus). The
"all codecs" rows count each base clip three times; the per-codec rows are the honest sample sizes.

### Cross-dataset test of VERIQ's trained voice head (Claude C, sandbox, 25 Oct 00:47 IST)

The head was trained on FSDD (real) vs Kokoro (synthetic) only. B's LA eval subset is data it never saw: a different
dataset, different speakers, 13 other synthesis systems. Scored through the product path (gate, VAD, chunks) with
the head's own threshold (0.9068, fixed on its FSDD/Kokoro dev split; not refitted). Command:
`python -m eval --input data/subsets/eval --labels data/subsets/eval/labels.csv --detector head`
(`results/asvspoof/head_v1_eval.csv`, `HEAD_V1_CROSS_DATASET_ROWS.md`).

| VERIQ head v1 | n (real/fake) | AUC | EER | genuine flagged [95% Wilson] | synthetic missed [95% Wilson] |
|---|---|---|---|---|---|
| in-domain, FSDD/Kokoro held-out test (24 Oct, for comparison) | 80/80 | 0.82 | 0.20 | 0.188 | 0.312 |
| **cross-dataset, ASVspoof 2019 LA eval, all codecs** | 300/300 | **0.457** | **0.527** | **0.540** [0.483, 0.596] | **0.507** [0.450, 0.563] |
| cross-dataset, clean | 100/100 | 0.507 | 0.500 | 0.500 [0.404, 0.596] | 0.500 [0.404, 0.596] |
| cross-dataset, mp3 | 100/100 | 0.483 | 0.490 | 0.500 [0.404, 0.596] | 0.460 [0.366, 0.557] |
| cross-dataset, Opus | 100/100 | 0.385 | 0.590 | 0.620 [0.522, 0.709] | 0.560 [0.462, 0.653] |

**It collapses to chance.** The 0.82 learned the difference between our two sources (FSDD recordings vs Kokoro),
not synthetic speech in general. Consequence, applied on 25 Oct: the head is now **off by default** in the app
(`VERIQ_VOICE_HEAD=1` turns it on only for the in-domain demo). The app's voice check therefore abstains
("can't assess") on real uploads unless a calibrated detector is installed, which we will not do on this evidence.

### Retrained voice head with grouped cross-validation (Q2 item a; Claude C, sandbox, 25 Oct 01:30 IST)

Command: `python -m bench.voice.cross_dataset --voiceset <voiceset> --asv-dev data/subsets/dev --asv-eval
data/subsets/eval --aasist external/aasist --out results/voice_xd` (`results/voice_xd/`: results.json, table.md,
per-file scores). Features: mean AASIST embedding over the product preprocessing (gate, VAD, 4 s chunks); this
mean-embedding path scores pretrained AASIST slightly differently from the product's per-chunk path (AUC 0.777 vs
0.766 above; 57 clips abstained in both). Threshold for every head: 5% genuine flagged, chosen by 5-fold GROUPED
cross-validation on that head's own training data (groups = speaker / TTS voice / ASVspoof base clip, so the three
codec copies of a clip never straddle folds). LA eval is used only for reporting.

| Head (training data) | Test set | n (real/fake) | AUC | EER | genuine flagged [95% Wilson] | synthetic caught [95% Wilson] |
|---|---|---|---|---|---|---|
| v1 as shipped (FSDD/Kokoro train) | LA eval | 276/267 | 0.474 | 0.519 | 0.533 [0.474, 0.591] | 0.509 [0.450, 0.569] |
| FSDD/Kokoro train+dev only | LA eval (other dataset) | 276/267 | 0.583 | 0.438 | 0.250 [0.203, 0.304] | 0.371 [0.315, 0.430] |
| LA dev only | FSDD/Kokoro test (other dataset) | 80/80 | 0.631 | 0.413 | 0.125 [0.069, 0.215] | 0.150 [0.088, 0.244] |
| LA dev only | LA eval (same dataset) | 276/267 | 0.865 | 0.203 | 0.094 [0.065, 0.134] | 0.678 [0.620, 0.731] |
| **v2: FSDD/Kokoro train+dev + LA dev** | **LA eval** | 276/267 | **0.832** | 0.239 | **0.051** [0.030, 0.083] | **0.438** [0.380, 0.498] |
| v2 | LA eval, Opus only | 92/89 | 0.797 | 0.276 | 0.076 [0.037, 0.149] | 0.449 [0.350, 0.553] |
| **v2** | **FSDD/Kokoro held-out test** | 80/80 | **0.836** | 0.275 | **0.075** [0.035, 0.154] | **0.400** [0.300, 0.510] |
| v2 | Hindi Kokoro voices (synthetic only) | 0/40 | n/a | n/a | n/a | 0.800 [0.652, 0.895] |

What it says: (1) every head trained on ONE source falls apart on the other source (0.583, 0.631): the voice check
learns its training data, not "synthetic speech". (2) Trained on both sources, the head keeps the 5% false-alarm target
on held-out speakers and mostly-unseen attack types of both (5.1% and 7.5%), but catches only 40 to 44% of synthetic
clips. (3) LA eval is NOT a cross-dataset test for v2 (LA dev is in its training data); no third dataset was run, and
the leave-one-dataset-out rows predict that a new source (real WhatsApp notes, Indian languages, other TTS engines) would
degrade it. Decision: v2 is exported to `bench/voice/v2/` and **not installed**. (25 Oct 03:00: per the team's Prompt 2, the app now uses pretrained AASIST with B's LA-dev threshold as a weak review cue: see C-39.)

## Rubric evidence runs (Prompt 2, message 1; Claude C's Linux sandbox, 25 Oct 03:00-03:30 IST)

| Metric | Result | Command | Data |
|---|---|---|---|
| Live journey, 5 varied inputs (C-42) | J1 English UPI + mismatched name: NAME_DISCREPANCY (as expected); **J2 UPI ID broken by spaces + amount in words: no payee found (MISS)**; J3 Hinglish account + "18% tax to withdraw": INCONCLUSIVE (as expected); J4 Devanagari, name matches: NO_MAJOR_ISSUE + "not a guarantee" (as expected); J5 payee switch to a Razorpay handle: NAME_DISCREPANCY + gateway INCONCLUSIVE (as expected) | `python scripts/live_journey.py` | 5 chats written by Claude C for this run, not tuned on |
| Mistake path, scenario D (C-41) | false alarm NAME_DISCREPANCY → overturned; **1 user click + 1 reviewer click** after the alert; app processing 0.4-0.5 s in total; human time not measured; audit trail has no raw payee ID | `python scripts/mistake_path.py` | synthetic scenario |
| Safeguards running (C-40) | after a full check through the app: 0 files on disk containing the chat text; offline mode: 0 outgoing connections; delete-my-data clears the session | `python -m pytest tests/completeness/test_safeguards_running.py` | |
| Voice weak cue (C-39) | flag → HUMAN_REVIEW; no_signal never clears; demo TTS clip with real AASIST + LA-dev threshold: **no_signal (missed)**, raw score -3.19 vs threshold -4.24 | `python -m pytest tests/completeness/test_voice_weak_cue.py` | demo clip (Kokoro TTS) |
| Blind dataset load check | **not provided**: `data/blind_ai/`, `data/names_blind/`, `data/extract_blind/`, `data/voice_scripts/` are not in this delivery (the dataset zip was not attached) | `python -m bench.datasets` | |

## Q2-Q4 measurements (25 Oct 2026, Claude C's Linux sandbox unless marked)

| Metric | Result | Command | Data |
|---|---|---|---|
| Name matcher, 97 labelled name pairs (C-34) | same firm called a discrepancy: **3/42** (Wilson 95% [0.025, 0.190]); unrelated businesses caught **36/36** ([0.904, 1.0]); non-firm name called a match: **0** | `python -m bench.names.run` | written by us after the matcher (specification check, not blind) |
| Chat benchmark after the shop-name fix (C-16) | held-out synthetic test (generated by us): **100%** (399/399), dev 100%; was **96.2%** in the first blind run (`bench/results_test_blind_24oct.json`). The fix was made after seeing those 15 failures, so 100% is not blind | `python -m bench.run test` | synthetic, generated by us |
| Red-team set after the fix | defended **32/32**, known gaps still open **3/3** (KRISHNA DAIRY FARM row now defended) | `python -m bench.adversarial` | synthetic, written by us |
| Time per chat with voice notes (deck target <= 60 s) | **2.94 s** for a 9-message chat with 3 voice notes, AASIST loaded (2-vCPU sandbox). Laptop: run by `finale_laptop.ps1` | `python scripts/time_chat_with_voice.py` | scenario A + demo clips |
| Pressure cues on UCI SMS Spam (C-35) | **not run** (download on the laptop: `finale_laptop.ps1` step 3) | `python -m bench.sms.run` | public; not UPI fraud |
| Blind teammate chats (C-36) | **not run** (chats being written) | `python -m bench.blind.run` | written blind by teammates |
| Smoke test, fresh install (C-38) | **7/7 steps pass**, 0 outgoing connections; also from an offline wheelhouse install (41 wheels, `--no-index`) | `python scripts/smoke.py`; `install_offline.sh` | Linux, Python 3.13 |
| Tests after Q2-Q5 | pinned venv without voice extras: **1109 passed, 0 failed, 7 skipped**; sandbox with voice extras + real AASIST: **1121 passed, 0 skipped**; 3 extra random orders (seeds 1, 7, 20261025): all passed | `python -m pytest`; `make reproduce` | |
| Coverage after Q2-Q5 | product code **92.8%** (pinned, no voice extras), **94.4%** (with voice extras); only product file below 85%: `app/views/kit.py` 83.8% | `python -m pytest --cov` | |
| Mutation check after Q2-Q5 | **17/17 killed** | `python scripts/mutation_check.py` | |
| Docker image | **not verified** (Docker Hub blocked in the sandbox); laptop: `finale_laptop.ps1` step 6 if Docker is installed | `docker compose build && docker compose up -d` | |

## Test quality and reproducibility (Q1, 2026-10-24, Claude's Linux sandbox unless marked user-reported)

Commit: Q1 delivery (uncommitted in the sandbox; the team commits it as `FINALE: Q1 ...`). Full table:
`results/REPRODUCE_REPORT.md`. Command for all of it: `python scripts/reproduce.py --mutation` (`make reproduce-full`).

| Metric | Result | Command | Date (IST) | Environment / data |
|---|---|---|---|---|
| Synthetic data regenerated from seeded generators | **4/4 files byte-identical** to the committed ones (bench dev/test chats, campaign cases, registry seed) | `make reproduce` | 24 Oct 22:56, re-run 23:06 | Linux, pinned venv; synthetic, generated by us |
| Full test suite, exact pins, no voice extras | **1085 passed, 0 failed, 6 skipped** (skips: torch / soundfile not installed, each reason printed) | `python -m pytest` | 24 Oct 22:56, re-run 23:06 | clean venv from `requirements-dev.txt`, Python 3.13.16 |
| Full test suite, with voice extras (torch, soundfile, sklearn, ffmpeg) | **1096 passed, 0 failed, 0 skipped** with the real AASIST weights (`VERIQ_AASIST_REPO` set); 1095 passed, 1 skipped without them | `python -m pytest` | 24 Oct | sandbox Python 3.13.16 |
| Statement coverage, product code (app, core, extract, match, parsing, registry, report, rules, voice, eval) | **92.9%** without voice extras (only file below 85%: voice/detector.py 35%, needs torch); **94.6%** with voice extras and real AASIST (no product file below 85%) | `python -m pytest --cov` | 24 Oct | test files excluded from the count |
| Statement coverage, bench/ scripts/ data/ (benchmark and tool scripts) | 65.4% (was 0% for most bench scripts before Q1) | same | 24 Oct | tool tests that start subprocesses are not counted |
| Mutation check: planted safety bugs caught | **17/17 killed** (first run: 16/17, survivor M10 "defanging broken in the reports": the old test never put a link into a report; test added, re-run killed it) | `python scripts/mutation_check.py` | 24 Oct 22:58 | pinned venv |
| Random test order (pytest-randomly) | **13 shuffled runs, 12 clean, 1 failure not reproduced.** Failing run: seed 424242 during the first `make reproduce` (1084 passed, 1 failed); the test name was not captured (tool fixed: it now records `FAILED` lines). The same seed re-run 3 times, 8 other seeds and the final `make reproduce` (seeds 20261024, 424242): all 1085 passed. Most likely cause, not proven: we edited CLAIMS.md and TESTPLAN.md during that run, and one test compares those two files. | `make reproduce` + extra seeds | 24 Oct | pinned venv |
| Chat benchmark re-run after the Q1 extractor change (Hindi account words) | identical to committed: held-out synthetic test (generated by us) 399/399 payees, 96.24%, 0/178 false alarms; dev 162/162, 100% | `python -m bench.run test` / `dev` | 24 Oct 22:56, re-run 23:06 | synthetic, generated by us; test split not used for tuning |
| Red-team set re-run | identical: 31/31 defended, 4/4 known gaps still open | `python -m bench.adversarial` | 24 Oct 22:56, re-run 23:06 | synthetic, written by us |
| Pins installable | all 41 pins have wheels for Windows Py 3.11/3.13, Linux Py 3.13, macOS arm64 Py 3.12 | `pip download --only-binary=:all: --platform ...` | 24 Oct 22:45 | PyPI |
| Laptop run of Q1 | **not run yet** (send the `reproduce.ps1` output) | `reproduce.ps1` | | Windows 11 laptop |

Bugs found by the new tests and fixed in Q1: (1) a bank account written after the Hindi words "खाता संख्या" was not
found (edge test, mixed languages); `extract/` now knows खाता / खाते / अकाउंट / संख्या / नंबर. (2) The report-defanging
test never exercised a link (mutation M10). (3) `bench/voice/make_set.py` picked FSDD files in directory order, which
differs between computers; it now sorts them (the committed voice set predates this, see REPRODUCE.md section 3).

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
| 2026-10-24 19:38 IST | see git log | FINALE: `python -m bench.voice.make_set` + `python -m bench.voice.train_eval` (520 clips, speaker/voice-disjoint, Opus, app preprocessing) | test AUC: pretrained 0.669, trained head 0.82; EER 0.35 vs 0.2; synthetic caught 15.0% vs 68.8%; genuine flagged 5.0% vs 18.8%; Hindi synthetic caught 77.5%; 0.551 s/clip. See bench/voice/README.md |
| 2026-10-24 19:38 IST | see git log | FINALE: first voice run on whole clips (not app preprocessing) | **discarded**: through the app path it flagged 71/80 genuine clips (silence artefact); retrained as above |
| 2026-10-24 19:38 IST | see git log | FINALE: `python -m pytest -q tests app registry report voice` | **988 passed** |
| 2026-10-24 21:29 IST | Q0 (uncommitted) | fresh venv (Python 3.13.16, Linux sandbox): `pip install -r requirements.txt` then `python -m pytest` | **988 passed**, 0 failed, 0 skipped |
| 2026-10-24 21:29 IST | Q0 (uncommitted) | same venv with ffmpeg removed from PATH: `python -m pytest` | **967 passed, 21 skipped** (all: "ffmpeg not installed"), 0 failed |
| 2026-10-24 21:47 IST | Q0 (uncommitted) | **user-reported**, team laptop, Windows 11, Python 3.14.5 (global interpreter, no venv): `python -m pip install -r requirements.txt` then `python -m pytest` | **967 passed, 21 skipped** (all: "ffmpeg not installed"), 0 failed, 47.5 s |
| 2026-10-24 22:03 IST | Q0 (uncommitted) | **user-reported**, team laptop, Windows 11, Python 3.11.9 **venv**, ffmpeg 9.0.2, no torch | **987 passed, 1 failed**, 177 s. Failure: `test_results_page_shows_measured_numbers`, Streamlit AppTest timed out after 30 s (a test-harness limit on a slow first run, not a wrong answer). Fixed in patch 1: timeout 180 s; results-table cells made plain text (removes an Arrow conversion fallback seen in the log). Re-run pending. |
| 2026-10-24 22:15 IST | Q0 + patch 1 (commit 80bd936, pushed) | **user-reported**, team laptop, Windows 11, Python 3.11.9 venv, ffmpeg 9.0.2, no torch | **988 passed, 0 failed, 0 skipped**, 129 s (slowest: voice eval CLI tests ~19 s each, ffmpeg start-up on Windows) |
| — | — | Windows 11 with ffmpeg + torch (voice model active) | **not run** |

The 113/114 are code tests, not accuracy numbers. Demo results are Claude A's *expected* fixture values, not a rules engine.
Chat-side and voice numbers above are on SYNTHETIC or public data (bench/README.md); say so whenever they are shown. No voice detector numbers exist yet. Do not quote any voice number in the deck.

## Claude B: voice runs (pasted from voice/B_RESULTS_ROWS.md, now docs/history/B_RESULTS_ROWS.md; nothing here is an accuracy number)

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
  - Held-out synthetic-voice test (FSDD real vs Kokoro TTS, Opus) . AUC 0.82 (pretrained 0.669), EER 0.2
  - Synthetic caught / genuine flagged ......................... 68.8% / 18.8% (review cue only)
  - Hindi synthetic (unseen language) caught .................... 77.5%
  - Seconds per clip (2-core CPU) ............................... 0.551
  - ASVspoof 2019 LA (Claude B) ................................. NOT RUN yet
LANE 2 RECIPIENT, QR & NAME MATCHING (rules, no trained model)
  - Payee extraction, held-out synthetic test (generated by us), 300 chats .. 399/399 found, 0 false pickups
  - Decisions as expected ...................................... 96.2% (384/399); named failure: given-name shop names
  - False alarms on genuine payees ............................. 0/178
  - Scam payees given "No major issue" ......................... 0/221
  - Red-team: look-alike names 6/6, genuine variants 4/4, obfuscated cues 11/11, QR payees 2/2, benign sentences 4/4
  - Known gaps: identical-name mule account, "KRISHNA DAIRY FARM", 2 reworded phrases with no keyword
LANE 3 DECISION ENGINE
  - Rules time per chat (laptop-class CPU, Linux sandbox) ...... median 0.4 ms, max ~1 ms (excludes voice)
  - End-to-end time with voice ................................. NOT RUN
```
