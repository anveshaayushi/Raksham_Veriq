# Engineering walkthrough: what we built during the finale, module by module

Source of truth: `git log v0-prebuilt..HEAD` (every finale commit starts with "FINALE:"). Code was written with Claude
(Anthropic) under the team's direction (Claude A: contract and rules; Claude B: voice; Claude C: app, registry,
reports, integration, evaluation); the team ran, reviewed and committed it. "Off-the-shelf" below means code or
models we did not write.

## Finale commits (real times IST, from git)
| Commit | Time | What |
|---|---|---|
| `704c9f5` | 24 Oct 11:43 | SQLite cross-victim registry (keyed hashes, poisoning defences) |
| `8fb36e1` | 24 Oct 12:54 | PREBUILT boundary, CLAIMS.md, Windows run script |
| `abbaab5` | 24 Oct 15:24 | the real decision engine on the shared contract (parser, extractor, name matcher, rules) |
| `4d9a619` | 24 Oct 15:27 | seeded synthetic chat benchmark with a held-out synthetic test |
| `0dd905b` | 24 Oct 15:38 | Claude B's voice module, eval tool and dataset scripts merged |
| `8011c97` | 24 Oct 17:09 | QR payees, look-alike names, de-obfuscated cues, mistake recovery, 1930 incident card, red-team set |
| `844fdd0` | 24 Oct 19:39 | voice head trained on AASIST embeddings; results page; paste box |
| `80bd936`, `37206c1` | 24 Oct ~22:15-22:23 | Q0 clean install (laptop) |
| later FINALE commits | 24-25 Oct | Q1 reproducibility, Q2-Q5 (open data, kit runner, player, deployment), this delivery: see `git log` |
| `e8b4a47` (branch of B) | 25 Oct ~00:30 | Claude B's ASVspoof 2019 LA run (files merged into this branch) |

## Module by module
| Module | What WE wrote (finale) | Off-the-shelf | Files | Owner to explain |
|---|---|---|---|---|
| Intake | consent, type/size/magic-byte checks, zip-bomb and path checks, kit-zip safety | Python zipfile | `app/intake.py`, `app/views/kit.py` | C |
| Parser | WhatsApp Android/iOS formats, day/month detection, multi-line messages | none | `parsing/__init__.py` | A/C |
| QR | UPI link parsing; OpenCV call to find codes | OpenCV QRCodeDetector | `parsing/qr.py` | C |
| Extractor | payees with decoys, amounts, firm, SEBI number, pressure cues with de-obfuscation, Hindi account words | regular expressions only | `extract/__init__.py` | A/C |
| Name matcher | generic/category words, look-alike detection, personal/gateway/initials/near-spelling = unverified, shop words | none | `match/__init__.py` | A/C |
| Decision rules | ranked ladder, evidence classes A-E, high-pressure variant, voice only escalates | none | `rules/` | A/C |
| Registry | keyed HMAC store, independent-reporter counting, burst and rate limits, gateway exclusion, reviews | SQLite | `registry/` | C |
| Reports | 1930 filing sheet, redacted summary, NCRP-style incident card, escaping/defanging | none | `report/` | C |
| Voice pipeline | ffmpeg decode, quality gate, VAD, chunking, calibration contract, never-crash service | **AASIST pretrained model (MIT, NAVER)**, ffmpeg, PyTorch | `voice/` | B |
| Voice evaluation | ASVspoof subset builder reading the zip directly, rows with Wilson intervals; trained heads, grouped CV, cross-dataset test | scikit-learn LogisticRegression | `scripts/b_run_all.py`, `scripts/make_results_rows.py`, `bench/voice/` | B / C |
| App | 6-step flow, why-it-fired + actions, reviewer view, scenario player, kit tab, privacy proof, plan page, evasion lab | Streamlit | `app/` | C |
| Evaluation and tests | seeded generators, benchmark runner, red-team set, name pairs, SMS/blind runners, reproduce, mutation check, smoke, acceptance | pytest, coverage | `bench/`, `eval/`, `scripts/`, `tests/` | C |
| Deployment | env config, offline mode guard, offline bundle, install scripts, Dockerfile/compose | Docker base image | `app/config.py`, `scripts/`, root | C |

Not ours and not claimed: AASIST's architecture and weights, Kokoro TTS, OpenCV, Streamlit, ffmpeg, scikit-learn,
PyTorch. "Fine-tuning" claim: we trained small logistic-regression heads on AASIST embeddings; we did NOT fine-tune AASIST.

## 3-minute talk track (any member)
1. (30 s) "Scammers don't need a fake voice to steal; they need you to pay the wrong account. So VERIQ follows the
   money: it lists every place the chat asks you to pay, separately."
2. (45 s) "For each payee it compares the name YOUR bank app shows with the firm the chat claims. That code is ours:
   it knows legal-form words, look-alike shells like 'NAVYUG ONLINE TRADERS', and when it can't tell (gateways,
   personal names) it says unverified instead of accusing."
3. (30 s) "Fixed rules, no scores: linked by other victims > name mismatch > SEBI number conflict > needs review >
   inconclusive > no major issue, which always says it is not a guarantee. Every answer cites its evidence."
4. (30 s) "Voice is the off-the-shelf part: pretrained AASIST. We measured it on ASVspoof: AUC 0.77, misses about half
   the fakes at a fixed threshold. We trained our own heads; one failed on new data, so we switched it off. Voice can
   only send a payee to human review."
5. (45 s) "Everything is tested and reproducible: about 1,130 tests, 17 planted bugs all caught, one command to
   reproduce every number, a smoke test that proves it works offline."
