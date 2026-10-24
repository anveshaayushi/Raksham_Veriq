# Decision rules: one answer per payee

## Plain words
Plain words: fixed rules, no scores or weights. The first rule that applies wins: reported by other victims (LINKED) >
name discrepancy > registration conflict > needs human review > inconclusive > no major issue. The whole chat gets the
worst payee's answer. "No major issue" always says "This is not a guarantee." Voice and chat cues can only make the
answer more careful; they never clear a payee.

| | |
|---|---|
| Code | `rules/`, `rules/templates.py` (English and Hindi labels) |
| Goes in | payees, cues, evidence (classes A user check, B SEBI snapshot, C registry, D chat/QR, E voice) |
| Comes out | a result, the rule id, reasons, the evidence used, and the next step |
| Can do | explain every answer with its evidence; stay identical whatever order things arrive in |
| Cannot say | whether a payment is safe |
| Tests / numbers | `tests/golden/` (exact golden match, all 384 input combinations), mutation check (17/17) |
| Known limit | Rules were written by the team; the synthetic benchmark is partly circular (REPRODUCE.md). |
