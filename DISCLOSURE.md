# DISCLOSURE

All AI-generated content, datasets, models, libraries and third-party assets. Every role appends here.

## AI assistance
- Claude (Anthropic) drafted code, tests and documentation for this project; the team reviews it. Model/version per session to be noted by the team.

## Data
- All fixture data from Claude A is **synthetic**: fictional names, UPI IDs, accounts, phone-free chats, and SEBI registration numbers with a `DEMO` marker.
- `fixtures/reference/sebi_snapshot_synthetic.json` is **not** the real SEBI list.
- No real chats, voices, bank, customer or platform data is used.
- Voice results in fixtures are **stub values**, not measurements.

## Libraries (Claude A, so far)
| Library | Use | Licence |
|---|---|---|
| Python standard library | schemas, validation | PSF |
| pytest | tests | MIT (not re-verified here; check before the final appendix) |

## Claude C (app, registry, report)
- All files under `app/`, `registry/`, `report/` and C's entries in the shared Markdown files were drafted by Claude acting
  as "Claude C", then run and tested; the team reviews them.
- Demos use Claude A's synthetic fixtures. The stub upload path never produces NO_MAJOR_ISSUE and never shows a voice score.
- No external services are called. Run Streamlit with `--browser.gatherUsageStats false` to disable its telemetry
  (the run scripts do).

| Library | Use | Licence |
|---|---|---|
| Streamlit | app UI | Apache-2.0 |
| OpenCV (`opencv-python-headless`), FINALE | reading UPI QR codes in uploaded images (no model download) | Apache-2.0 |
| pytest | tests | MIT |
| Python standard library (`zipfile`, `hashlib`, `hmac`, `html`, `re`) | intake, hashing, escaping | PSF |

## Not yet used / not yet verified
- OCR and QR libraries (to be chosen; licence to be recorded when added).
- IFSC dataset, real SEBI list snapshot: not downloaded.

## Claude B (voice), merged by Claude C

| Asset | Use | Licence | Status |
|---|---|---|---|
| AASIST (clovaai/aasist) code + pretrained weights | detector (Plan C) | repo says MIT as recalled by B: LICENSE and weights terms NOT yet read by a human | UNVERIFIED |
| ASVspoof 2019 LA | dev/test audio | ODC-By 1.0 (README.txt + LICENSE_text.txt, read 23 Oct); audio derived from VCTK, VCTK licence NOT yet checked | recorded in data/raw/asvspoof2019_la/LICENCE_CHECK.json |
| ffmpeg (Gyan.FFmpeg 9.0.2 full build) | decode / codec copies | GPL build; fine for local use, check before redistributing | UNVERIFIED |

Required notice if any ASVspoof-derived output is shown publicly: "Contains information from ASVspoof 2019 (https://doi.org/10.7488/ds/2555), made available under the ODC Attribution License (https://opendatacommons.org/licenses/by/1.0/)."

## Claude C voice training (finale, 2026-10-24)
| Asset | Use | Licence | Status |
|---|---|---|---|
| Free Spoken Digit Dataset (FSDD), Z. Jackson et al., github.com/Jakobovski/free-spoken-digit-dataset | real-speech clips for train/dev/test; demo clip `app/demo_media/demo_voice_real_human.wav` (derived) | CC BY-SA 4.0 (attribution + share-alike for derived clips) | downloaded 12 Oct 2026 (public), clips generated 24 Oct |
| Kokoro-82M TTS model (hexgrad) + voices file | synthetic-speech clips; demo clip `demo_voice_synthetic_tts.wav` | Apache-2.0 | downloaded 12 Oct 2026 (public), clips generated 24 Oct |
| kokoro-onnx (Python package) | runs Kokoro on CPU | MIT (as recalled; verify) | UNVERIFIED |
| scikit-learn | logistic-regression head | BSD-3-Clause | |
| VERIQ voice head (`bench/voice/head.json`) | trained on-site on AASIST embeddings | team's own | trained 24 Oct (custom, on top of off-the-shelf AASIST) |

## Q1: every Python package, with its licence (read 24 Oct 2026 from the installed packages' own metadata)

