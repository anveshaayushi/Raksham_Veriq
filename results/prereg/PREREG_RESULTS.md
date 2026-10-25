# Pre-registered dataset results

Metrics fixed in `bench/PREREG.md` before any run. Each line gives the command, date, commit and dataset. Intervals: 95% Wilson. Sets are never averaged together.

## BEFORE any fix (as committed)

### D1 chats: AI-generated blind set, n=80, author model not recorded, 25 Oct 2026
`python -m bench.prereg.run d1 --tag before` · 2026-10-25 05:17 IST · commit 2080ce0

**all 80**: scams warned 28/40 (70%) [0.55, 0.82]; accusing 22/40 (55%) [0.40, 0.69]; verify-first 6/40 (15%) [0.07, 0.29]; missed (called no major issue) 1/40 (2%) [0.00, 0.13]; no answer 11/40 (28%) [0.16, 0.43]. Genuine: false alarms (accusing) 7/40 (18%) [0.09, 0.32]; verify-first 16/40 (40%) [0.26, 0.55]; no major issue 7/40 (18%) [0.09, 0.32]; no answer 10/40 (25%) [0.14, 0.40].

**68 not seen in the Kit tab**: scams warned 24/34 (71%) [0.54, 0.83]; accusing 20/34 (59%) [0.42, 0.74]; verify-first 4/34 (12%) [0.05, 0.27]; missed (called no major issue) 1/34 (3%) [0.01, 0.15]; no answer 9/34 (26%) [0.15, 0.43]. Genuine: false alarms (accusing) 5/34 (15%) [0.06, 0.30]; verify-first 13/34 (38%) [0.24, 0.55]; no major issue 6/34 (18%) [0.08, 0.34]; no answer 10/34 (29%) [0.17, 0.46].

Of the genuine 'no answer' chats, 7/10 contain no payment request at all (nothing to check: the correct outcome).
Scam 'no answer' chats: 11 (payment link only: 5).

Payees (all 80): risky payees cleared 2/43 (5%) [0.01, 0.15], not extracted 11/43 (26%) [0.15, 0.40]; fine payees accused 6/25 (24%) [0.12, 0.43]; unclear (separate) results {'INCONCLUSIVE': 7, 'NAME_DISCREPANCY': 1}.
Extraction by kind: {'account': {'extracted': 16, 'not extracted': 2}, 'link': {'not extracted': 8}, 'phone_upi': {'extracted': 20, 'not extracted': 1}, 'upi': {'extracted': 26, 'not extracted': 3}}.
Voice-transcript chats: {'n': 8, 'voice_made_it_clearer': 0, 'note': 'no audio supplied: the voice detector did not run; transcripts add text only'}.

Failures: 30 chats (listed in the JSON).

### D2 name pairs: AI-generated, NOT blind (the writer had seen the engine; results are optimistic)
`python -m bench.prereg.run d2 --tag before` · 2026-10-25 05:17 IST · commit 2080ce0

**Dangerous matches** (different or lookalike called 'match'): 4/100 (4%) [0.02, 0.10]. False alarm (same entity called discrepancy): 2/70 (3%) [0.01, 0.10]. Same entity matched: 42/70 (60%) [0.48, 0.71]. Different entity -> discrepancy: 55/70 (79%) [0.68, 0.87]. Lookalike warned: 26/30 (87%) [0.70, 0.95]. Cannot tell -> unverified: 10/30 (33%) [0.19, 0.51].
Verdicts by relation: {'cannot_tell': {'discrepancy': 19, 'unverified': 10, 'lookalike': 1}, 'different_entity': {'discrepancy': 55, 'unverified': 14, 'lookalike': 1}, 'lookalike_of_different_entity': {'lookalike': 26, 'match': 4}, 'same_entity': {'match': 42, 'lookalike': 22, 'unverified': 4, 'discrepancy': 2}}.

