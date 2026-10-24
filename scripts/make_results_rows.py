#!/usr/bin/env python3
"""Turn eval predictions CSVs into RESULTS.md rows. Needs NO model and NO audio: only the CSVs.

    python scripts/make_results_rows.py --run "dev:out/asv_dev.csv" --run "eval:out/asv_eval.csv" \
        --command "python scripts/b_run_all.py" --commit <hash> --out out/B_RESULTS_ROWS_ASVSPOOF.md

Every number comes from the CSV rows (recomputed with eval.metrics); nothing is typed by hand. The 95% intervals are
Wilson intervals on the false-alarm and miss rates. The note about in-distribution data is added automatically.
"""
from __future__ import annotations

import argparse
import csv
import math
import sys
from datetime import datetime
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from eval import metrics as M  # noqa: E402


def wilson(k: int, n: int, z: float = 1.96):
    if n == 0:
        return (None, None)
    p = k / n
    d = 1 + z * z / n
    c = (p + z * z / (2 * n)) / d
    h = z * math.sqrt(p * (1 - p) / n + z * z / (4 * n * n)) / d
    return (max(0.0, c - h), min(1.0, c + h))


def fmt(x, nd=3):
    return "n/a" if x is None else f"{x:.{nd}f}"


def block(rows, polarity="higher_is_real"):
    sign = -1.0 if polarity == "higher_is_real" else 1.0
    lab = [r for r in rows if r["label"] in ("real", "fake") and r["score"] != ""]
    fk = [sign * float(r["score"]) for r in lab if r["label"] == "fake"]
    rl = [sign * float(r["score"]) for r in lab if r["label"] == "real"]
    real_p = [r for r in lab if r["label"] == "real" and r["pred_label"]]
    fake_p = [r for r in lab if r["label"] == "fake" and r["pred_label"]]
    fa_k = sum(r["pred_label"] == "fake" for r in real_p)
    ms_k = sum(r["pred_label"] == "real" for r in fake_p)
    return {
        "n": len(lab), "n_real": len(rl), "n_fake": len(fk),
        "auc": M.auc(fk, rl) if fk and rl else None, "eer": M.eer(fk, rl) if fk and rl else None,
        "fa": (fa_k / len(real_p)) if real_p else None, "fa_ci": wilson(fa_k, len(real_p)),
        "miss": (ms_k / len(fake_p)) if fake_p else None, "miss_ci": wilson(ms_k, len(fake_p)),
        "abstained": sum(r["state"] == "cant_assess" for r in lab),
    }


def row_md(name, b, extra):
    ci = lambda t: f"[{fmt(t[0])}, {fmt(t[1])}]"
    return (f"| {name} | n={b['n']} (real {b['n_real']}, fake {b['n_fake']}) | AUC {fmt(b['auc'])} | EER {fmt(b['eer'])} | "
            f"genuine flagged {fmt(b['fa'])} {ci(b['fa_ci'])} | synthetic missed {fmt(b['miss'])} {ci(b['miss_ci'])} | "
            f"abstained {b['abstained']} | {extra} |")


def main(argv=None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--run", action="append", required=True, help="name:path/to/preds.csv (repeatable)")
    ap.add_argument("--command", required=True)
    ap.add_argument("--commit", default="uncommitted")
    ap.add_argument("--polarity", default="higher_is_real")
    ap.add_argument("--out", required=True)
    a = ap.parse_args(argv)
    lines = [f"## ASVspoof 2019 LA runs (generated {datetime.now().strftime('%Y-%m-%d %H:%M')} local; commit {a.commit})", "",
             f"Command: `{a.command}`", "",
             "| run | size | AUC | EER | genuine flagged (95% Wilson) | synthetic missed (95% Wilson) | abstained | by |",
             "|---|---|---|---|---|---|---|---|"]
    detail = []
    for spec in a.run:
        name, _, path = spec.partition(":")
        with open(path, newline="", encoding="utf-8") as f:
            rows = list(csv.DictReader(f))
        mv = sorted({r["model_version"] for r in rows if r["score"] != ""})
        lines.append(row_md(name, block(rows, a.polarity), f"model {','.join(mv) or 'none'}"))
        for col in ("codec", "dataset"):
            vals = sorted({r[col] for r in rows if r[col]})
            if len(vals) > 1:
                for v in vals:
                    detail.append(row_md(f"{name} / {col}={v}", block([r for r in rows if r[col] == v], a.polarity), ""))
    if detail:
        lines += ["", "Breakdown by codec / dataset:", "", lines[4], lines[5]] + detail
    lines += ["", "Read this honestly:",
              "- The `dev` run is scored WITHOUT a threshold on purpose (the threshold is fitted from it), so it shows every clip as abstained and has no forced-label rates. Use its AUC/EER only.",
              "- ASVspoof 2019 LA is the data the pretrained AASIST was TRAINED on (its authors used the LA train split). "
              "Numbers here are in-distribution and flatter the model. They are not evidence for other fake generators, languages or real-world chats.",
              "- `genuine flagged` and `synthetic missed` use the forced label from the dev-fitted threshold (out/calibration_asvspoof_dev.json). "
              "Threshold was fitted on the dev split only; the eval split was never used to fit.",
              "- Audio is ASVspoof-derived: if any clip is shown publicly add the ODC-By notice from DISCLOSURE.md.", ""]
    Path(a.out).parent.mkdir(parents=True, exist_ok=True)
    Path(a.out).write_text("\n".join(lines), encoding="utf-8")
    print("\n".join(lines))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