Runtime pins (`requirements.txt`, from the laptop's clean venv) and test tools (`requirements-dev.txt`). Licence text is what each
package declares in its metadata (`License-Expression`, else its licence classifier); we did not audit transitive notices.

| Package | Version | Declared licence | Why we need it |
|---|---|---|---|
| altair | 6.3.0 | BSD License | Streamlit charts (dependency) |
| anyio | 4.15.1 | MIT | dependency of the above |
| attrs | 26.1.0 | MIT | dependency of the above |
| certifi | 2026.10.23 | Mozilla Public License 2.0 (MPL 2.0) | dependency of the above |
| charset_normalizer | 3.5.2 | MIT | dependency of the above |
| click | 8.5.0 | BSD-3-Clause | dependency of the above |
| colorama | 0.4.6 | BSD License | dependency of the above |
| h11 | 0.16.0 | MIT License | dependency of the above |
| idna | 3.20 | BSD-3-Clause | dependency of the above |
| iniconfig | 2.3.1 | MIT | dependency of the above |
| itsdangerous | 2.2.0 | BSD License | dependency of the above |
| jinja2 | 3.1.6 | BSD License | dependency of the above |
| jsonschema-specifications | 2025.9.1 | MIT | dependency of the above |
| jsonschema | 4.26.0 | MIT | dependency of the above |
| MarkupSafe | 3.0.4 | BSD-3-Clause | dependency of the above |
| narwhals | 2.27.1 | MIT | dependency of the above |
| numpy | 2.4.6 | BSD-3-Clause AND 0BSD AND MIT AND Zlib AND CC0-1.0 | arrays (voice, QR) |
| opencv-python-headless | 5.0.0.93 | Apache Software License | QR codes in images |
| packaging | 26.3 | Apache-2.0 OR BSD-2-Clause | dependency of the above |
| pandas | 3.1.0 | BSD-3-Clause | Streamlit tables |
| pillow | 13.0.0 | MIT-CMU | dependency of the above |
| pluggy | 1.7.0 | MIT License | dependency of the above |
| protobuf | 7.36.2 | 3-Clause BSD License | dependency of the above |
| pyarrow | 26.0.0 | Apache-2.0 | Streamlit tables |
| pydeck | 0.9.3 | Apache License 2.0 | dependency of the above |
| pygments | 2.21.0 | BSD-2-Clause | dependency of the above |
| pytest | 9.1.1 | MIT | tests |
| python-dateutil | 3.0.0 | BSD License; Apache Software License | dependency of the above |
| python-multipart | 0.0.32 | Apache-2.0 | dependency of the above |
| referencing | 0.37.0 | MIT | dependency of the above |
| requests | 2.34.2 | Apache Software License | dependency of the above |
| rpds-py | 2026.9.1 | MIT | dependency of the above |
| six | 1.17.0 | MIT License | dependency of the above |
| starlette | 1.10.0 | BSD-3-Clause | dependency of the above |
| streamlit | 1.66.1 | Apache-2.0 | app UI |
| typing-extensions | 4.16.0 | PSF-2.0 | dependency of the above |
| tzdata | 2026.5 | Apache-2.0 | dependency of the above |
| urllib3 | 2.8.0 | MIT | dependency of the above |
| uvicorn | 0.54.0 | BSD-3-Clause | dependency of the above |
| watchdog | 6.0.0 | Apache Software License | dependency of the above |
| websockets | 17.3 | BSD-3-Clause | dependency of the above |
| coverage | 7.17.0 | Apache-2.0 | coverage measurement |
| pytest-cov | 7.1.0 | MIT | coverage in pytest |
| pytest-randomly | 5.0.0 | MIT | random test order |

Voice extras (`requirements-voice.txt`; versions are the sandbox's, used for the committed voice results; laptop pins pending):

| Package | Version | Declared licence | Why we need it |
|---|---|---|---|
| torch | 2.14.1 | Apache-2.0 AND Apache-2.0 WITH LLVM-exception AND BSD-2-Clause AND BSD-3-Clause AND BSL-1.0 AND MIT | runs AASIST |
| torchaudio | 2.11.0 | BSD License | resampling when building the voice set |
| soundfile | 0.14.0 | BSD License | reading/writing WAV in bench/voice |
| scikit-learn | 1.9.1 | BSD-3-Clause | training the voice head |
| scipy | 1.18.1 | BSD License | scikit-learn dependency |
| onnxruntime | 1.29.0 | MIT License | runs Kokoro TTS (voice set build only) |
| kokoro-onnx | 0.6.1 | not declared in its metadata: UNVERIFIED | Kokoro TTS wrapper (voice set build only) |

Licence notes: certifi (MPL-2.0) is used unmodified as a dependency of requests. ffmpeg is a separate program
called on the command line (laptop: Gyan.FFmpeg 9.0.2 full build, GPL), not linked or redistributed by us.

## Q1: models and datasets (status updated)

| Asset | Licence | How verified | Used for |
|---|---|---|---|
| AASIST code + pretrained weights (clovaai/aasist, commit a04c9863) | MIT, Copyright (c) 2021-present NAVER Corp. | LICENSE file read in the cloned repository on 24 Oct 2026 (sandbox); the weights ship inside that repository | voice detector base model |
| Free Spoken Digit Dataset (commit 26eb9aaf) | CC BY-SA 4.0 | README.md "License" section of the cloned repository read on 24 Oct 2026 (sandbox) | real-speech clips; derived clips must keep CC BY-SA attribution |
| Kokoro-82M model files (kokoro-v1.0.onnx, voices-v1.0.bin) | Apache-2.0 | as recorded by the team on 24 Oct (model card); NOT re-read in Q1 | synthetic-speech clips (our generation) |
| ASVspoof 2019 LA | ODC-By 1.0 (B, 23 Oct) | README + LICENSE_text read by B | NOT USED YET (Q2) |

## Q1: AI assistance

Claude (Anthropic) wrote the Q1 code, tests and documents in this delivery (REPRODUCE.md, TESTPLAN.md, scripts/reproduce.py,
scripts/mutation_check.py, tests/completeness/, tests/edge/, pinned requirement files) and ran them in a Linux sandbox; the team
ran the install and test suite on the laptop and reported the output. The team reviews and commits every delivery.

## Q2-Q5 (25 Oct 2026)

| Asset | Use | Licence | Status |
|---|---|---|---|
| ASVspoof 2019 LA (dev and eval subsets, Claude B's run) | voice evaluation; head v2 training (dev only) | ODC-By 1.0 | audio kept on the team laptop, not in git; required notice: "Contains information from ASVspoof 2019 (https://doi.org/10.7488/ds/2555), made available under the ODC Attribution License (https://opendatacommons.org/licenses/by/1.0/)." ASVspoof audio is derived from VCTK: VCTK licence NOT checked by us |
| UCI SMS Spam Collection | pressure-cue false-alarm check | as shown on the UCI page (recorded by `finale_laptop.ps1` in `results/laptop/sms_readme.txt`) | NOT downloaded by Claude (no access); laptop only |
| Blind teammate chats (`data/blind/`) | blind chat evaluation | the team's own writing, fictional details | pending |
| Name-pair set (`bench/names/name_pairs.csv`) | name-matcher evaluation | ours; fictional firms written by Claude C | |
| python:3.11.9-slim-bookworm (Docker base image) | container | Python PSF; Debian packages under their own licences; ffmpeg from Debian (LGPL/GPL build) | Dockerfile written, image not built by us |

Code written by Claude (Anthropic) in this phase: `bench/voice/cross_dataset.py`, `bench/names/`, `bench/sms/`, `bench/blind/`,
`eval/kit.py` and the kit/head options in `eval/cli.py`, `app/views/` (kit, scenario player, privacy, plan),
`app/config.py`, results-page additions, `scripts/` (smoke, acceptance, plan_vs_delivered, make_slide,
make_offline_bundle, time_chat_with_voice), install and run scripts, Dockerfile, docker-compose.yml, `docs/`, and the
Markdown documents. Claude B's `scripts/b_run_all.py`, `scripts/make_results_rows.py`, updated
`scripts/make_asvspoof_subset.py` and `tests/voice_eval/test_subset_zip_and_rows.py` are merged unchanged.

## Code provenance (what we wrote vs third-party), 25 Oct 2026
- Written for VERIQ (by Claude A/B/C under the team's direction, run and committed by the team): everything under
  `app/`, `core/`, `parsing/`, `extract/`, `match/`, `rules/`, `registry/`, `report/`, `voice/`, `eval/`, `bench/`,
  `scripts/`, `tests/`, `fixtures/`, `data/synthetic/`, `docs/` and the root documents. See ENGINEERING_WALKTHROUGH.md.
- Third-party code is NOT copied into the repository. It is installed or downloaded at run time: Python packages
  (requirements*.txt, licences above), ffmpeg (separate program), AASIST code + weights (cloned into `external/aasist`,
  git-ignored, MIT), Kokoro model files (downloaded, Apache-2.0). `voice/detector.py` imports AASIST's `Model` class
  from that clone; it does not contain AASIST code.
- AI-generated blind datasets (Prompt 2): to be generated in a SEPARATE Claude chat that never saw this repository,
  committed with their generation code (`generation/`) BEFORE any scoring run, and labelled "AI-generated blind set,
  n=.., written by <model>, <date>". Not in this delivery (not attached): status "not provided".

