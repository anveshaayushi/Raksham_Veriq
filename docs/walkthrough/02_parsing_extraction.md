# Parsing and extraction: who asked you to pay, where

## Plain words
Plain words: VERIQ reads the chat line by line (Android and iPhone formats, Indian or US dates) and lists every place
you were asked to send money (UPI IDs, account numbers, QR codes in images), the amounts, the firm and SEBI number
quoted, and pressure tactics ("guaranteed returns", "pay tax to withdraw", "share the OTP"), even when disguised as
"gu@r@nteed" or "u_r_g_e_n_t".

| | |
|---|---|
| Code | `parsing/`, `parsing/qr.py`, `extract/` |
| Goes in | the chat text (and voice-note transcripts if pasted), images |
| Comes out | messages with times, payees (each separately, with the message it came from), amounts, cues (hard / soft) |
| Can do | find payees with decoys around them (phone numbers, e-mails, order numbers); detect payee changes |
| Cannot say | who owns a UPI ID; meaning of reworded pressure with no keyword |
| Tests / numbers | `app/tests/test_extract_stub.py`, `app/tests/test_finale_features.py`, `bench/` (399/399 payees on synthetic chats) |
| Known limit | Chats without timestamps are refused (the contract needs a time per message). Pressure phrased without any keyword is missed. |
