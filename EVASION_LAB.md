# Evasion lab: how an attacker beats VERIQ today, what we miss, what we would change

Interactive version: the app's results page, section 4 (type a sentence; type a claimed firm and a shown name).
Evidence: `bench/results_adversarial.json` (32/32 defended attacks, 3 known gaps; synthetic, written by us),
`results/live_journey.json`, `bench/names/results.json`, `results/asvspoof/`.

| # | How an attacker evades | What happens today | Evidence | What we would change |
|---|---|---|---|---|
| 1 | Open the mule account in the firm's EXACT name | name matches → at best "No major issue" (with "not a guarantee"); pressure cues may still give "Inconclusive" | red-team known gap | bank-side data: account age, KYC type, link to the firm's registered @valid handle |
| 2 | Write pressure without any keyword ("your chance closes soon") | cue missed | red-team known gaps (2) | a small classifier trained on consented, labelled Indian scam chats |
| 3 | Break the UPI ID with spaces or words ("aarohan dot ipo2 at okaxis", "(at)", spaced digits) | **fixed 25 Oct**: read and normalised; a plain "at" counts only when the ID is clearly an ID, so "meet at office" is never a UPI ID | live journey J2 (was a miss), D3 recall 18/53 → 50/53 (C-45) | numbers written in words ("nine eight one ...") are still missed |
| 4 | Ask for payment only through a link | **since 25 Oct**: "check before you pay: VERIQ can't see who receives a link payment" (was "nothing found") | C-46; 5/40 D1 scam chats | treat payment links as payees the user can check |
| 5 | Use a TTS or voice-clone engine we never saw | AASIST misses about half even on its own dataset; our demo TTS clip is not flagged | C-29, C-30, results page | voice stays a review cue; train on many engines and Indian languages; never a decision |
| 6 | Pick a short/abbreviated legal name ("SSL") so genuine and fake both look odd | short forms and initials are now "can't tell", never an accusation (0/42 same-firm names called a discrepancy after the 25 Oct fixes; 3/42 before) | C-34, scenario D | reviewer path (measured: 1 user click + 1 reviewer click); bank-registered names |
| 7 | Flood the registry with false reports against a rival | one reporter or a burst counts once; 2 independent reporters needed | registry tests | reviewer confirmation for high-impact links; report caps per device |
| 8 | Use a payment gateway handle | never linked, name "unverified" | registry + matcher tests | ask the user for the merchant name shown at checkout |
| 9 | Chat without timestamps (copied text) | refused honestly ("no dated messages") | edge tests | accept undated text with a clear "times unknown" label |
| 10 | Copy the firm's name with one letter changed ("COBOLT MEADOW CAPITAL") | "can't tell" (never a match): a transliteration and a copycat look the same | C-44: our first fix let 6 such names count as a match; fixed again, 1/100 left | firm-level lists of approved account names |
VERIQ can be fooled. It is built so that being fooled leaves the user where they were ("don't pay yet, verify"), not
falsely reassured: "No major issue" always says "This is not a guarantee".