### D3 extraction: AI-generated, NOT blind (the writer had seen the engine; results are optimistic)
`python -m bench.prereg.run d3 --tag before` · 2026-10-25 05:17 IST · commit 2080ce0

- upi_vpa: precision 15/16 (94%) [0.72, 0.99], recall 15/34 (44%) [0.29, 0.60], cases fully found 15/33 (46%) [0.30, 0.62]
- bank_account: precision 3/3 (100%) [0.44, 1.00], recall 3/19 (16%) [0.06, 0.38], cases fully found 3/19 (16%) [0.06, 0.38]
- ifsc: precision 7/7 (100%) [0.65, 1.00], recall 7/11 (64%) [0.35, 0.85], cases fully found 7/11 (64%) [0.35, 0.85]
- phone: precision 2/3 (67%) [0.21, 0.94], recall 2/8 (25%) [0.07, 0.59], cases fully found 2/8 (25%) [0.07, 0.59]
- url: precision 6/9 (67%) [0.35, 0.88], recall 6/6 (100%) [0.61, 1.00], cases fully found 6/6 (100%) [0.61, 1.00]
- payees (UPI + account): precision 18/19 (95%) [0.75, 0.99], recall 18/53 (34%) [0.23, 0.47]
- amounts (display helper only, first amount per message): precision 24/24 (100%) [0.86, 1.00], recall 24/50 (48%) [0.35, 0.61]
- false extraction on should-not-extract strings: 4/43 (9%) [0.04, 0.22]
- cases exact on every kind: 56/100 (56%) [0.46, 0.65]; cases with no dated message parsed: 0

## AFTER the first fixes (NOT blind: we saw the failures first)

### D1 chats: AI-generated blind set, n=80, author model not recorded, 25 Oct 2026
`python -m bench.prereg.run d1 --tag after` · 2026-10-25 05:29 IST · commit 2125984

**all 80**: scams warned 35/40 (88%) [0.74, 0.94]; accusing 29/40 (72%) [0.57, 0.84]; verify-first 6/40 (15%) [0.07, 0.29]; missed (called no major issue) 0/40 (0%) [0.00, 0.09]; no answer 5/40 (12%) [0.06, 0.26]. Genuine: false alarms (accusing) 1/40 (2%) [0.00, 0.13]; verify-first 18/40 (45%) [0.31, 0.60]; no major issue 11/40 (28%) [0.16, 0.43]; no answer 10/40 (25%) [0.14, 0.40].

**68 not seen in the Kit tab**: scams warned 30/34 (88%) [0.73, 0.95]; accusing 26/34 (76%) [0.60, 0.88]; verify-first 4/34 (12%) [0.05, 0.27]; missed (called no major issue) 0/34 (0%) [0.00, 0.10]; no answer 4/34 (12%) [0.05, 0.27]. Genuine: false alarms (accusing) 1/34 (3%) [0.01, 0.15]; verify-first 15/34 (44%) [0.29, 0.60]; no major issue 8/34 (24%) [0.12, 0.40]; no answer 10/34 (29%) [0.17, 0.46].

Of the genuine 'no answer' chats, 7/10 contain no payment request at all (nothing to check: the correct outcome).
Of the scam 'no answer' chats, 5/5 now get the 'asked to pay through a link: check before you pay' answer (not counted as warned above).

Payees (all 80): risky payees cleared 1/43 (2%) [0.00, 0.12], not extracted 5/43 (12%) [0.05, 0.24]; fine payees accused 1/25 (4%) [0.01, 0.20]; unclear (separate) results {'INCONCLUSIVE': 8}.
Extraction by kind: {'account': {'extracted': 18}, 'link': {'not extracted': 8}, 'phone_upi': {'extracted': 21}, 'upi': {'extracted': 29}}.
Voice-transcript chats: {'n': 8, 'voice_made_it_clearer': 0, 'note': 'no audio supplied: the voice detector did not run; transcripts add text only'}.

Failures: 17 chats (listed in the JSON).

