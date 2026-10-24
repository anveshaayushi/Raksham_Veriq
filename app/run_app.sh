#!/usr/bin/env bash
# VERIQ v0 on macOS/Linux. Run from the veriq/ folder:  bash app/run_app.sh [--phone]
set -euo pipefail
[ -d .venv ] || { python3 -m venv .venv; .venv/bin/pip install -r app/requirements.txt; }
.venv/bin/python -m pytest -q tests app registry report
extra=(); [ "${1:-}" = "--phone" ] && extra=(--server.address 0.0.0.0)
exec .venv/bin/python -m streamlit run app/streamlit_app.py --browser.gatherUsageStats false --client.toolbarMode minimal ${extra[@]+"${extra[@]}"}
