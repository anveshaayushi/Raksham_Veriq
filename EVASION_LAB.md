# Evasion lab: how an attacker beats VERIQ today, what we miss, what we would change

Interactive version: the app's results page, section 4 (type a sentence; type a claimed firm and a shown name).
Evidence: `bench/results_adversarial.json` (32/32 defended attacks, 3 known gaps; synthetic, written by us),
`results/live_journey.json`, `bench/names/results.json`, `results/asvspoof/`.

| # | How an attacker evades | What happens today | Evidence | What we would change |
|---|---|---|---|---|
| 1 | Open the mule account in the firm's EXACT name | name matches → at best "No major issue" (with "not a guarantee"); pressure cues may still give "Inconclusive" | red-team known gap | bank-side data: account age, KYC type, link to the firm's registered @valid handle |
| 2 | Write pressure without any keyword ("your chance closes soon") | cue missed | red-team known gaps (2) | a small classifier trained on consented, labelled Indian scam chats |
| 3 | Break the UPI ID with spaces or words ("aarohan . ipo2 @ okaxis") | payee NOT found → no answer | live journey J2 (miss) | normalise spaced/obfuscated handles before extraction, with a decoy test set |
| 4 | Send the payment link outside the chat (SMS, a website) | nothing to check | by design | let the user paste the link or the UPI ID they were given |
| 5 | Use a TTS or voice-clone engine we never saw | AASIST misses about half even on its own dataset; our demo TTS clip is not flagged | C-29, C-30, results page | voice stays a review cue; train on many engines and Indian languages; never a decision |
| 6 | Pick a short/abbreviated legal name ("SSL") so genuine and fake both look odd | genuine firms can be called a discrepancy (3/42 same-firm names in our pair set) | C-34, scenario D | reviewer path (measured: 1 user click + 1 reviewer click); bank-registered names |
| 7 | Flood the registry with false reports against a rival | one reporter or a burst counts once; 2 independent reporters needed | registry tests | reviewer confirmation for high-impact links; report caps per device |
| 8 | Use a payment gateway handle | never linked, name "unverified" | registry + matcher tests | ask the user for the merchant name shown at checkout |
| 9 | Chat without timestamps (copied text) | refused honestly ("no dated messages") | edge tests | accept undated text with a clear "times unknown" label |
VERIQ can be fooled. It is built so that being fooled leaves the user where they were ("don't pay yet, verify"), not
falsely reassured: "No major issue" always says "This is not a guarantee".
