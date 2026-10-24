# Pre-registration: blind-set metrics (written 25 Oct 2026, ~04:00 IST, BEFORE any blind run)

Commit this file before running anything on the blind sets. Each set is run exactly ONCE with the code as committed.
No tuning on the results. If a bug is fixed afterwards, report BEFORE and AFTER, and mark every affected case "no
longer blind". Sets are never averaged together; the teammate set stays separate from the AI-generated sets.
Intervals: 95% Wilson. Labels: "AI-generated blind set, n=.., written by <model>, 25 Oct 2026" or
"hand-written by teammates, n=.., not tuned on".

## Definitions (VERIQ answers)
- **warned** = any payee's answer is not NO_MAJOR_ISSUE (case result != NO_MAJOR_ISSUE).
- **accusing** = NAME_DISCREPANCY, REGISTRATION_CONFLICT, LINKED or HUMAN_REVIEW.
- **verify-first** = INCONCLUSIVE.
- **missed** = NO_MAJOR_ISSUE for every payee of a scam chat. **no answer** = no payee or no dated message found.

## 1. AI chat set D1 (`data/blind_ai/`, n=80) — `python -m bench.blind.run --data data/blind_ai --out results/q2/blind_ai.json`
- Scam (n=40): recall = warned; accusing; missed — each with Wilson interval.
- Genuine (n=40): false alarms = accusing; verify-first rate; clear (NO_MAJOR_ISSUE) rate.
- Payee level against `intended_risk` (risky / fine; **unclear n=8 reported separately**) and by `name_relation`.
- Breakdowns by `language` and `difficulty`. Payees not extracted (by `kind`) counted as misses.
- Failure-case table: file, what VERIQ said, why, the change we would make.
- The 8 chats with `voice_transcripts`: confirm voice only escalates (never clears).

## 2. Name pairs D2 (`data/names_blind/pairs.csv`, n=200)
- Agreement per relation class, with intervals.
- **Headline: dangerous matches** = different_entity or lookalike_of_different_entity called "match".
- False alarm = same_entity called "discrepancy". cannot_tell must be "unverified" (verify-first).
- Failure cases.

## 3. Extraction D3 (`data/extract_blind/cases.jsonl`, n=100)
- Precision, recall and exact match per kind (upi, account, ifsc, phone, link) and for amounts.
- False-extraction rate on should_not_extract cases. Failure cases.

## 4. Voice scripts D4 (`data/voice_scripts/`) — run NOTHING
- Recording guide (open TTS for fakes; teammates' own consented voices for real and own-voice clones) and an
  `audio_labels_template.csv` (file,label,source,language,script_id) for the Kit runner. Missing sets = "not run".

## 5. Teammate set (`data/blind/`, if provided)
- Same metrics as 1, once, reported separately, never averaged with the AI set.

## Addendum (25 Oct ~04:10 IST, still before any run): how D2-D4 are labelled
`data/GENERATION.md` (written by the dataset author) states that D2, D3 and D4 were written by Claude Sonnet 5.5 in
the same conversation that wrote VERIQ's parser, extractor, name matcher and rules, with sight of that code. They are
therefore reported as **"AI-generated, NOT blind (the writer had seen the engine; results are optimistic)"**, never as
blind. D1's author model is not recorded in the files; until the team confirms it, D1 is "AI-generated blind set,
n=80, author model not recorded". The metrics above do not change.

