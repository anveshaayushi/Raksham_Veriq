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

## Speech-to-text (branch claude-b-voice-results; added 25 Oct 2026)
| Item | Licence | How verified |
|---|---|---|
| faster-whisper 1.2.1 (SYSTRAN), Python package | MIT | package metadata (`pip show faster-whisper`) and the LICENSE file in github.com/SYSTRAN/faster-whisper, read 25 Oct |
| OpenAI Whisper code and model weights | MIT | github.com/openai/whisper README: "Whisper's code and model weights are released under the MIT License", read 25 Oct |
| CTranslate2 conversions downloaded by faster-whisper (Hugging Face `Systran/faster-whisper-<size>`) | converted from the MIT Whisper weights; the model card's own licence line was NOT checked (Hugging Face not reachable from our build sandbox) | check the model card on the laptop before quoting |
