# Demo script and backup-video plan (Claude C)

Synthetic data only. Every answer is computed live by the engine (demos only pre-fill inputs). Say "stub" wherever
the app says stub (demo voice results until B's threshold is calibrated).

## Live demo, about 4 minutes
1. **Consent (15 s).** "Before anything is uploaded, VERIQ asks for consent and says what it can't do: it can't prove fraud or confirm a voice is real."
2. **Upload (20 s).** Show the upload tab and its limits, then switch to *Try a synthetic demo* → Scenario A.
3. **Confirm the firm (20 s).** "Meera believes she's dealing with Navyug Wealth Research. Each place she was asked to pay is listed separately: two UPI IDs and an account. The second came from a voice note."
4. **Payee names (30 s).** "She checks each one in her own UPI app without paying, and types the name she sees. VERIQ labels it user-reported; it never contacts a bank."
5. **Answer (60 s).** Overall: payee name doesn't match. Walk payee by payee: `ramesh.k@upi`, `sunita.t@upi` (from the
   voice note) and the account each show their own name discrepancy (claimed firm vs the trading-company name her app showed),
   with source, date, rule and limitation. Open "Evidence about the whole case" for the registration and voice lines.
   "Change any typed name and the answer is recomputed": try 'NAVYUG ONLINE TRADERS' on Scenario B (look-alike -> review).
6. **Money already sent (30 s).** Turn on the toggle: the results stay the same, and the next step changes to calling 1930.
7. **Reports (45 s).** Download the filing sheet: 1930 fields, BLANKs for what only Meera knows, and the "what to say on the call" box. Then the shareable summary: account cut to the last four digits.
7b. **Mistake recovery (40 s, Scenario B + 'Also attach a QR screenshot').** The QR names OM SAI ENTERPRISES -> Needs
   review. Open "This looks wrong?", choose "different legal or trading name", add the @valid reference, ask for review.
   Turn on *Reviewer view* (left menu), overturn with a reason: "Reviewed: explained", time taken shown, original result
   kept on record; download the audit trail and the 1930 incident card (JSON).
7c. **Voice (30 s).** Demo C with 'Attach real audio': the synthetic clip is flagged → Needs review; open the case
   evidence (score vs calibrated threshold). Then open *How accurate is VERIQ?* (left menu) for the measured numbers
   and failure cases.
8. **Close (20 s).** Scenario B shows "No major issue … This is not a guarantee." Scenario C shows Inconclusive. "VERIQ files no complaints, blocks nothing and contacts no one."

## Phone demo
`powershell -ExecutionPolicy Bypass -File app\run_app.ps1 -Phone` on the laptop, connected to the phone's hotspot; open the
printed IPv4 address with `:8501` on the phone. Rehearse twice; venue Wi-Fi may block device-to-device traffic.

## Backup video 1: demo (2–3 min, record after the finale freeze)
- Tool: Windows **Win + Alt + R** (Xbox Game Bar) or OBS; 1080p; browser zoom 110%.
- Shots: steps 1–8 above on the **final** build, Scenario A end to end, then B and C answers only.
- Caption the opening frame: "VERIQ · synthetic data · built at RAKSHAM 2026"; show only real measured numbers.
- Keep copies on two laptops and a pen drive.

## Backup video 2: explainer (60–90 s)
Problem (the adviser sounded real; where was the money going?) → claim vs evidence per payee → what the user does next
(pause, check, 1930) → what VERIQ will not do. Captions rather than voice-over if the room is noisy.

## Before you present
- [ ] `python -m pytest -q` is green on the presenting laptop
- [ ] App opens with Wi-Fi off (no internet needed)
- [ ] Phone path rehearsed twice on the hotspot
- [ ] Videos on two devices
