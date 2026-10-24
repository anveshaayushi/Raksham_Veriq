#!/usr/bin/env bash
# VERIQ on macOS/Linux. Run from the veriq/ folder:  bash app/run_app.sh [--phone] [--no-voice] [--skip-tests]
set -euo pipefail
phone=0; voice=1; tests=1
for a in "$@"; do case "$a" in --phone) phone=1;; --no-voice) voice=0;; --skip-tests) tests=0;; esac; done
[ -x .venv/bin/python ] || python3 -m venv .venv
.venv/bin/python -m pip install -q -r requirements.txt          # pinned versions
if [ "$voice" = 1 ]; then .venv/bin/python -m pip install -q -r requirements-voice.txt || echo "voice extras not installed: voice notes will say can't assess"; fi
command -v ffmpeg >/dev/null || echo "ffmpeg not found: install it (apt install ffmpeg / brew install ffmpeg)"
if [ "$tests" = 1 ]; then .venv/bin/python -m pytest || echo "Some tests failed; starting the app anyway."; fi
extra=(); [ "$phone" = 1 ] && extra=(--server.address 0.0.0.0)
exec .venv/bin/python -m streamlit run app/streamlit_app.py --browser.gatherUsageStats false --client.toolbarMode minimal ${extra[@]+"${extra[@]}"}
