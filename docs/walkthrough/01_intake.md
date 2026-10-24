# Intake: what you upload

## Plain words
Plain words: before VERIQ reads anything, it asks your consent and checks the files are what they say they are:
a WhatsApp chat export (.txt or WhatsApp's own .zip), voice notes, screenshots. Anything odd is refused with a reason.

| | |
|---|---|
| Code | `app/intake.py`, `app/views/kit.py` (kit zips) |
| Goes in | chat .txt / WhatsApp .zip (max 2 MB chat, 60 MB zip), voice notes (.opus .ogg .m4a .mp3 .wav .aac, 20 MB each, max 10), images (.jpg .png .webp, 8 MB, max 10) |
| Comes out | accepted files with a SHA-256 fingerprint each, or a plain refusal |
| Can do | refuse wrong types, empty or oversized files, zip bombs, path tricks, encrypted zips, non-UTF-8 text |
| Cannot say | whether the content is genuine; it only checks the container |
| Tests / numbers | `app/tests/test_intake.py`, `tests/edge/test_edge_inputs.py` |
| Known limit | Legacy encodings (cp1252) are refused rather than guessed; the user must re-export. |
