# HANDOFF_B_FINAL (Claude B -> Claude C), 25 Oct 2026

The ASVspoof run FINISHED on the team laptop (Windows, Python 3.13.1, CPU), started 2026-10-25 00:01 IST, all steps PASS (user-reported log: `results/asvspoof/b_run_all.log`).
Run on top of C's commit 844fdd0 plus the uncommitted B patch. Numbers below are copied from that log and from `results/asvspoof/B_RESULTS_ROWS_ASVSPOOF.md`.

## What B added on top of delivery 6 (all in `scripts/`, tested in `tests/voice_eval/`)
| file | what it does | verified |
|---|---|---|
| `scripts/make_asvspoof_subset.py --zip LA.zip` | builds a seeded, labelled, codec-augmented subset reading clips straight from LA.zip (no 7 GB extraction) | tested on a mock zip (synthetic audio); **not yet run on the real zip** |
| `scripts/b_run_all.py --zip LA.zip` | one command: selfcheck, dev subset, eval subset, score dev, fit threshold on dev only, score eval, length sweep (1/2/4 s), rows, bundle | flow tested end to end with a FAKE detector in a Linux sandbox (plumbing only); real run: PASS on the laptop, see "After the run" |
| `scripts/make_results_rows.py` | recomputes AUC, EER, genuine-flagged and synthetic-missed with Wilson 95% intervals from the predictions CSVs; needs no model and no audio | unit-tested |
| `tests/voice_eval/test_subset_zip_and_rows.py` | tests for the above | passes (33 in `tests/voice_eval`) |

## Why C needs NO big download
The 7.6 GB LA.zip stays on the laptop. `python scripts/b_run_all.py --zip <LA.zip>` produces `out/veriq_B_results_bundle.zip` (tens of MB):
the labelled clips (dev, eval, length-trimmed), every predictions CSV, the summaries, the dev-fitted threshold file, `MANIFEST.json` with sha256, and the ODC-By notice.
The human sends that one zip to C. C unzips it inside the repo root and can then, with no network:
1. Re-run the rows: `python scripts/make_results_rows.py --run dev:results/asvspoof/asv_dev.csv --run eval:results/asvspoof/asv_eval.csv --command "python scripts/b_run_all.py" --out out/rows.md` (CSV only).
2. **Test C's own trained head on unseen data** (C's Q2(a)): the bundle's `data/subsets/eval` is data the head never saw (it was trained on FSDD vs Kokoro). Score it with the app's head adapter and report cross-dataset numbers next to the in-domain 0.82. If it collapses, say so; voice stays a review cue.
3. Re-run B's AASIST scoring only if AASIST weights are present: `python -m eval --input data/subsets/eval --labels data/subsets/eval/labels.csv --out out/again.csv`.
Small committed copy (no audio, no local paths): `results/asvspoof/` after the human commits.

## Decisions B made (change them only with a reason)
- **The fitted threshold is NOT installed as `voice/calibration.json`.** It is `results/asvspoof/calibration_asvspoof_dev.json`. Reason: it is fitted on one dataset (ASVspoof LA dev) and C already measured that a dev threshold did not transfer (18.8% genuine flagged vs a 5% target). Installing it would make `voice.analyse()` start returning `flagged`/`no_signal` for real uploads. Install only after a cross-dataset test shows an acceptable genuine-flagged rate; until then the app keeps abstaining (`cant_assess`) on raw AASIST.
- The `dev` run is scored without a threshold on purpose, so it shows all clips as abstained; use its AUC/EER only.
- Pretrained AASIST was TRAINED on ASVspoof 2019 LA, so LA numbers are in-distribution and flatter it. Label them that way everywhere (the rows file says so automatically). The honest test for the *head* is cross-dataset; for pretrained AASIST it needs another dataset (In-the-Wild, MLAAD, Hindi) which is NOT downloaded and NOT run.
- Short clips: the gate returns `cant_assess` under 1.0 s of speech (provisional). The length sweep (first 1/2/4 s of the same dev clips) gives the first evidence for choosing that cutoff; the cutoff itself is unchanged until the numbers are read.

## Not done / not run
- No result on any dataset other than ASVspoof LA (pending run) and C's FSDD/Kokoro set. No In-the-Wild, MLAAD, Hindi, LibriSpeech/VCTK runs.
- AASIST code/weights licence and VCTK licence not read by a human. ASVspoof LA is ODC-By 1.0 (recorded 23 Oct). Do not commit ASVspoof-derived audio; the bundle is for team use only.
- Speaker consistency, speech-to-text, bilingual evidence-card text, seconds per clip on the final path: not built / not measured by B (C measured 0.551 s per clip for its head path).
- Q1, Q3, Q4, Q5 of the Final Fix Prompt are C's.

## Exact human steps (Windows laptop, `cmd`, repo `C:\veriq_work\veriq`)
```
tar -xf C:\Users\anves\Downloads\veriq_B_final_patch.zip
set VERIQ_AASIST_REPO=C:\Users\anves\Downloads\veriq_claude_B\veriq\external\aasist
python -m pytest -q tests/voice_eval
python scripts\b_run_all.py --zip C:\Users\anves\Downloads\LA.zip
python scripts\make_results_rows.py --help
git add -A
git commit -m "FINALE: B ASVspoof evaluation runner, results, handoff"
git log -1 --format=%h
```
Then send C: `out\veriq_B_results_bundle.zip`, the commit hash, and `results\asvspoof\b_run_all.log`.

