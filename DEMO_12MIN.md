# 12-minute live demo (judges use the product; no slides)

One-command start (Windows, from `veriq\`):
```powershell
$env:VERIQ_REGISTRY_SECRET="demo-secret-change-me-0123"; python -m registry.seed registry_demo.db; $env:VERIQ_REGISTRY_DB="registry_demo.db"; powershell -ExecutionPolicy Bypass -File app\run_app.ps1 -SkipTests
```
Night before: `python scripts\acceptance.py --fast` must end "ACCEPTED" (it replays every step below).

| Min | Step (judge drives where possible) | What to show / say | Evidence |
|---|---|---|---|
| 0-1 | Who and what | Meera's story (PROBLEM_USER.md); "VERIQ checks who would actually receive the money, before you pay." | PROBLEM_USER.md |
| 1-3 | **Judge picks a chat and a payee**: paste box. Ask the judge to type a payment chat (any language, any UPI ID) and the name their bank app would show | alert, **why it fired**, the four actions (do not pay / check name / ask review / report pack) | C-24, safeguard tests |
| 3-5 | Live journey, scenario player A: attack arrives message by message; answer changes after the payee rotates; download the report pack | "Detection is not the end: here is what the user does next." | C-33 |
| 5-6 | Judge varies the input: change a payee's UPI ID or the bank-app name in the player; answer recomputes | "Nothing is pre-written." | C-15, C-33 |
| 6-7 | Second victim → **Linked**; gateway never linked (scenario A answer, "I lost money" button) | keyed hashes, 2 independent reporters | C-8..C-10 |
| 7-8.5 | **Mistake path**, scenario D: genuine broker flagged → reason shown → "ask for review" → reviewer overturns; time shown | measured: 1 user click + 1 reviewer click after the alert; app time 0.5 s (human time not included) | `results/mistake_path.json` |
| 8.5-9.5 | **Named failure, shown on purpose**: voice. Attach the synthetic demo clip: AASIST says no signal (missed). Results page 2b: AUC 0.77, ~56% of fakes missed on ASVspoof eval; our own head failed cross-dataset, so it is off | "Voice only ever asks for review; it never clears." | C-29, C-30, C-39 |
| 9.5-10.5 | Evasion lab: type "gu@r@nteed" (caught); "your chance closes soon" (missed); spaced UPI ID (missed) | how an attacker beats us, what we change | EVASION_LAB.md |
| 10.5-11.5 | Measured accuracy and the kit tab: numbers with intervals; offer to run the judge's own folder | RESULTS.md, Kit tab | C-16, C-32 |
| 11.5-12 | Privacy proof: "Delete my data" before/after; offline smoke | safeguards running | C-31, C-38 |
If anything breaks: say so, use the backup video (docs/DEMO_SCRIPT.md), keep answering live.
