# GENERATION.md: provenance of the blind datasets

**Date: to be filled by the human.**

## Who wrote what
| Dataset | Written by | Notes |
|---|---|---|
| D1 blind chats (`data/blind_ai/`) | A separate AI session (the one that produced `generation/d1_batch*.py`, rendered by `generation/render_d1.py`) | **Model name was not recorded in the delivered files; the human who ran Prompt 1 must fill it in.** |
| D2 name pairs, D3 extraction cases, D4 voice scripts, this file | **Claude Sonnet 5.5 (Anthropic), via claude.ai** | Source: `generation/d2.py`, `d3.py`, `build_d3.py`, `d4.py`, `build_d4.py`, `assemble.py` (seed 20261024). |

## IMPORTANT: D2, D3 and D4 are NOT blind in the way Prompt 1 intends
Prompt 1 asks for a fresh chat with no knowledge of the tool, preferably a different AI from the one that wrote the engine. D2-D4 were written by the **same model, in the same conversation, that wrote VERIQ's parser, extractor, name matcher and rules engine**, and the writer had seen that code and its word lists (for example the matcher's list of generic words and gateway names). Mitigations actually applied: relations/expected values were decided by real-world judgement; the engine was **not run** on D2-D4 and nothing was changed in response to any engine output. Edits that were made came from structural self-checks only (a forbidden name removed, an invalid 20-digit account fixed, two cases dropped to hit the quotas, link cases rewritten to include a scheme, a forbidden name removed from D2); every fictional identifier follows Prompt 1's safety rules. Residual risk: unconscious alignment, e.g. D2's "shares only a generic word" pairs and D3's OTP/ticket-id negatives mirror behaviours the writer knew the engine cares about. Treat results on D2-D4 as **optimistic**, and prefer an independently written set if one can be produced.

## Counts
**D1** (80 chats; label x language):
| | english | hinglish | devanagari_hindi |
|---|---|---|---|
| scam | 16 | 17 | 7 |
| genuine | 20 | 15 | 5 |

D1 (label x difficulty):
| | easy | medium | hard | ambiguous |
|---|---|---|---|---|
| scam | 7 | 24 | 7 | 2 |
| genuine | 15 | 6 | 9 | 10 |

D1 formats: 58 Android-style, 22 iPhone-style files; voice notes in 8 chats.

**D2** (`names_blind/pairs.csv`, 200 pairs): same_entity 70, different_entity 70, lookalike_of_different_entity 30, cannot_tell 30.

**D3** (`extract_blind/cases.jsonl`, 100 cases): designed as 60 positive and 40 negative/tricky cases. Four of the 40 tricky cases also contain a real payee next to distractors, so by "has an expected payee" the split is 64 with payees and 36 without. Expected payee kinds: {'phone': 8, 'account': 19, 'upi': 34, 'ifsc': 11, 'link': 6}.

**D4** (`voice_scripts/scripts.csv`, 60 scripts; type x language):
| | en | hi | hinglish |
|---|---|---|---|
| scam_like | 10 | 10 | 10 |
| genuine | 10 | 10 | 10 |

10 scam_like and 10 genuine scripts mention a payee spoken aloud. Reading time targets are 8 to 16 s (estimated at about 2.5 words/s, 2.2 for Hindi; not measured by recording).

## Self-checks run on D2-D4 (structure only, engine not used)
Row/quota counts, no forbidden names (Meera, Rahul, Navyug, Sunita, Ramesh), phones follow 5 digits + 000 + 2 digits, accounts begin 0000, every expected account/phone/IFSC in D3 is recoverable from its own text.

## Known weaknesses of this data
- Written by AI: tidier and more varied in a "designed" way than real chats and real voice notes; scams follow familiar scripts.
- D1 was authored as data tables and rendered by code, so message formatting and timing are more regular than real exports.
- D2-D4 are correlated with the engine's author (see above). D1's writer is a different session but may share training-data habits with the engine's author model.
- Relation labels in D2 (and "ambiguous" in D1) are judgement calls; `cannot_tell` and `lookalike` boundaries are fuzzy. A second human labeller is advisable.
- D3: the expected canonical value for links assumes the scheme written in the text; some tricky negatives (a helpline number, a retracted ID) are debatable.
- D4: scripts only; no audio exists. Genuine and scam-like scripts were matched in style by hand, not verified with a classifier. Hindi was written without a native-speaker review.
- All identifiers are fictional but some firm or shop names could coincide with real ones by chance.
