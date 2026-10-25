# Acceptance list

Run 2026-10-25 05:41 IST, commit 3ce6666 (fast mode). Command: `python scripts/acceptance.py`.

| Part | Item | Command | Result | Detail |
|---|---|---|---|---|
| A | Reproduction: data, tests, coverage, random order, benchmarks | `python scripts/reproduce.py` | **NOT RUN** | skipped (--fast) |
| A | Smoke test (fresh install, offline, app health) | `python scripts/smoke.py` | **PASS** | SMOKE: PASS (6/6 steps) |
| A | Mutation check result on file: every planted bug caught | `python scripts/mutation_check.py` | **PASS** | killed 17/17 |
| A | Plan versus delivered: every promise points at an existing claim | `python scripts/plan_vs_delivered.py` | **PASS** | PLAN_VS_DELIVERED.md regenerated |
| A | CLAIMS.md: every proof file it names exists; every 'runs' row has a command or file | `(this script)` | **PASS** | 46 claims checked |
| A | Finale slide matches CLAIMS.md line for line | `python scripts/make_slide.py` | **PASS** | FINALE_SLIDE.md is up to date |
| A | Required documents present | `(this script)` | **PASS** | 27/27 present |
| A | Open-data and blind results recorded (or honestly 'not run') | `python -m bench.sms.run; python -m bench.blind.run` | **NOT RUN** | not run yet (allowed: RESULTS.md says 'not run') |
| B | 1. Three changing payees are found and checked separately (scenario A) | `demo: scenario A` | **PASS** | ['ramesh.k@upi', 'sunita.t@upi', '30112233445021'] -> NAME_DISCREPANCY |
| B | 2. Name matches but 'pay 18% tax to withdraw' -> Inconclusive | `demo: paste chat` | **PASS** | answer INCONCLUSIVE |
| B | 3. A voice cue never clears: flagged voice + matching name -> review, never 'no major issue' | `demo: voice` | **PASS** | voice ['flagged'] -> HUMAN_REVIEW |
| B | 4. A second victim's report links the payee; 5. a payment gateway never links | `demo: registry` | **PASS** | 1 report: clean; 2 victims: linked; gateway reports: excluded, lookup: unavailable |
| B | 6. Filing sheet for 1930 / cybercrime.gov.in with full identifiers | `demo: reports` | **PASS** | 3223 characters |
| B | 7. Works offline: no outgoing connection during a full check | `demo: offline` | **PASS** | 0 blocked attempts |
| B | 8. A NEW chat typed live gets a computed answer in under a second | `demo: paste box` | **PASS** | INCONCLUSIVE in 0 ms |
| B | 9. A genuine user flagged by mistake is cleared by a reviewer, with time to decision | `demo: scenario D` | **PASS** | NAME_DISCREPANCY -> overturned, decided in 0 s |

**ACCEPTED** ('NOT RUN' items are listed, never hidden).
