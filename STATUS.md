# STATUS (updated by the human after each handoff; Claude A's lines below)

Legend: not started / in progress / merged / tested

## Claude A
- core/schemas.py (contract + provisional types): **tested** (45 golden/schema tests pass in the sandbox)
- fixtures/ scenarios A, B, C + synthetic SEBI snapshot: **tested** (validator + mutation tests)
- core/validate.py (fixture validator): **tested**
- FINALE: WhatsApp parser (Android, iPhone, multi-line, system lines, day/month order): **tested** (ported to the contract by C, CR-C13)
- FINALE: extractor (payees, IFSC, SEBI no., phone, URL, firm name, amounts, hard/soft cues): **tested** (CR-C13)
- FINALE: name matcher with exclusion classes (gateway, personal name, initials, near spelling): **tested** (CR-C13)
- FINALE: decision ladder + evidence builder + SEBI snapshot check + truth table/property tests: **tested** (CR-C13)
- Image OCR / QR extraction: not started (after the core flow)
- Video: **out of scope** (rejected at validation)

## Claude B (merged by C, 2026-10-24 15:38 IST; see HANDOFF_B_to_C.md)
- FINALE: `voice.analyse(file_id, data, filename)`: ffmpeg decode, quality gate, AASIST, three states, never raises: **merged, tested** (synthetic noise + fake detector; not accuracy)
- `voice/stub.py`: contract-valid placeholders ("stub-NOT-A-MODEL"): **merged**
- FINALE: `eval/` (veriq-eval, metrics, fit_threshold), `scripts/` (dataset licence log, ASVspoof subset): **merged**; subset script tested only on a mock folder
- AASIST selfcheck on the team laptop (23 Oct): loads. Calibrated threshold, EER/AUC, seconds per clip: **not run**
- ASVspoof 2019 LA download: in progress / extraction not confirmed. Speaker consistency, speech-to-text: not built

## Claude C
- Streamlit app (consent, upload, confirm firm, user-reported payee names, per-payee answer, money toggle): **tested** against A's contract and golden fixtures
- Filing sheet + redacted summary (HTML, Markdown): **tested**
- Registry interface + stub + keyed HMAC helper: **tested** (pre-built)
- FINALE: SQLite registry (keyed hashes, independent-reporter linking, reviewer confirm/reject, rate limits, burst
  defence, gateway exclusion, "unavailable" on failure) + synthetic seed: **tested** (17 tests)
- Adapters to A's parser/extractor/rules and B's voice: **merged** (labelled stubs until those exist)
- Campaign graph, reviewer console: not started (C4)
- Windows run script (`app/run_app.ps1`): written, **not run**
