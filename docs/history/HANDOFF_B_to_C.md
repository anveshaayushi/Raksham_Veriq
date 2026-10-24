# Handoff: Claude B (voice + eval) -> Claude C (integration)
Date: 24 Oct 2026. Repo state: C delivery 1 + B folders + CR-B1/CR-B4 test fixes.
Verified on the team Windows laptop: `python -m pytest -q tests app registry report voice` -> exit code 0 (172 tests).

## What B delivers (all in this zip)
- `voice/` : `voice.analyse(file_id, data: bytes, filename) -> core.schemas.VoiceResult`. Never raises.
  Until `voice/calibration.json` exists for the loaded model, every real result is `cant_assess` (raw score kept, threshold null).
  `no_signal` means "no signal found", never "genuine". A voice score never clears or accuses a payee.
- `voice/stub.py` : contract-valid placeholders (model_version "stub-NOT-A-MODEL"). Never show the numbers.
- `eval/` : `python -m eval --input <folder> --out out\preds.csv [--json] [--labels labels.csv]` (veriq-eval).
  `python -m eval.fit_threshold` fits a threshold on DEV only.
- `scripts/` : `datasets.py` (licence log), `make_asvspoof_subset.py`, `fetch_asvspoof_sample.py`. Nothing is downloaded automatically.
- `voice/B_DOC_UPDATES.md` : exact text for CHANGES_REQUESTED / PREBUILT / STATUS / DISCLOSURE. `voice/B_RESULTS_ROWS.md` : RESULTS rows.

## What C must do
1. Keep the CR-B1 and CR-B4 edits in `app/tests/` (they are applied here). Never put big values in pytest parametrize without short `ids=`.
2. Paste the text from `voice/B_DOC_UPDATES.md` into the shared docs (B does not edit them).
3. Commit with prefix `FINALE:`; never rebase/amend/force-push; never move the `v0-prebuilt` tag.
4. Call `voice.analyse(media_ref, bytes, filename)`; `VoiceResult.file_id` must equal `Message.media_ref`. Key decisions off `state`, never off `score`.
5. Do not put any voice accuracy number in the deck until RESULTS.md has a re-runnable command with date and commit.

## NOT done / not run (do not claim)
- No accuracy measured (EER/AUC) on any dataset. No calibrated threshold. No timing per clip. No per-codec / per-language results.
- No non-ASVspoof dataset tested. Pretrained AASIST was trained on ASVspoof 2019 LA, so LA results flatter it.
- AASIST code/weights licence and VCTK licence not yet read by a human. ffmpeg GPL build: check before redistributing.
- AMR-NB codec path untested (encoder missing in B's sandbox). Speaker consistency, speech-to-text, bilingual evidence-card text: not built (Pack B3/B4).
- Claude A's delivery (rules/extract/parsing) does not match the frozen `core/schemas.py`; A must rewrite against the repo's real schema.

## B's next steps (laptop, in order)
1. `set VERIQ_AASIST_REPO=<...>\external\aasist` then `python -m voice.detector --selfcheck`.
2. Locate extracted ASVspoof LA; `python scripts\make_asvspoof_subset.py --root %LAROOT% --split dev --n-real 60 --n-fake 60 --codecs opus,mp3 --out data\subsets\dev`.
3. `python -m eval --input data\subsets\dev --out out\asv_dev.csv --labels data\subsets\dev\labels.csv` ; read `out\asv_dev.summary.json`.
4. Fit threshold on dev, test on a separate eval subset, record real numbers in RESULTS.md.
5. Test on a non-LA dataset (test only) after checking its licence and size.
