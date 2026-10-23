# DISCLOSURE

All AI-generated content, datasets, models, libraries and third-party assets. Every role appends here.

## AI assistance
- Claude (Anthropic) drafted code, tests and documentation for this project; the team reviews it. Model/version per session to be noted by the team.

## Data
- All fixture data from Claude A is **synthetic**: fictional names, UPI IDs, accounts, phone-free chats, and SEBI registration numbers with a `DEMO` marker.
- `fixtures/reference/sebi_snapshot_synthetic.json` is **not** the real SEBI list.
- No real chats, voices, bank, customer or platform data is used.
- Voice results in fixtures are **stub values**, not measurements.

## Libraries (Claude A, so far)
| Library | Use | Licence |
|---|---|---|
| Python standard library | schemas, validation | PSF |
| pytest | tests | MIT (not re-verified here; check before the final appendix) |

## Claude C (app, registry, report)
- All files under `app/`, `registry/`, `report/` and C's entries in the shared Markdown files were drafted by Claude acting
  as "Claude C", then run and tested; the team reviews them.
- Demos use Claude A's synthetic fixtures. The stub upload path never produces NO_MAJOR_ISSUE and never shows a voice score.
- No external services are called. Run Streamlit with `--browser.gatherUsageStats false` to disable its telemetry
  (the run scripts do).

| Library | Use | Licence |
|---|---|---|
| Streamlit | app UI | Apache-2.0 |
| pytest | tests | MIT |
| Python standard library (`zipfile`, `hashlib`, `hmac`, `html`, `re`) | intake, hashing, escaping | PSF |

## Not yet used / not yet verified
- OCR and QR libraries (to be chosen; licence to be recorded when added).
- IFSC dataset, real SEBI list snapshot: not downloaded.
