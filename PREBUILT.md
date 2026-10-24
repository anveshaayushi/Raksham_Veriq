# PREBUILT: what this repository contained before the finale

Scope: this file covers the code in **this repository**. Everything in tag `v0-prebuilt` was written on
**23 Oct 2026 between 14:55 and 22:49 IST** (pre-build window, before the finale started on 24 Oct, 11:00 IST),
with AI assistance (Claude, Anthropic), and reviewed by the team. Commit times in `git log` are the record.

## Declared prototype: tag `v0-prebuilt` (commit `8718c9c`) claims ONLY

1. **The app flow**: consent, upload validation (types, sizes, magic bytes, safe ZIP reading, SHA-256), claimed-firm
   confirmation, and the step-by-step Streamlit screens.
2. **User-reported payee names and the per-payee answer screen**, with the money-already-sent toggle that changes only
   the next step.
3. **The 1930 report**: filing sheet and redacted shareable summary (HTML and Markdown).
4. **The shared contract, golden fixtures and tests**: `core/schemas.py`, `core/validate.py`, three synthetic scenarios,
   45 golden/schema tests (Claude A) and the app/report/registry tests (Claude C).

Also present but **labelled as stubs**, not claimed as working features: the registry stub, voice-plumbing drafts
(adapters that call Claude B's `voice` package when it exists), a small regex parser/extractor stub, and a screen that
replays the golden fixtures' expected answers ("Claude A's golden fixture ... rules engine not built yet").

**Not in `v0-prebuilt`:** the WhatsApp parser, payee extractor, name matcher and decision rules (Claude A's
`parsing/`, `extract/`, `match/`, `rules/` are empty), any voice detector or threshold, the SQLite registry, the
campaign graph and the reviewer console. These are built during the finale.

## Files in `v0-prebuilt`

| Owner | Path | What it is | Status at v0-prebuilt |
|---|---|---|---|
| A | `core/schemas.py`, `core/validate.py` | shared contract and fixture validator | tested |
| A | `fixtures/`, `tests/golden/` | 3 synthetic scenarios, synthetic SEBI snapshot, 45 tests | tested |
| C | `app/streamlit_app.py`, `app/intake.py`, `app/case.py`, `app/evidence_input.py`, `app/next_steps.py`, `app/text_safety.py`, `app/contracts.py` | app flow, upload checks, user-reported names, money-sent toggle, escaping/redaction | tested |
| C | `app/adapters/extract.py`, `decide.py`, `voice.py` | call A's and B's modules when present; otherwise labelled stubs | **stub** |
| C | `report/build.py` | 1930 filing sheet and redacted summary | tested |
| C | `registry/interface.py`, `registry/stub.py` | registry interface, keyed HMAC helper, stub table | interface tested; registry **stub** |
| C | `app/run_app.ps1`, `app/run_app.sh`, `app/RUN.md`, `app/DEMO.md` | run scripts and demo notes | `.sh` run on Linux; `.ps1` not run |

## Drafted before the finale but not in this repository until the finale
- **Claude B's `voice/` and `eval/` drafts** were written on 23 Oct 2026 (in `veriq_claude_B.zip`), and the AASIST
  self-check was run on the team laptop on 23 Oct (15:20 IST). They entered this repository during the finale, in the
  commit that merges Claude B (24 Oct). `voice/service.py`, the contract-valid `voice/stub.py`, `voice/tests`,
  `eval/fit_threshold` and `scripts/` are finale work (see HANDOFF_B_to_C.md).

## Git

| Commit (23 Oct, IST) | What |
|---|---|
| `19a5217` 15:23 | Claude C v0: app, filing sheet, redacted summary, registry stub |
| `64bfbb6` 15:23 | record the v0 hash |
| `1f52e04` 16:04 | Claude B's voice stub wired in |
| `4a113b1` 16:19 | Claude A's contract, fixtures and golden tests merged |
| `6c2b592` 16:20 | record the merge hash |
| `8718c9c` 22:49 | voice transcripts merged before A's extractor; **tag `v0-prebuilt`** |

Everything after `8718c9c` is finale work; those commit messages start with `FINALE:`.
Check with `git log --oneline` and `git show v0-prebuilt --stat`.
