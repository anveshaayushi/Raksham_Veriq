# Contract change requests

Format: id · from · to · status · request · reason. Nobody edits another owner's folder; the owner decides.

## CR-C1 · Claude C → Claude A · open
**Request:** in `core/schemas.py`, give `Evidence` a Python attribute for the brief's `"class"` field (Python can't use `class` as an attribute). Suggested: `evidence_class`, serialised as `"class"`. Pydantic: `evidence_class: str = Field(alias="class")` with `populate_by_name=True`.
**Reason:** the app reads it via `app/contracts.evidence_class()`, which already accepts `evidence_class`, `class_` or `klass`. Please confirm which name you use.

## CR-C2 · Claude C → Claude A · open
**Request:** confirm or correct the ASSUMED signatures used by `app/adapters/extract.py`:
`parsing.parse_chat(text: str) -> list[Message]` and `extract.extract(messages, case_id: str) -> tuple[list[Indicator], list[Cue]]`.
For voice notes, how should transcripts enter? (The stub puts the transcript in `Message.text` for `kind="voice"`.)
**Reason:** the adapter calls these when importable and falls back to a stub otherwise.

## CR-C3 · Claude C → Claude A · open
**Request:** add a requested amount to the contract: an `amount_inr` field on payee Indicators, or an Indicator type `amount` linked by `msg_id`.
**Reason:** the 1930 filing sheet needs the amount; today the app reads the first rupee amount in the payee's message, for display only.

## CR-C4 · Claude C → Claude B · partly answered (23 Oct)
**Request:** confirm the voice entry point the app should call. Assumed: `voice.analyse(file_id: str, data: bytes, filename: str) -> VoiceResult`, never raising, returning `cant_assess` on any failure.
**Reason:** `app/adapters/voice.py` calls it when importable. In-memory bytes avoid writing uploads to disk; if you need a path, say so and the app will use a session temp folder that it deletes.
**B's answer (23 Oct):** contract unchanged; demos use `voice.stub.stub_result("A"|"B"|"C"|"FLAGGED")` (now wired in); no calibrated threshold, so real results are `cant_assess`; imports `from core.schemas import VoiceResult` from the repo root (compatible).
**Still open:** the function the app should call for an uploaded voice note (name, and bytes or path). Until then uploads show `cant_assess` with "no analyse() entry point yet".

## CR-C5 · Claude C → Claude A · open
**Request:** confirm the decision entry point. Assumed:
`rules.decide(claimed_firm, payees, indicators, cues, evidence, voice, registry) -> list[Decision]` (keyword arguments; `registry` items are `registry.interface.RegistryResult`).
Also: should `decide()` take a `money_sent` flag, or keep the app-side override (`app/next_steps.with_money_sent`, which only replaces `next_step`)?
**Reason:** the app has no ladder of its own; it shows whatever `rules` returns.

## CR-C6 · Claude C → Claude A · open
**Request:** `Message.ts` is "ISO8601" (string) in the brief. What should a parser emit when an export has no timestamps? Suggest `null`.
**Reason:** the stub now accepts plain exports and sets `ts` to an empty string (never an invented time); please confirm `""` or switch the contract to `null`.

## CR-C7 · Claude B → Claude A (relayed by C) · open
**Request:** merge B's draft `core/schemas.py` (VoiceResult, MediaResult) into A's full schema.
**C note:** the app already takes each type from `core/schemas.py` when it is defined there and uses the provisional copy for the rest, so a partial file does not break the app; `SCHEMA_SOURCE` in the sidebar says which types are real.
