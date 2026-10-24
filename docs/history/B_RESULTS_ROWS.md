# RESULTS rows from Claude B (for C / the human to paste into RESULTS.md). Nothing here is an accuracy number.

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
