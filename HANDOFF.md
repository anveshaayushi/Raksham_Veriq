# HANDOFF · phase Q0 (clean-install fix)

## What works
A clean install from the declared requirements now passes the whole suite with one command.

## Exact test commands and real results (Claude's Linux sandbox, Python 3.13.16)
    python -m venv .venv
    .venv\Scripts\activate            (Linux/mac: source .venv/bin/activate)
    pip install -r requirements.txt
    python -m pytest                  -> 988 passed
    (without ffmpeg on PATH)          -> 967 passed, 21 skipped, reason shown: "ffmpeg not installed"
`make test` does the same where `make` exists (not on plain Windows; use `python -m pytest`).

## What changed
- `app/tests/test_voice_head.py`: writes its test WAV with Python's built-in `wave` module, so `soundfile` is not needed.
- `pyproject.toml`: `python -m pytest` now runs tests/, app/, registry/, report/ and voice/, and prints skip reasons.
- `requirements.txt` (new, root): includes app and voice requirements. Minimums only; exact pins come in Q1 from your `pip freeze`.
- `Makefile`: `make test`; run scripts install `requirements.txt` and run `python -m pytest`; RUN.md updated.
- STATUS.md rewritten (it was out of date); FINALE_LOG.md started; RESULTS.md has the Q0 rows.

## Still a stub / not done
Nothing in Q0 is a stub. Not verified: Windows run on the laptop (please paste it).

## Plain words
Before, a fresh computer could not run one test because a sound-file library was missing. Now the test uses a built-in
tool instead, and one command runs every test and says why any test was skipped.

## Five likely judge questions
1. How do I run all your tests? `python -m pytest` (988 tests).
2. Why are some tests skipped? Only when ffmpeg is missing; the reason is printed.
3. Are the test counts accuracy? No, they are code checks; accuracy is in RESULTS.md.
4. Did a clean machine pass? Yes in Claude's Linux sandbox; the Windows laptop run is pending your paste.
5. Who wrote the code? Claude (Anthropic) under the team's direction; the team reviews and runs it.

## For you now (laptop)
1. Unzip over the repo, then: `pip install -r requirements.txt` and `python -m pytest`. Paste the last lines.
2. `pip freeze > freeze.txt` and paste it (for Q1 pins).
3. Commit: `git add -A` then `git commit -m "FINALE: Q0 clean-install fix"` then `git push origin --all --tags`.