### D2 name pairs: AI-generated, NOT blind (the writer had seen the engine; results are optimistic)
`python -m bench.prereg.run d2 --tag after` · 2026-10-25 05:29 IST · commit 2125984

**Dangerous matches** (different or lookalike called 'match'): 7/100 (7%) [0.03, 0.14]. False alarm (same entity called discrepancy): 0/70 (0%) [0.00, 0.05]. Same entity matched: 59/70 (84%) [0.74, 0.91]. Different entity -> discrepancy: 56/70 (80%) [0.69, 0.88]. Lookalike warned: 23/30 (77%) [0.59, 0.88]. Cannot tell -> unverified: 28/30 (93%) [0.79, 0.98].
Verdicts by relation: {'cannot_tell': {'unverified': 28, 'discrepancy': 1, 'lookalike': 1}, 'different_entity': {'discrepancy': 56, 'unverified': 14}, 'lookalike_of_different_entity': {'lookalike': 23, 'match': 7}, 'same_entity': {'match': 59, 'unverified': 10, 'lookalike': 1}}.

### D3 extraction: AI-generated, NOT blind (the writer had seen the engine; results are optimistic)
`python -m bench.prereg.run d3 --tag after` · 2026-10-25 05:29 IST · commit 2125984

- upi_vpa: precision 34/36 (94%) [0.82, 0.98], recall 34/34 (100%) [0.90, 1.00], cases fully found 33/33 (100%) [0.90, 1.00]
- bank_account: precision 16/16 (100%) [0.81, 1.00], recall 16/19 (84%) [0.62, 0.94], cases fully found 16/19 (84%) [0.62, 0.94]
- ifsc: precision 7/7 (100%) [0.65, 1.00], recall 7/11 (64%) [0.35, 0.85], cases fully found 7/11 (64%) [0.35, 0.85]
- phone: precision 7/9 (78%) [0.45, 0.94], recall 7/8 (88%) [0.53, 0.98], cases fully found 7/8 (88%) [0.53, 0.98]
- url: precision 6/9 (67%) [0.35, 0.88], recall 6/6 (100%) [0.61, 1.00], cases fully found 6/6 (100%) [0.61, 1.00]
- payees (UPI + account): precision 50/52 (96%) [0.87, 0.99], recall 50/53 (94%) [0.85, 0.98]
- amounts (display helper only, first amount per message): precision 24/24 (100%) [0.86, 1.00], recall 24/50 (48%) [0.35, 0.61]
- false extraction on should-not-extract strings: 6/43 (14%) [0.07, 0.27]
- cases exact on every kind: 85/100 (85%) [0.77, 0.91]; cases with no dated message parsed: 0

## FINAL, after a second fix (NOT blind). The first fixes let one-letter copycat names ('COBOLT' for 'Cobalt') count as a match, so spelling variants now give 'can't tell'

### D1 chats: AI-generated blind set, n=80, author model not recorded, 25 Oct 2026
`python -m bench.prereg.run d1 --tag final` · 2026-10-25 05:30 IST · commit 3ce6666

**all 80**: scams warned 35/40 (88%) [0.74, 0.94]; accusing 29/40 (72%) [0.57, 0.84]; verify-first 6/40 (15%) [0.07, 0.29]; missed (called no major issue) 0/40 (0%) [0.00, 0.09]; no answer 5/40 (12%) [0.06, 0.26]. Genuine: false alarms (accusing) 1/40 (2%) [0.00, 0.13]; verify-first 18/40 (45%) [0.31, 0.60]; no major issue 11/40 (28%) [0.16, 0.43]; no answer 10/40 (25%) [0.14, 0.40].

**68 not seen in the Kit tab**: scams warned 30/34 (88%) [0.73, 0.95]; accusing 26/34 (76%) [0.60, 0.88]; verify-first 4/34 (12%) [0.05, 0.27]; missed (called no major issue) 0/34 (0%) [0.00, 0.10]; no answer 4/34 (12%) [0.05, 0.27]. Genuine: false alarms (accusing) 1/34 (3%) [0.01, 0.15]; verify-first 15/34 (44%) [0.29, 0.60]; no major issue 8/34 (24%) [0.12, 0.40]; no answer 10/34 (29%) [0.17, 0.46].

