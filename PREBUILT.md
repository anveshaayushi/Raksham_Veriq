# PREBUILT: what was built before the finale

Disclosure per the organisers' rule: clearly state what was built before the finale versus during it.

**Honesty note.** The Round 1 deck described a *plan*. No working code existed when it was submitted.
Everything below was written on **23 Oct 2026 (pre-build window, before the finale starts on 24 Oct)**,
with AI assistance (Claude, Anthropic), and reviewed by the team.

**Commit hashes.** Claude A's files were written in a scratch workspace and first committed when Claude C merged
them (commit `4a113b18fd`). See "Git" below.

| Area | Files | Written (IST) | Team-repo commit |
|---|---|---|---|
| Shared contract | `core/schemas.py` | 2026-10-23 (afternoon) | `4a113b18fd` |
| Fixture validator | `core/validate.py` | 2026-10-23 | `4a113b18fd` |
| Golden fixtures (synthetic) | `fixtures/scenario_*.json`, `fixtures/reference/sebi_snapshot_synthetic.json`, `fixtures/build_fixtures.py` | 2026-10-23 | `4a113b18fd` |
| Golden/schema tests | `tests/golden/test_fixtures.py` | 2026-10-23 | `4a113b18fd` |
| Shared docs | `CHANGES_REQUESTED.md`, `STATUS.md`, `PREBUILT.md`, `DISCLOSURE.md`, `RESULTS.md` | 2026-10-23 | `4a113b18fd` |

Claude B and Claude C add their own rows.

## Claude C (app, registry, report) · written 23 Oct 2026, about 14:55 IST – 16:16 IST, with AI assistance (Claude)

| Path | What it is | Status |
|---|---|---|
| `app/streamlit_app.py` | 6-step Streamlit app: consent, upload, confirm firm, user-reported payee names, per-payee answer with money-already-sent toggle, reports | works; tested |
| `app/intake.py` | upload guard: types, sizes, counts, magic bytes, in-memory ZIP reading with slip/bomb/encryption checks, SHA-256 | works; tested |
| `app/case.py` | assembles a case from adapters (no Streamlit), builds report data | works; tested |
| `app/contracts.py`, `app/_provisional_schemas.py` | import point for Claude A's `core/schemas.py` (now the real contract); the provisional copy is only a fallback | works; tested |
| `app/adapters/extract.py` | calls Claude A's parser/extractor if present; otherwise a small labelled STUB (Android, iPhone and plain exports, per-file day/month order, regexes, cues) | **stub** |
| `app/adapters/decide.py` | calls Claude A's `rules.decide` if present; otherwise INCONCLUSIVE (`INCONCL`) for uploads; demos show Claude A's golden-fixture expected values, labelled as such | **stub** |
| `app/adapters/voice.py` | uses Claude B's `voice.stub.stub_result` for demos; `voice.analyse` for uploads when B exposes it, else `cant_assess`; hides scores without a calibrated threshold | **stub** |
| `app/evidence_input.py` | user-typed bank/UPI-app name → contract `Evidence` (lane payee_name, class A, "User-reported") | works; tested |
| `app/next_steps.py` | money-sent toggle (changes only `next_step`), "This is not a guarantee." enforcement | works; tested |
| `app/text_safety.py` | Markdown escaping, URL defanging, redaction | works; tested |
| `app/case.py` demo loading | loads Claude A's `fixtures/scenario_*.json`; if the user edits a demo input, the golden answer is dropped and the stub runs | works; tested |
| `registry/interface.py`, `registry/stub.py` | registry result type, keyed HMAC-SHA256 helper, non-attributable rule; stub fixture table | interface works; registry is a **stub** |
| `report/build.py` | filing sheet and redacted summary, HTML and Markdown | works; tested |
| `app/tests`, `registry/tests`, `report/tests` | 68 tests (incl. golden-fixture checks, a test double of B's `voice/stub.py`, Streamlit AppTest of the UI flow) | run, see RESULTS.md |
| `app/run_app.ps1`, `app/run_app.sh` | one-command setup + tests + start (`-Phone` / `--phone` for hotspot demo) | `.sh` run; `.ps1` not run |
| `app/DEMO.md` | demo script, phone demo, backup-video plan | written |

**Not implemented yet (planned):** SQLite registry, campaign graph, reviewer console, bilingual text, the real parser,
extractor, rules and voice entry point (owned by A and B), speech-to-text, QR, video.

## Earlier work by the team (not part of this v0)
- 12 Oct 2026: a Streamlit prototype (`VERIQ_prototype.zip`) with a parser, rules and an AASIST voice check.
- 23 Oct 2026 (morning): a React + FastAPI version (`VERIQ_full_app.zip`).
Neither is used in this v0.

## Git
Repository in this folder (`.git`). History before the finale:

| Commit | What |
|---|---|
| `19a52177ec` | Claude C v0 (app, registry, report) |
| `1f52e04` | Claude C: Claude B's voice stub wired in |
| `4a113b18fd` | Claude A's contract, fixtures, golden tests merged; app moved onto A's contract |

Tag `v0-prebuilt` points at the latest pre-finale commit. Check with `git log --oneline` and `git show v0-prebuilt --stat`.
Author name/email are placeholders; set `git config user.name` / `user.email` before your next commit. To push: create an
empty GitHub repo, then `git remote add origin <url>` and `git push -u origin main --tags`.
