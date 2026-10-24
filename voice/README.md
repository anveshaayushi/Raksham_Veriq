# voice/ (Claude B): synthetic-voice cue

PLAIN WORDS: this looks at a voice note and says "possible manipulation cues (review a human)", "no signal found
(this does NOT mean the voice is genuine)" or "can't assess" (clip unusable, or no calibrated threshold yet).
It never decides whether a payee is safe or fraudulent.

TECHNICAL: ffmpeg -> 16 kHz mono -> energy VAD -> quality gate -> 4 s chunks -> pretrained AASIST (Plan C) ->
mean score -> threshold from `voice/calibration.json` (must match the model's `model_version`) -> three-state
`core.schemas.VoiceResult`. Entry point for the app: `voice.analyse(file_id, data: bytes, filename)`; never raises.

## Status (honest)
- Code and tests: run, see RESULTS.md rows from B.
- AASIST model: loaded once on the team laptop with `python -m voice.detector --selfcheck` (plumbing only).
- Calibrated threshold: NONE yet, so every real result is `cant_assess` (raw score kept, threshold null).
- Accuracy: NOT MEASURED. No voice number belongs in the deck until RESULTS.md has a re-runnable command for it.
- Speed per clip: not measured in the test environment (no model there). Measure on the laptop (below).

## Install on Windows (offline after the downloads)
1. ffmpeg on PATH (`winget install Gyan.FFmpeg`, then a NEW terminal). Check: `ffmpeg -version`.
2. `pip install -r voice\requirements.txt` and CPU torch: `pip install torch --index-url https://download.pytorch.org/whl/cpu`
3. Model code + weights, stored locally (not in git): `git clone https://github.com/clovaai/aasist external\aasist`, then put the
   published pretrained weights at `external\aasist\models\weights\AASIST.pth`. Read the repo LICENSE and README for the
   weights' terms before use. Or point elsewhere: `set VERIQ_AASIST_REPO=C:\path\to\aasist`.
4. Check: `python -m voice.detector --selfcheck`  -> prints `loaded. model_version=aasist-pretrained@<hash>`.

## Run one clip
    python -m voice path\to\clip.opus
Prints the VoiceResult JSON. Time it: `powershell -Command "Measure-Command { python -m voice clip.opus }"` (includes ~seconds of model load).

## Calibration (finale work)
`eval\fit_threshold.py` writes `voice\calibration.json` from DEV scores only. See SETUP in scripts/ and RESULTS.md.
Threshold file is refused if its `model_version` differs from the loaded weights.
