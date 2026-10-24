# TESTPLAN: what is tested, how, and what is not

Organisers' rule 4: completeness of tests matters as much as accuracy. This file maps every claim in CLAIMS.md and every
requirement we hold ourselves to onto the tests that check it. `tests/completeness/test_testplan.py` fails if a test
named here no longer exists, or if a CLAIMS.md row is missing from this plan, so this file cannot silently go stale.

Run everything: `python -m pytest` (one command). Measured test quality: `make reproduce` (coverage, two random-order
runs) and `python scripts/mutation_check.py` (planted bugs). Current numbers: RESULTS.md, section "Test quality".

**Test types used below.** unit: one function. property: every combination of inputs (exhaustive, not sampled).
golden: exact match with hand-checked expected output. integration/UI: the real Streamlit script driven by
`streamlit.testing` (no browser). adversarial: attacks a scammer would try. benchmark: measured numbers on a dataset.
security: hostile input or data-protection checks. regression: a test added after a bug or a surviving mutant.
reproducibility: regenerated data and results equal the committed ones.

## 1. CLAIMS.md rows

| Claim | Tests (file::test) | Types |
|---|---|---|
| C-1 consent, file type, size, magic bytes, ZIP safety | `app/tests/test_app_flow.py::test_consent_required_before_upload`, `app/tests/test_intake.py::test_zip_bomb_ratio_rejected`, `app/tests/test_intake.py::test_zip_slip_rejected`, `tests/edge/test_edge_inputs.py::test_hostile_zip_is_refused`, `tests/edge/test_edge_inputs.py::test_oversize_chat_and_audio_are_refused` | integration/UI, security |
| C-2 every payment destination is a separate payee | `app/tests/test_extract_stub.py::test_payees_separate_and_cues`, `app/tests/test_adapters_and_case.py::test_payees_stay_separate_with_own_amounts` | unit, integration |
| C-3 user's own app check is class A, labelled user-reported | `app/tests/test_adapters_and_case.py::test_user_reported_evidence_is_class_a_and_labelled` | unit |
| C-4 "money already sent" changes only the next step | `app/tests/test_next_steps_and_safety.py::test_money_sent_changes_only_next_step`, `app/tests/test_app_flow.py::test_money_sent_toggle_changes_only_next_step`, `app/tests/test_golden_integration.py::test_money_sent_variant` | unit, golden, UI |
| C-5 filing sheet full identifiers, summary redacted | `report/tests/test_reports.py::test_filing_sheet_fields_and_blanks`, `report/tests/test_reports.py::test_summary_redacts_accounts_and_phones_and_keeps_standing_line` | unit |
| C-6 chat text escaped, links defanged | `report/tests/test_reports.py::test_untrusted_chat_text_is_escaped`, `report/tests/test_reports.py::test_links_are_defanged_in_markdown_reports`, `app/tests/test_next_steps_and_safety.py::test_urls_are_defanged_so_markdown_cannot_autolink` | security, regression (M10) |
| C-7 "No major issue" always says "This is not a guarantee." | `app/tests/test_next_steps_and_safety.py::test_no_major_issue_always_says_not_a_guarantee`, `report/tests/test_reports.py::test_no_major_issue_disclaimer_in_reports`, `tests/golden/test_fixtures.py::test_no_major_issue_requires_disclaimer` | unit, golden |
| C-8 registry stores only keyed hashes | `registry/tests/test_sqlite_registry.py::test_no_raw_identifiers_or_tokens_in_the_file`, `registry/tests/test_registry.py::test_hmac_is_keyed_namespaced_and_not_a_plain_hash` | security |
| C-9 linking needs 2 independent reporters or a reviewer | `registry/tests/test_sqlite_registry.py::test_two_independent_reporters_link`, `registry/tests/test_sqlite_registry.py::test_poisoning_one_token_twenty_false_reports`, `registry/tests/test_sqlite_registry.py::test_poisoning_five_tokens_in_one_minute` | unit, adversarial |
| C-10 gateways never stored or linked; broken registry is "unavailable" | `registry/tests/test_sqlite_registry.py::test_gateway_handles_never_stored_or_linked`, `registry/tests/test_sqlite_registry.py::test_locked_database_is_unavailable`, `tests/completeness/test_core_paths.py::test_every_registry_call_says_unavailable_when_the_file_is_not_a_database`, `tests/edge/test_edge_inputs.py::test_locked_registry_is_shown_as_unavailable_in_a_case` | security, edge |
| C-11 one answer per payee from fixed rules, computed live | `tests/golden/test_decide_golden.py::test_decide_on_fixture_evidence_matches_exactly`, `tests/golden/test_decide_golden.py::test_raw_chat_end_to_end` | golden |
| C-12 voice note: ffmpeg, gate, AASIST; never crashes, never clears | `voice/tests/test_analyse.py::test_bad_input_never_raises_and_abstains`, `tests/voice_eval/test_pipeline.py::test_bad_inputs_never_raise`, `tests/completeness/test_voice_paths.py::test_decoder_errors_are_codes_not_crashes`, `tests/completeness/test_voice_detector.py::test_loads_scores_in_batches_and_versions_by_weights_hash` | unit, security |
| C-13 more risk never milder; voice never clears; unavailable is not clean | `tests/golden/test_engine_properties.py::test_every_combination_is_valid_and_honest`, `tests/golden/test_engine_properties.py::test_more_risk_never_milder`, `tests/golden/test_engine_properties.py::test_voice_never_clears`, `tests/golden/test_engine_properties.py::test_unavailable_registry_is_not_clean` | property (all 384 combinations) |
| C-14 gateway, personal-looking, initials, near spellings are "unverified" | `tests/golden/test_engine_properties.py::test_name_matcher_classes` | unit |
| C-15 judge edits the typed name, answer recomputed | `app/tests/test_golden_integration.py::test_judge_can_vary_the_demo_and_the_engine_recomputes` | integration |
| C-16 chat benchmark numbers | `tests/completeness/test_bench_smoke.py::test_committed_test_results_match_a_fresh_run`, `tests/completeness/test_bench_smoke.py::test_chat_generator_reproduces_the_committed_benchmark_byte_for_byte` | benchmark, reproducibility |
| C-17 UPI ID inside a QR image found; QR name only asks for review | `app/tests/test_finale_features.py::test_qr_payee_is_extracted_as_image_source_and_compared`, `tests/completeness/test_core_paths.py::test_qr_in_a_huge_screenshot_and_cv2_errors` | integration, edge |
| C-18 look-alike names go to review; genuine variants match | `app/tests/test_finale_features.py::test_lookalike_shell_names_go_to_review`, `tests/completeness/test_bench_smoke.py::test_red_team_defences_hold_and_known_gaps_are_reported` | adversarial |
| C-19 obfuscated pressure phrases caught | `app/tests/test_finale_features.py::test_obfuscated_pressure_phrases`, `app/tests/test_finale_features.py::test_onboarding_fee_is_not_a_withdrawal_fee` | adversarial |
| C-20 unassessable voice + pressure gives "Don't pay yet: high pressure" | `app/tests/test_finale_features.py::test_high_pressure_variant_for_unassessable_audio` | unit |
| C-21 mistake recovery: request, overturn/uphold, audit without raw identifiers | `app/tests/test_app_flow.py::test_mistake_recovery_flow_request_then_reviewer_overturns`, `app/tests/test_finale_features.py::test_review_request_overturn_and_audit_has_no_raw_identifier` | UI, security |
| C-22 1930 / NCRP incident card | `app/tests/test_finale_features.py::test_incident_card_json` | unit |
| C-23 trained voice head numbers | `app/tests/test_voice_head.py::test_head_files_match_and_load_without_torch`, `tests/completeness/test_bench_smoke.py::test_voice_train_eval_end_to_end_with_a_stand_in_model`, `tests/completeness/test_bench_smoke.py::test_voice_set_builder_end_to_end_with_stand_in_inputs` | benchmark (script), reproducibility |
| C-24 a judge can paste any chat | `app/tests/test_app_flow.py::test_judge_can_paste_a_chat_and_get_an_answer` | UI |
| C-25 the app shows its own measured results | `app/tests/test_app_flow.py::test_results_page_shows_measured_numbers` | UI |
| C-29 ASVspoof 2019 LA results for pretrained AASIST (in-distribution) | `tests/completeness/test_q2_tools.py::test_asvspoof_rows_recompute_from_the_committed_predictions`, `tests/voice_eval/test_subset_zip_and_rows.py` (B's subset builder and rows tool) | benchmark, reproducibility |
| C-30 trained head fails cross-dataset; off by default | `tests/completeness/test_q2_tools.py::test_head_cross_dataset_rows_recompute_and_head_is_off_by_default`, `tests/completeness/test_voice_paths.py::test_head_installer_is_off_by_default` | benchmark, regression |
| C-31 privacy proof | `tests/completeness/test_privacy_proof.py::test_delete_my_data_empties_session_and_temp_folders`, `tests/completeness/test_privacy_proof.py::test_voice_note_leaves_no_file_and_registry_has_no_raw_identifier` | security |
| C-32 kit runner | `tests/completeness/test_kit_runner.py::test_kit_runner_on_a_mixed_kit_never_crashes_and_reports`, `tests/completeness/test_kit_runner.py::test_kit_zip_safety_and_app_kit_function` | integration, security |
| C-33 scenario player | `tests/completeness/test_q3_pages.py::test_scenario_player_plays_and_scenario_d_is_cleared_by_review`, `tests/completeness/test_q3_pages.py::test_player_recomputes_after_an_edit` | integration/UI |
| C-34 name pairs | `tests/completeness/test_q2_tools.py::test_name_pair_set_results_match_the_committed_file` | benchmark |
| C-35 SMS cues | `tests/completeness/test_q2_tools.py::test_sms_cue_check_on_a_mock_file` (script only; data not run yet) | benchmark (script) |
| C-36 blind chats | `tests/completeness/test_q2_tools.py::test_blind_runner_counts_outcomes_and_runs_only_once` (script only; data not run yet) | benchmark (script) |
| C-37 retrained voice head, grouped CV | `tests/completeness/test_cross_dataset.py::test_cross_dataset_script_on_cached_embeddings` | benchmark (script) |
| C-38 offline install and smoke | `tests/completeness/test_deploy.py::test_smoke_without_the_web_app`, `tests/completeness/test_deploy.py::test_offline_mode_blocks_outgoing_but_not_loopback`, `tests/completeness/test_deploy.py::test_container_files_follow_the_rules` | deployment, security |
| Q5 demo story and documents | `tests/completeness/test_acceptance.py::test_demo_story_and_document_checks_pass`, `app/tests/test_app_flow.py::test_second_victim_report_links_the_payee` | acceptance, UI |
| C-39 voice weak cue | `tests/completeness/test_voice_weak_cue.py::test_flag_only_escalates_to_review`, `tests/completeness/test_voice_weak_cue.py::test_no_signal_never_clears_a_payee`, `tests/completeness/test_voice_weak_cue.py::test_default_threshold_is_bs_asvspoof_dev_file_and_can_be_switched_off` | unit, safety |
| C-40 alert, actions, safeguards running | `tests/completeness/test_safeguards_running.py::test_no_raw_chat_or_audio_left_on_disk_after_a_full_check`, `tests/completeness/test_safeguards_running.py::test_offline_mode_full_check_makes_no_outgoing_connection`, `tests/completeness/test_safeguards_running.py::test_alert_says_why_and_offers_actions_and_delete_my_data_clears_everything` | security, UI |
| C-41 mistake path measured | `tests/completeness/test_journeys.py::test_mistake_path_genuine_user_is_cleared_with_reason_and_audit` | UI, responsible AI |
| C-42 live journey | `tests/completeness/test_journeys.py::test_live_journey_five_variations_reported_including_misses` | integration |
| Blind dataset loaders (load only) | `tests/completeness/test_datasets_load.py::test_blind_ai_loader_joins_and_reports_problems`, `tests/completeness/test_datasets_load.py::test_other_loaders_and_missing_sets` | data checks |
| C-26 one command reproduces data, tests and benchmarks | `tests/completeness/test_reproduce_tools.py::test_reproduce_environment_data_and_voice_checks`, `tests/completeness/test_reproduce_tools.py::test_reproduce_detects_a_changed_benchmark_result`, `tests/completeness/test_bench_smoke.py::test_campaign_generator_reproduces_the_committed_files` | reproducibility |
| C-27 coverage, planted bugs caught, random order | `tests/completeness/test_reproduce_tools.py::test_every_mutant_still_applies_to_exactly_one_place`, `tests/completeness/test_reproduce_tools.py::test_mutation_check_kills_a_mutant_on_a_small_suite` (plus `make reproduce-full`) | mutation, reproducibility |
| C-28 hostile and broken inputs | `tests/edge/test_edge_inputs.py::test_hostile_zip_is_refused`, `tests/edge/test_edge_inputs.py::test_legacy_encodings_are_refused_with_a_fix`, `tests/edge/test_edge_inputs.py::test_text_without_timestamps_is_explained_not_guessed`, `tests/edge/test_edge_inputs.py::test_zero_second_audio_cannot_be_assessed`, `tests/edge/test_edge_inputs.py::test_garbage_with_an_opus_header_cannot_be_assessed`, `tests/edge/test_edge_inputs.py::test_locked_registry_is_shown_as_unavailable_in_a_case` | edge, security |

## 2. Requirements beyond the claims

| Requirement | Tests | Types |
|---|---|---|
| Shared contract (core/schemas.py) round-trips; unknown fields rejected | `tests/golden/test_fixtures.py::test_roundtrip_all_objects`, `tests/golden/test_fixtures.py::test_unknown_and_missing_fields_rejected` | unit |
| Fixture validator rejects each kind of broken fixture (23 kinds) | `tests/completeness/test_core_paths.py::test_validator_rejects_each_broken_fixture` | unit, regression |
| Case result = worst payee | `app/tests/test_next_steps_and_safety.py::test_case_result_is_worst_payee` | unit |
| Class D (QR, chat) never decides alone | `tests/golden/test_fixtures.py::test_validator_catches_decision_on_class_d_only` (validator) and mutant M15 (engine) | unit, mutation |
| Voice: uncalibrated detector never shows a verdict or a score | `tests/voice_eval/test_pipeline.py::test_uncalibrated_abstains_but_keeps_raw_score`, `voice/tests/test_app_adapter.py::test_adapter_hides_numbers_when_uncalibrated` | unit |
| Voice: a calibration for another model is refused | `tests/voice_eval/test_pipeline.py::test_calibration_for_other_model_is_refused`, `app/tests/test_voice_head.py::test_head_refuses_a_different_base_model` | unit |
| Voice: uploaded audio is deleted after analysis | `voice/tests/test_analyse.py::test_temp_files_are_deleted` | security |
| Voice: the app never crashes when the voice module is missing or broken | `tests/completeness/test_voice_paths.py::test_adapter_without_voice_package_is_a_labelled_stub`, `tests/completeness/test_voice_paths.py::test_adapter_without_entry_point_and_with_crashing_entry_point`, `tests/completeness/test_voice_paths.py::test_service_last_resort_guard` | unit |
| Edge inputs (organisers' list): empty, huge, zip bomb, encodings, no timestamps, mixed languages, 0 s audio, corrupt opus, registry locked | `tests/edge/test_edge_inputs.py` (one test or more per item; see its docstring) | edge, security |
| Mixed Hindi/English account number found | `tests/edge/test_edge_inputs.py::test_mixed_hindi_hinglish_english_chat` | regression (found and fixed in Q1: "खाता संख्या" was missed) |
| Synthetic data generation code is submitted and reproduces the data | `tests/completeness/test_bench_smoke.py::test_chat_generator_reproduces_the_committed_benchmark_byte_for_byte`, `tests/completeness/test_bench_smoke.py::test_campaign_generator_reproduces_the_committed_files` | reproducibility |
| The reproduction and mutation tools work and detect changes | `tests/completeness/test_reproduce_tools.py::test_reproduce_detects_a_changed_benchmark_result`, `tests/completeness/test_reproduce_tools.py::test_mutation_check_reports_survivors_and_stale_mutants`, `tests/completeness/test_reproduce_tools.py::test_every_mutant_still_applies_to_exactly_one_place` | unit |
| Test order does not matter | `make reproduce` (two pytest-randomly seeds) | reproducibility |

## 3. Mutation check (planted bugs)

`scripts/mutation_check.py` plants 17 bugs, one at a time, in a temporary copy: LINKED never fires; rule rank flipped;
hard-cue block removed; voice clears a payee; flagged voice ignored; gateway exclusion dropped; registry threshold 1;
burst protection off; defanging broken (app, reports); "not a guarantee" dropped; money-sent toggle changes the result;
zip-ratio check off; broken registry says "clean"; QR name trusted like the user's app; SEBI conflict ignored; raw
identifiers stored. Result and survivors: RESULTS.md and `results/mutation.json`.

## 4. What is NOT tested, and why

| Not tested | Why | What we do instead |
|---|---|---|
| Real victims' chats | none available to us; privacy | synthetic benchmark (circular: see REPRODUCE.md), blind teammate set (C-36), public SMS Spam set (C-35) |
| Real voice clones of real people | not allowed (rules) | Kokoro TTS voices, public FSDD speakers; ASVspoof 2019 LA planned in Q2 |
| Voice detection on a dataset none of our models saw in any form (In-the-Wild, real WhatsApp notes, Hindi) | not downloaded / not available with consent | ASVspoof LA run (C-29, C-30, C-37); voice stays a review cue and abstains |
| The browser itself (clicks in Chrome/Edge, phone layout) | AppTest drives the script, not a browser | manual check in the demo checklist (DEMO_12MIN.md); Playwright run once on 24 Oct |
| Live bank, UPI or SEBI lookups | not allowed (rules); no partnership | user's own app check (class A), dated synthetic SEBI snapshot |
| OCR of screenshots (text in images) | not built | QR codes only; documented gap |
| Load / many simultaneous users | single-user laptop demo | not claimed |
| Real AASIST weights inside the normal test run | weights are a 1.3 MB third-party download, not in git | `test_real_aasist_if_available` runs when `VERIQ_AASIST_REPO` is set (passes in the sandbox) |
| Reworded scam phrases without any keyword, identical name on a mule account | known gaps, kept on purpose in the red-team set (the shop-name gap was fixed in Q2) | listed as "known gap" rows in `bench/results_adversarial.json` |
