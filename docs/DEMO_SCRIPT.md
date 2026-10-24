# 2-minute live demo (order) and backup-video script

Before the slot: laptop on charger, hotspot on, a seeded demo registry (fictional reports only), the app running,
browser at http://localhost:8501, a second tab on the "Scenario player" page:

```powershell
$env:VERIQ_REGISTRY_SECRET = "demo-secret-change-me-0123"; python -m registry.seed registry_demo.db
$env:VERIQ_REGISTRY_DB = "registry_demo.db"; powershell -ExecutionPolicy Bypass -File app\run_app.ps1 -SkipTests
``` Every step below is checked automatically by
`python scripts/acceptance.py` (part B), so if it passes the night before, the demo works.

| Time | What you click | What you say (one line) |
|---|---|---|
| 0:00-0:20 | Main page, demo **Scenario A** → continue to the answer | "One 'firm', three payees that keep changing. VERIQ checks each payee separately; the name Meera's bank app shows belongs to a shop, not the firm: **Payee name doesn't match**." |
| 0:20-0:35 | Paste box: a chat where the name **matches** but says "pay 18% tax to withdraw" | "A matching name is not a clean bill: the withdrawal-tax demand keeps it **Inconclusive: don't pay yet**." |
| 0:35-0:50 | Scenario A's voice note, then the results page section 2b | "Voice is a review cue only. A voice result can never clear a payee, and on a public benchmark no threshold held up, so the app says 'can't assess' rather than guess." |
| 0:50-1:05 | Scenario A answer: `sunita.t@upi` already **Linked**; on the account press "I lost money to this payee" → it becomes **Linked**; a `...@razorpay` payee's report → "excluded" | "One report never brands anyone; a second independent victim does. A payment gateway is never stored, because it hides the merchant." |
| 1:05-1:15 | Reports step: download the **filing sheet** | "Everything the 1930 helpline asks for, blanks left blank, nothing invented." |
| 1:15-1:25 | Point at the sidebar: "VERIQ files no complaints, blocks nothing and contacts no one" | "It runs **offline** on this laptop: the smoke test proves no outgoing connection." |
| 1:25-1:45 | Ask a judge for a **new chat**; type it into the paste box | "Your chat, computed live, not pre-written." |
| 1:45-2:00 | Scenario player → **D**: genuine broker flagged → ask for review → reviewer overturns | "A genuine user flagged by mistake gets a review in one step, with the time to decision and an audit trail." |

If something breaks live: say so, switch to the backup video, and offer the kit runner on any folder they give us.

## Backup video script (record the night before; 2 minutes; screen recording with voice-over)

1. Title card (3 s): "VERIQ · check the payee before you pay · recorded <date/time>, commit <hash>".
2. Record exactly the eight steps above, in order, at normal speed, no cuts inside a step.
3. Show the clock or `git log -1` in a terminal at the start and the end, so the recording is clearly of this build.
4. End card (5 s): "Live demo preferred; this video is a backup. Numbers: RESULTS.md. Limits: evasion lab."
Rule from the rubric: a video instead of a live demo scores 1, so use it only if the live app fails.
