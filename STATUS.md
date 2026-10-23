# STATUS (updated by the human after each handoff; Claude A's lines below)

Legend: not started / in progress / merged / tested

## Claude A
- core/schemas.py (contract + provisional types): **tested** (45 golden/schema tests pass in the sandbox)
- fixtures/ scenarios A, B, C + synthetic SEBI snapshot: **tested** (validator + mutation tests)
- core/validate.py (fixture validator): **tested**
- WhatsApp parser + validation (Android, iPhone, zip safety, hashes): not started
- Regex extractor + pressure cues: not started
- Name matcher + exclusion classes: not started
- v0 decision ladder + truth table + property tests: not started
- Image OCR / QR extraction: not started (after the core flow)
- Video: **out of scope** (rejected at validation)

## Claude B (as reported to C on 23 Oct)
- AASIST runs on CPU; no calibrated threshold, so real results are `cant_assess`: **in progress**
- `voice/stub.py` `stub_result("A"|"B"|"C"|"FLAGGED")`: reported; C's app calls it for demos
- Entry point for uploaded voice notes (CR-C4): **open**

## Claude C
- Streamlit app (consent, upload, confirm firm, user-reported payee names, per-payee answer, money toggle): **tested** against A's contract and golden fixtures
- Filing sheet + redacted summary (HTML, Markdown): **tested**
- Registry interface + stub + keyed HMAC helper: **tested**
- Adapters to A's parser/extractor/rules and B's voice: **merged** (labelled stubs until those exist)
- SQLite registry, campaign graph, reviewer console: not started (P2)
- Windows run script (`app/run_app.ps1`): written, **not run**