## After the run: results (pretrained AASIST, ASVspoof 2019 LA subsets, seeds 1234 dev / 4321 eval)
Command: `python scripts\b_run_all.py --zip LA.zip` (dev 60 real + 60 fake, eval 100 real + 100 fake, each also as opus and mp3 copies, so 3 versions of every clip).
Selfcheck model: `aasist-pretrained@51d2d9cf0738`. Threshold fitted on DEV only: -4.241993 (target 5% genuine flagged; on dev it flagged 4.4% of 180 genuine clips).

| set | n | AUC | EER | genuine flagged | synthetic missed | abstained |
|---|---|---|---|---|---|---|
| dev, all (no threshold applied) | 360 | 0.948 | 0.150 | n/a | n/a | n/a (uncalibrated) |
| **eval, all** (held out) | 600 | **0.766** | **0.317** | **0.157** | **0.563** | 57 |
| eval, clean | 200 | 0.817 | 0.270 | 0.110 [0.063, 0.186] | 0.570 [0.472, 0.663] | 19 |
| eval, mp3 | 200 | 0.782 | 0.300 | 0.090 [0.048, 0.162] | 0.580 [0.482, 0.672] | 19 |
| eval, opus | 200 | 0.701 | 0.370 | 0.270 [0.193, 0.364] | 0.540 [0.443, 0.634] | 19 |

First N seconds of the same 120 clean dev clips, scored with the dev threshold:
| length | AUC | EER | genuine flagged | synthetic missed | abstained |
|---|---|---|---|---|---|
| 1 s | 0.752 | 0.383 | 0.150 | 0.533 | 120 of 120 |
| 2 s | 0.704 | 0.300 | 0.483 | 0.200 | 70 of 120 |
| 4 s | 0.945 | 0.150 | 0.067 | 0.233 | 13 of 120 |

### What this says (plain words, no spin)
- The dev number (AUC 0.95) is the easy one: AASIST was trained on this dataset, and dev contains the same attack types as its training set. The held-out eval split, which has attack types the model never saw (as far as B knows: attacks A07 to A19), drops to AUC 0.77 / EER 0.32. That drop happens WITHIN the dataset the model was trained on, so expect worse on other datasets. Not yet tested on any.
- **The dev-fitted threshold did not transfer, even inside LA:** target 5% genuine flagged, got 15.7% on eval (27% on opus-compressed clips). It also missed 56% of synthetic clips. This confirms the decision not to install a threshold in the app. Voice remains a review cue; it must never be shown as proof either way.
- Short clips: 1 s and 2 s results are unreliable (every 1 s clip abstained; at 2 s the threshold flagged 48% of genuine clips). 4 s looks much better, BUT many ASVspoof clips are shorter than 4 s, so "first 4 s" is often the whole clip, and n is only 120 (60 real + 60 fake), so the intervals are wide. Provisional suggestion: raise the minimum speech from 1.0 s towards 3 to 4 s. B has NOT changed the gate; decide after looking at the numbers.
- Sample caveat: each base clip appears three times (clean, mp3, opus), so the "all" rows overstate independent evidence (200 base clips in eval, 120 in dev). The per-codec rows (100 real + 100 fake each) are the honest sample sizes. Wilson intervals are in `results/asvspoof/`.
- C's head (AUC 0.82 on FSDD vs Kokoro) and B's AASIST on LA (AUC 0.77 on held-out eval) are on different data. Do not put them side by side as one number.
- Still unknown: other datasets (In-the-Wild, MLAAD, Hindi), real WhatsApp voice notes, other languages.

## Five questions a judge may ask B, with honest answers
1. *Does it detect deepfakes?* Partly. On held-out ASVspoof 2019 LA clips: AUC 0.77, EER 0.32; it missed 56% of synthetic clips at the dev threshold and flagged 16% of genuine ones. The model was trained on this dataset, so treat it as a ceiling. Other datasets: not run.
2. *Why not a calibrated threshold in the app?* One-dataset thresholds did not transfer; we abstain instead of guessing.
3. *What if the voice note is 0.5 s?* `cant_assess`, with the reason; never a guess.
4. *Can a voice score clear a payee?* No. Voice only escalates to human review; `no_signal` never means genuine.
5. *Can I reproduce it?* `python scripts/b_run_all.py --zip LA.zip`, seeds 1234 (dev) and 4321 (eval) fixed; needs the dataset and AASIST weights.

## Addendum (25 Oct, B): the rest of the voice work in one command
`python scripts\b_finish_all.py` (run after `b_run_all.py`): length sweep 0.1 to 6 s on the held-out eval clips, a faster-whisper sample, the Hinglish own set, and an In-the-Wild probe (lists files and sizes, downloads nothing).
Each step is independent and the report `results/asvspoof/B_FINISH_REPORT.md` says PASS / FAIL / SKIP per step. Read that file before quoting anything.
- `voice/transcribe.py` (faster-whisper): tested with a fake model; real-model status is in B_FINISH_REPORT.md. See CR-B5 in `voice/B_DOC_UPDATES.md` for how the app should call it.
- `scripts/hinglish_build.py`: 12 invented Hindi/Hinglish sentences; teammates record them (consent), Kokoro makes the fakes. Tiny set: behaviour, not accuracy.
- Not done: MLAAD (no Hindi, CC-BY-NC, gated), SEA-Spoof (licence unstated, release may not be live), In-the-Wild scoring (probe only; licence disagreement between its HF card CC-BY-SA-4.0 and demo page Apache-2.0), speaker consistency, bilingual evidence-card text.
