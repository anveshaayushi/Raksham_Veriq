# CLAIMS: what we say VERIQ does, and the proof for each line

Rule: a line goes on a slide only if its Status is **runs** and its Proof can be re-run. Each role appends its rows from
`CLAIMS_ROWS.md`; Claude C merges them here. "Built" says whether it is in `v0-prebuilt` (PRE) or finale work (FINALE).

| # | Claim (plain words) | Owner | Built | Status | Proof (command or file) |
|---|---|---|---|---|---|
| C-1 | Asks for consent before any upload, and checks file type, size, magic bytes and ZIP safety | C | PRE | runs | `app/tests/test_intake.py`, `test_app_flow.py` |
| C-2 | Lists every place the user was asked to pay as a separate payee | C | PRE | runs (stub extractor until A's) | `app/tests/test_extract_stub.py` |
| C-3 | The payee name the user saw in their own bank/UPI app is labelled "user-reported" (class A) | C | PRE | runs | `app/tests/test_adapters_and_case.py` |
| C-4 | "I have already sent money" changes only the next step (to 1930), never the result | C | PRE | runs | `app/tests/test_next_steps_and_safety.py`, `test_golden_integration.py` |
| C-5 | 1930 filing sheet keeps full identifiers; shareable summary shows accounts as last 4 digits | C | PRE | runs | `report/tests/test_reports.py` |
| C-6 | Chat text is escaped in the app and reports (no script runs, links are defanged) | C | PRE | runs | `report/tests/test_reports.py`, `app/tests/test_next_steps_and_safety.py` |
| C-7 | "No major issue" always says "This is not a guarantee." | C | PRE | runs | `app/tests/test_golden_integration.py` |
| C-8 | Cross-victim registry stores only keyed hashes: pseudonymisation, not anonymity | C | FINALE | runs | `registry/tests/test_sqlite_registry.py::test_no_raw_identifiers_or_tokens_in_the_file` |
| C-9 | A payee links only after 2 independent reporters or a reviewer; one reporter or a burst of new reporters cannot link it | C | FINALE | runs | `registry/tests/test_sqlite_registry.py` (poisoning tests) |
| C-10 | Payment-gateway handles are never stored or linked; a broken registry says "unavailable", never "clean" | C | FINALE | runs | `registry/tests/test_sqlite_registry.py` |
| C-11 | Every payee gets its own answer from fixed rules (first rule that applies wins), computed live from the chat | A/C | FINALE | runs | `tests/golden/test_decide_golden.py` (exact golden match, raw chat end to end) |
| C-13 | More risk never gives a milder answer; a voice result never clears a payee; "unavailable" is never "clean" | A/C | FINALE | runs | `tests/golden/test_engine_properties.py` (all 384 input combinations) |
| C-14 | Gateway names, personal-looking names, initials and near spellings are "unverified", never an accusation | A/C | FINALE | runs | `tests/golden/test_engine_properties.py::test_name_matcher_classes` |
| C-15 | A judge can change the typed payee name and the answer is recomputed on the spot | C | FINALE | runs | `app/tests/test_golden_integration.py::test_judge_can_vary_the_demo_and_the_engine_recomputes` |
| C-16 | On 300 held-out synthetic chats: every payee found (399/399), 96.2% of answers as expected, 0 false alarms on 178 genuine payees, 0 scams cleared | C | FINALE | runs (synthetic) | `python -m bench.run test`, `bench/README.md` |
| C-17 | A UPI ID hidden in a QR screenshot is found and checked like any other payee; if the QR's own name differs from the claimed firm, the answer is "needs review" (the QR name is sender-typed, so it never decides alone) | C | FINALE | runs | `app/tests/test_finale_features.py` (QR tests), `bench/adversarial.py` |
| C-18 | A look-alike account ("NAVYUG ONLINE TRADERS" for "Navyug Broking") goes to review instead of passing as the firm; genuine variants still match | A/C | FINALE | runs | `bench/adversarial.py` (6/6 look-alikes, 4/4 genuine variants) |
| C-19 | Obfuscated pressure phrases ("gu@r@nteed", "u_r_g_e_n_t", "P.a.y t@x to withdraw", Hinglish) are still caught | A/C | FINALE | runs | `bench/adversarial.py` (11/11); reworded phrases without keywords are missed (known gap) |
| C-20 | A short or unclear voice note plus pressure to pay an unverified payee gives "Don't pay yet: high pressure" | A/C | FINALE | runs | `app/tests/test_finale_features.py::test_high_pressure_variant_for_unassessable_audio` |
| C-21 | A genuine user flagged by mistake can ask for a review in one step; a reviewer overturns or upholds with a reason; the original result and an audit trail (no raw identifiers) are kept; time to decision is shown | C | FINALE | runs | `app/tests/test_app_flow.py::test_mistake_recovery_flow_request_then_reviewer_overturns` |
| C-22 | 1930 / NCRP incident card (JSON): every field the complaint asks for, blanks left blank, file hashes and timeline; not an official format | C | FINALE | runs | `app/tests/test_finale_features.py::test_incident_card_json` |
| C-12 | An uploaded voice note goes through ffmpeg, a quality gate and AASIST, and returns flagged / no_signal / can't assess; it never crashes and never clears a payee | B/C | FINALE | runs (no accuracy yet: every real result is "can't assess" until a threshold is calibrated) | `voice/tests`, `tests/voice_eval` (synthetic noise, fake detector) |

Only C-16 is a measured number, and it is on synthetic chats (say so). No voice numbers are claimed. Test counts are code tests, not accuracy.