Of the genuine 'no answer' chats, 7/10 contain no payment request at all (nothing to check: the correct outcome).
Of the scam 'no answer' chats, 5/5 now get the 'asked to pay through a link: check before you pay' answer (not counted as warned above).

Payees (all 80): risky payees cleared 1/43 (2%) [0.00, 0.12], not extracted 5/43 (12%) [0.05, 0.24]; fine payees accused 1/25 (4%) [0.01, 0.20]; unclear (separate) results {'INCONCLUSIVE': 8}.
Extraction by kind: {'account': {'extracted': 18}, 'link': {'not extracted': 8}, 'phone_upi': {'extracted': 21}, 'upi': {'extracted': 29}}.
Voice-transcript chats: {'n': 8, 'voice_made_it_clearer': 0, 'note': 'no audio supplied: the voice detector did not run; transcripts add text only'}.

Failures: 17 chats (listed in the JSON).

### D2 name pairs: AI-generated, NOT blind (the writer had seen the engine; results are optimistic)
`python -m bench.prereg.run d2 --tag final` · 2026-10-25 05:30 IST · commit 3ce6666

**Dangerous matches** (different or lookalike called 'match'): 1/100 (1%) [0.00, 0.05]. False alarm (same entity called discrepancy): 0/70 (0%) [0.00, 0.05]. Same entity matched: 57/70 (81%) [0.71, 0.89]. Different entity -> discrepancy: 56/70 (80%) [0.69, 0.88]. Lookalike warned: 23/30 (77%) [0.59, 0.88]. Cannot tell -> unverified: 28/30 (93%) [0.79, 0.98].
Verdicts by relation: {'cannot_tell': {'unverified': 28, 'discrepancy': 1, 'lookalike': 1}, 'different_entity': {'discrepancy': 56, 'unverified': 14}, 'lookalike_of_different_entity': {'lookalike': 23, 'unverified': 6, 'match': 1}, 'same_entity': {'match': 57, 'unverified': 12, 'lookalike': 1}}.

### D3 extraction: AI-generated, NOT blind (the writer had seen the engine; results are optimistic)
`python -m bench.prereg.run d3 --tag final` · 2026-10-25 05:30 IST · commit 3ce6666

- upi_vpa: precision 34/36 (94%) [0.82, 0.98], recall 34/34 (100%) [0.90, 1.00], cases fully found 33/33 (100%) [0.90, 1.00]
- bank_account: precision 16/16 (100%) [0.81, 1.00], recall 16/19 (84%) [0.62, 0.94], cases fully found 16/19 (84%) [0.62, 0.94]
- ifsc: precision 7/7 (100%) [0.65, 1.00], recall 7/11 (64%) [0.35, 0.85], cases fully found 7/11 (64%) [0.35, 0.85]
- phone: precision 7/9 (78%) [0.45, 0.94], recall 7/8 (88%) [0.53, 0.98], cases fully found 7/8 (88%) [0.53, 0.98]
- url: precision 6/9 (67%) [0.35, 0.88], recall 6/6 (100%) [0.61, 1.00], cases fully found 6/6 (100%) [0.61, 1.00]
- payees (UPI + account): precision 50/52 (96%) [0.87, 0.99], recall 50/53 (94%) [0.85, 0.98]
- amounts (display helper only, first amount per message): precision 24/24 (100%) [0.86, 1.00], recall 24/50 (48%) [0.35, 0.61]
- false extraction on should-not-extract strings: 6/43 (14%) [0.07, 0.27]
- cases exact on every kind: 85/100 (85%) [0.77, 0.91]; cases with no dated message parsed: 0

D4 (voice scripts): nothing run, by design (no recordings).
Teammate blind set (`data/blind/`): not provided, not run.
