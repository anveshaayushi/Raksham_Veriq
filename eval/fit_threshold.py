"""Fit a threshold from a DEV predictions file and write a calibration JSON.

    ./veriq-eval --input dev_audio/ --out dev_preds.csv --labels dev_labels.csv   (uncalibrated is fine)
    python -m eval.fit_threshold --preds dev_preds.csv --far 0.05 \
        --polarity higher_is_real --calibrated-on "describe dev sets + codecs + date" --out calibration.json

Picks the threshold so at most --far of GENUINE dev clips are flagged (brief section 7 design target
<= 5%, report the actual). Uses raw scores = score_kind "raw"; Platt/isotonic calibration is a later upgrade.
RULES: dev data only (never the test sets); dev must mix datasets and codecs; the file records the model_version
so it cannot be applied to a different model. The tool refuses mixed model versions.
"""
from __future__ import annotations

import argparse
import csv
import sys

from eval.metrics import threshold_for_far
from voice.calibration import Calibration, save_calibration


def main(argv=None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--preds", required=True)
    ap.add_argument("--far", type=float, default=0.05)
    ap.add_argument("--polarity", choices=["higher_is_real", "higher_is_fake"], default="higher_is_real")
    ap.add_argument("--calibrated-on", required=True)
    ap.add_argument("--out", required=True)
    a = ap.parse_args(argv)
    if a.polarity != "higher_is_real":
        print("only higher_is_real is implemented (AASIST). Negate scores upstream for others.", file=sys.stderr)
        return 2
    with open(a.preds, newline="", encoding="utf-8") as f:
        rows = list(csv.DictReader(f))
    real = [r for r in rows if r.get("label") == "real" and r.get("score")]
    versions = {r["model_version"] for r in rows if r.get("score")}
    if len(versions) != 1:
        print(f"need exactly one model_version among scored rows, found {sorted(versions)}", file=sys.stderr)
        return 2
    if len(real) < 20:
        print(f"only {len(real)} genuine scored clips; refusing to fit (need >=20; more is better)", file=sys.stderr)
        return 2
    thr = threshold_for_far([float(r["score"]) for r in real], a.far)
    mv = versions.pop()
    save_calibration(Calibration(thr, a.polarity, "raw", mv, a.calibrated_on, a.far), a.out)
    flagged = sum(float(r["score"]) < thr for r in real) / len(real)
    print(f"threshold={thr:.6f} model={mv} genuine_flagged_on_dev={flagged:.3f} (n={len(real)})")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
