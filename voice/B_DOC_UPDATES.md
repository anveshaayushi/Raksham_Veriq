# Text for the shared files (Claude B does not edit shared docs; Claude C / the human merges this)

## CHANGES_REQUESTED.md additions
### CR-B1 · Claude B → Claude C · open (tests, app/tests)
With the real `voice/` package present, 3 app tests fail because they assumed no voice module / a test double on the path.
Verified on a scratch copy: with these two edits all tests pass (159 at the time of checking).
1. `app/tests/test_adapters_and_case.py::test_voice_stub_never_returns_no_signal`: drop `is_stub and` (a real `analyse()` is
   now called, so `is_stub` is correctly False). Keep `vr.state == "cant_assess" and vr.score is None`.
2. `app/tests/test_claude_b_integration.py`: the subprocess runs from the repo root, where the real `voice/` now shadows
   `app/tests/fake_b`. Put the double first: add `import sys; sys.path.insert(0, <FAKE path>)` as the first line of SCRIPT.
   Also the test named `test_upload_without_analyse_entry_point...` only holds for the double; it keeps passing once (2) is done.
### CR-B2 · Claude B → all · answered CR-C4
Entry point is `voice.analyse(file_id: str, data: bytes, filename: str) -> core.schemas.VoiceResult` (bytes, not a path).
Never raises; until `voice/calibration.json` exists for the loaded model, state is `cant_assess` with score = raw value (or null)
and threshold null. `voice.stub.stub_result` now returns contract-valid results (score and threshold present for
no_signal/flagged; the numbers are arbitrary placeholders and model_version is "stub-NOT-A-MODEL").
### CR-B3 · Claude B → Claude A · info
VoiceResult for `cant_assess` may carry a raw `score` with `threshold` null. Rules must key off `state` only, never off the score.
`.gitignore` additions needed in the repo: `external/`, `data/raw/`, `data/subsets/`, `dev/`, `out/`, `*.pth`, `voice/calibration.json` is NOT ignored (it is small and must be committed once real).

## PREBUILT.md / STATUS.md rows (finale work, built from 24 Oct 11:00 IST; log with real commit time)
voice/service.py, voice/__init__.py (analyse), voice/stub.py (contract-valid), voice/tests, voice/README.md, eval/ (veriq-eval, fit_threshold), scripts/ (datasets, make_asvspoof_subset, fetch_asvspoof_sample).
NOTE: the drafts of voice/ and eval/ existed before 24 Oct 11:00 (written 23 Oct, in veriq_claude_B.zip); the AASIST selfcheck was run on the team laptop on 23 Oct. Everything else above is finale work.

## DISCLOSURE.md rows
| AASIST (clovaai/aasist) code + pretrained weights | detector (Plan C) | repo says MIT as recalled by B: LICENSE and weights terms NOT yet read by a human | UNVERIFIED |
| ASVspoof 2019 LA | dev/test audio | ODC-By 1.0 (README.txt + LICENSE_text.txt, read 23 Oct); audio derived from VCTK, VCTK licence NOT yet checked | recorded in data/raw/asvspoof2019_la/LICENCE_CHECK.json |
| ffmpeg (Gyan.FFmpeg 9.0.2 full build) | decode / codec copies | GPL build; fine for local use, check before redistributing | UNVERIFIED |
Required notice if any ASVspoof-derived output is shown publicly: "Contains information from ASVspoof 2019 (https://doi.org/10.7488/ds/2555), made available under the ODC Attribution License (https://opendatacommons.org/licenses/by/1.0/)."

## RESULTS.md rows from B: see voice/B_RESULTS_ROWS.md

### CR-B4 · Claude B → Claude C · applied in the integrated repo, please keep
`app/tests/test_intake.py::test_bad_chat_rejected` used a 2 MB bytes value as a pytest parameter, so its test id was ~2,097,000 characters.
On Windows pytest stores the current test id in an environment variable (limit 32,767 chars) and the whole run crashed with
"ValueError: the environment variable is longer than 32767 characters". Linux has no such limit, so it passed in the sandbox.
Fix: `ids=[...]` on the parametrize (applied). Rule for everyone: never put big values in parametrize without short ids.

### CR-B5 · Claude B → Claude C · speech-to-text hook (new, optional)
`voice.transcribe.transcribe(file_id, data, filename) -> Transcript{file_id,text,language,language_probability,error,model}`; never raises.
Wire it in `app/adapters/voice.py` (or `app/case.py`) ONLY when the user did not paste a transcript: build `transcripts[media_ref] = t.text`
and pass it to the existing `extract.run(..., transcripts)` (CR-8). Cues from a transcript stay `source="voice"`, confidence never `high`.
Show the user the transcript and its language so they can correct it (Hinglish may come out in Devanagari or Latin letters). Do not store transcripts.
Status: tested with a fake model only; real model NOT run yet (needs a one-time download on the laptop).
DISCLOSURE row: | faster-whisper (+ Whisper weights, "small" by default) | speech-to-text for voice notes | licence NOT yet read by a human (believed MIT; verify) | UNVERIFIED |
