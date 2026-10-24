#!/usr/bin/env bash
# Install VERIQ with NO internet, from the wheelhouse/ made by scripts/make_offline_bundle.py. Run in the veriq/ folder.
set -euo pipefail
python3 -m venv .venv
.venv/bin/python -m pip install --no-index --find-links wheelhouse -r requirements.txt
if ls wheelhouse/torch-* >/dev/null 2>&1; then
  .venv/bin/python -m pip install --no-index --find-links wheelhouse torch torchaudio soundfile scikit-learn || true
fi
.venv/bin/python scripts/smoke.py
echo "Installed. Start with: bash app/run_app.sh"
