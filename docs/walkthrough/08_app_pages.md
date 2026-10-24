# The app's extra pages

## Plain words
Plain words: besides the main check, the app has a scenario player (watch a scam arrive message by message and see
the answer change; scenario D shows a genuine broker flagged by mistake and cleared by a reviewer), a kit runner for
judges (upload a test folder, get per-file answers and a report), a plan-versus-delivered page, a privacy proof
("delete my data" with before and after), and the measured results with an evasion lab where you can try to fool it.

| | |
|---|---|
| Code | `app/streamlit_app.py`, `app/views/`, `app/results_page.py` |
| Goes in | clicks and uploads |
| Comes out | pages |
| Can do | everything the command line can, on screen |
| Cannot say | - |
| Tests / numbers | `app/tests/test_app_flow.py`, `tests/completeness/test_q3_pages.py` |
| Known limit | Streamlit app for one user at a time; not load-tested. |
