# Voice notes: a review cue, never proof

## Plain words
Plain words: a voice note is converted (ffmpeg), checked for enough clear speech, and scored by AASIST, a public
deepfake detector. On the public ASVspoof benchmark it misses about half of unseen attacks, and our own trained add-on
fell to chance on new data. So in the app a voice note today mostly says "can't assess". Even when a calibrated detector
flags a note, the payee only goes to human review; a voice result can never clear a payee.

| | |
|---|---|
| Code | `voice/` (Claude B), `app/adapters/voice*.py`, `bench/voice/` |
| Goes in | one audio or video file |
| Comes out | flagged / no_signal / can't assess, with reasons; never crashes |
| Can do | refuse short, silent, clipped or corrupt audio; raise a review cue when calibrated |
| Cannot say | real or fake for certain; anything about who is speaking |
| Tests / numbers | `voice/tests`, `tests/voice_eval`, `tests/completeness/test_voice_*.py`; results: RESULTS.md (ASVspoof C-29, head C-30) |
| Known limit | No threshold transferred across datasets. Hindi, real WhatsApp voice notes and real clones: not measured. |
