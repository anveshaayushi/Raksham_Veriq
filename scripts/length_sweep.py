#!/usr/bin/env python3
"""How does detection change with clip length? Uses the EVAL clean clips already built by b_run_all.py (no new download).

    python scripts/length_sweep.py --calibration out/calibration_asvspoof_dev.json

For each length L the first L seconds of every clean eval clip are cut with ffmpeg and scored with the dev-fitted threshold
(the eval set is never used to fit anything). Output: out/B_LENGTH_SWEEP.md and results/asvspoof/length_sweep/.
`speech_s` is the median seconds of speech the voice activity detector found: at very short lengths it is ~0, so the gate abstains.
Very short clips (0.1 s) usually contain no speech at all; this table shows what that does to the numbers.
"""
from __future__ import annotations

import argparse
import csv
import os
import shutil
import statistics
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "scripts"))
from make_results_rows import block, fmt  # noqa: E402


def main(argv=None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--src", default=str(ROOT / "data" / "subsets" / "eval"))
    ap.add_argument("--calibration", default=str(ROOT / "out" / "calibration_asvspoof_dev.json"))
    ap.add_argument("--lengths", default="0.1,0.25,0.5,1,2,3,4,6")
    ap.add_argument("--aasist-repo", default=os.environ.get("VERIQ_AASIST_REPO", str(ROOT / "external" / "aasist")))
    ap.add_argument("--force", action="store_true")
    a = ap.parse_args(argv)
    src = Path(a.src)
    env = dict(os.environ, VERIQ_AASIST_REPO=a.aasist_repo)
    lab = [r for r in csv.DictReader(open(src / "labels.csv", encoding="utf-8")) if r["codec"] == "clean"]
    if not lab:
        print("no clean clips in labels.csv", file=sys.stderr)
        return 2
    out = ROOT / "out"
    table = ["| first N seconds | clips | scored | speech_s (median) | AUC | EER | genuine flagged | synthetic missed | abstained |",
             "|---|---|---|---|---|---|---|---|---|"]
    for L in [float(x) for x in a.lengths.split(",")]:
        tag = f"{L:g}s"
        d = ROOT / "data" / "subsets" / "eval_len" / tag
        csvp = out / f"asv_evallen_{tag}.csv"
        if not csvp.is_file() or a.force:
            shutil.rmtree(d, ignore_errors=True)
            for sub in ("real", "fake"):
                (d / sub).mkdir(parents=True, exist_ok=True)
            keep = []
            for r in lab:
                p = subprocess.run(["ffmpeg", "-nostdin", "-y", "-loglevel", "error", "-i", str(src / r["file"]), "-t", str(L),
                                    str(d / r["file"])], capture_output=True)
                if p.returncode == 0:
                    keep.append([r["file"], r["label"], r["dataset"], f"first_{tag}", r["language"]])
            (d / "labels.csv").write_text("file,label,dataset,codec,language\n" + "\n".join(",".join(x) for x in keep) + "\n", encoding="utf-8")
            cmd = [sys.executable, "-m", "eval", "--input", str(d), "--out", str(csvp), "--labels", str(d / "labels.csv")]
            if Path(a.calibration).is_file():
                cmd += ["--calibration", a.calibration]
            print("running:", " ".join(cmd), flush=True)
            if subprocess.run(cmd, cwd=ROOT, env=env, capture_output=True, text=True).returncode != 0:
                print(f"FAIL at {tag}", file=sys.stderr)
                return 1
        rows = list(csv.DictReader(open(csvp, newline="", encoding="utf-8")))
        b = block(rows)
        sp = [float(r["speech_seconds"]) for r in rows if r["speech_seconds"] != ""]
        table.append(f"| {tag} | {len(rows)} | {sum(r['score'] != '' for r in rows)} | {fmt(statistics.median(sp) if sp else None, 2)} | "
                     f"{fmt(b['auc'])} | {fmt(b['eer'])} | {fmt(b['fa'])} | {fmt(b['miss'])} | {b['abstained']} |")
        print(table[-1], flush=True)
    note = ["", "Read this honestly:",
            "- Same 200 base clips (100 real, 100 fake, ASVspoof 2019 LA eval, clean only) at every length. The model was trained on this dataset.",
            "- Threshold = dev-fitted (not tuned on these clips). If genuine flagged is far above 5%, the threshold does not transfer to that length.",
            "- 'abstained' counts clips the gate refuses (not enough speech). A refusal is the correct answer for a clip with no speech.",
            "- Many LA clips are only a few seconds long, so the longest rows are often the whole clip.", ""]
    text = "\n".join(table + note)
    (out / "B_LENGTH_SWEEP.md").write_text(text, encoding="utf-8")
    pub = ROOT / "results" / "asvspoof" / "length_sweep"
    pub.mkdir(parents=True, exist_ok=True)
    shutil.copy(out / "B_LENGTH_SWEEP.md", pub / "B_LENGTH_SWEEP.md")
    for p in out.glob("asv_evallen_*.csv"):
        with open(p, newline="", encoding="utf-8") as f:
            rd = csv.DictReader(f)
            keep = [c for c in rd.fieldnames if c != "path"]
            rows = [{c: r[c] for c in keep} for r in rd]
        with open(pub / p.name, "w", newline="", encoding="utf-8") as f:
            w = csv.DictWriter(f, fieldnames=keep)
            w.writeheader()
            w.writerows(rows)
    print("\n" + text)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
