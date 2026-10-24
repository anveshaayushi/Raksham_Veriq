# Name check: does the bank app's name belong to the firm?

## Plain words
Plain words: the name YOUR bank or UPI app shows before you pay is the strongest evidence we have. VERIQ compares it
with the firm the chat claims to be. Different business name: a discrepancy. Same brand plus a new word ("NAVYUG ONLINE
TRADERS"): a look-alike, sent to review. Gateways (Razorpay...), personal names, initials and near spellings: "unverified",
because we cannot tell, so we never accuse.

| | |
|---|---|
| Code | `match/` |
| Goes in | claimed firm name, name shown by the user's app (typed by the user, labelled user-reported) |
| Comes out | match / discrepancy / lookalike / unverified, with a reason |
| Can do | catch unrelated shop names used as mule accounts; avoid accusing on legal-form, spelling or script variants |
| Cannot say | that a matching name means the firm is legitimate (a mule account can be opened in the firm's exact name) |
| Tests / numbers | `tests/golden/test_engine_properties.py::test_name_matcher_classes`, `bench/names/` (97 labelled pairs) |
| Known limit | 3/42 same-firm names still called a discrepancy ("BLUE RIVER" vs "BlueRiver", initials "SSL", "BRF"); see C-34. |
