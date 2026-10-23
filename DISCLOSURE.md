# DISCLOSURE: AI assistance, libraries, data

## AI-generated content
- All files under `app/`, `registry/`, `report/` and the C entries in the shared Markdown files were drafted by an AI
  assistant (Claude, Anthropic) acting as "Claude C", then run and tested; the team reviews them.
- Demo chats in `app/demo/` are fictional and written by the assistant. Their stub voice and decision values were
  typed by hand from the team brief, not produced by any model or rules engine.

## Libraries (Claude C)
| Library | Use | Licence |
|---|---|---|
| Streamlit | app UI | Apache-2.0 |
| pytest | tests | MIT |
| Python standard library (`zipfile`, `hashlib`, `hmac`, `html`, `re`) | intake, hashing, escaping | PSF |

## Data
- No real chats, voices, bank, customer or platform data. All identifiers in fixtures are fictional.
- No external services are called. Run Streamlit with `--browser.gatherUsageStats false` to disable its telemetry.
