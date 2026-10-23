# PREBUILT: what existed before the finale (24 Oct 2026, 11:00)

Code commit: **`19a52177ecc14e228afcd3fd3ffed6321e5fbb2c`** (2026-10-23T09:53:47+00:00). Tag `v0-prebuilt` points at the commit that records this hash.
Check with `git log --oneline` and `git show v0-prebuilt --stat`.

## Claude C (app, registry, report) · written 23 Oct 2026, about 14:55–15:40 IST, with AI assistance (Claude)

| Path | What it is | Status |
|---|---|---|
| `app/streamlit_app.py` | 6-step Streamlit app: consent, upload, confirm firm, user-reported payee names, per-payee answer with money-already-sent toggle, reports | works; tested |
| `app/intake.py` | upload guard: types, sizes, counts, magic bytes, in-memory ZIP reading with slip/bomb/encryption checks, SHA-256 | works; tested |
| `app/case.py` | assembles a case from adapters (no Streamlit), builds report data | works; tested |
| `app/contracts.py`, `app/_provisional_schemas.py` | import point for `core/schemas.py`; provisional copy of brief §3.3 used only while it is missing | **provisional** |
| `app/adapters/extract.py` | calls Claude A's parser/extractor if present; otherwise a small labelled STUB (Android, iPhone and plain exports, per-file day/month order, regexes, cues) | **stub** |
| `app/adapters/decide.py` | calls Claude A's `rules.decide` if present; otherwise demo-fixture values or INCONCLUSIVE `STUB-NO-ENGINE` | **stub** |
| `app/adapters/voice.py` | calls Claude B's `voice.analyse` if present; otherwise `cant_assess` | **stub** |
| `app/evidence_input.py` | user-typed bank/UPI-app name → contract `Evidence` (lane payee_name, class A, "User-reported") | works; tested |
| `app/next_steps.py` | money-sent toggle (changes only `next_step`), "This is not a guarantee." enforcement | works; tested |
| `app/text_safety.py` | Markdown escaping, URL defanging, redaction | works; tested |
| `app/demo/scenario_{A,B,C}.json` | fictional chats; voice and decision values **typed by hand** from the brief's ladder, labelled as stubs | **provisional fixtures** |
| `registry/interface.py`, `registry/stub.py` | registry result type, keyed HMAC-SHA256 helper, non-attributable rule; stub fixture table | interface works; registry is a **stub** |
| `report/build.py` | filing sheet and redacted summary, HTML and Markdown | works; tested |
| `app/tests`, `registry/tests`, `report/tests` | 51 tests incl. Streamlit AppTest of the UI flow | run, see RESULTS.md |
| `app/run_app.ps1`, `app/run_app.sh` | one-command setup + tests + start (`-Phone` / `--phone` for hotspot demo) | `.sh` run; `.ps1` not run |
| `app/DEMO.md` | demo script, phone demo, backup-video plan | written |

**Not implemented yet (planned):** SQLite registry, campaign graph, reviewer console, bilingual text, the real parser,
extractor, rules and voice detector (owned by A and B), speech-to-text, QR, video.

## Earlier work by the team (not part of this v0)
- 12 Oct 2026: a Streamlit prototype (`VERIQ_prototype.zip`) with a parser, rules and an AASIST voice check.
- 23 Oct 2026 (morning): a React + FastAPI version (`VERIQ_full_app.zip`).
Neither is used in this v0.

## Git
The repository is already initialised in this folder (`.git`). Author name/email are placeholders; change them with
`git config user.name` / `user.email` before your next commit. To push: create an empty GitHub repo, then
`git remote add origin <url>` and `git push -u origin main --tags`.
