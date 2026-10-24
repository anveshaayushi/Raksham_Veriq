#!/usr/bin/env python3
"""Claude B: ONE command that runs the whole ASVspoof evaluation and packs everything Claude C needs.

    python scripts/b_run_all.py --zip C:\\Users\\anves\\Downloads\\LA.zip

Steps (each prints PASS or FAIL; a FAIL stops the run and says which command to send back):
  1 selfcheck   AASIST loads                     2 dev subset    from the zip, no extraction
  3 eval subset from the zip (held out)          4 score dev     uncalibrated
  5 fit         threshold on DEV only            6 score eval    with the dev-fitted threshold
  7 length      the same dev clips cut to 1, 2, 4 s, scored      8 rows + bundle zip

Output (all under out/ and data/subsets/, both git-ignored):
  out/asv_dev.csv, out/asv_eval.csv, out/asv_len_*.csv  (+ .summary.json)   out/calibration_asvspoof_dev.json (small; deliberately NOT installed as voice/calibration.json)
  out/B_RESULTS_ROWS_ASVSPOOF.md                         out/veriq_B_results_bundle.zip  <- send this to Claude C
Claude C does NOT need the 7 GB dataset: the bundle holds the small labelled clips (a few hundred), the predictions and the rows.
Resumable: a step whose output already exists is skipped unless --force.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import shutil
import subprocess
import sys
import zipfile
from datetime import datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
PY = sys.executable
LOG = ROOT / "out" / "b_run_all.log"


def say(msg: str) -> None:
    print(msg, flush=True)
    LOG.parent.mkdir(parents=True, exist_ok=True)
    with open(LOG, "a", encoding="utf-8") as f:
        f.write(msg + "\n")


def run(cmd: list, step: str, env=None) -> None:
    say(f"[{step}] $ " + " ".join(str(c) for c in cmd))
    p = subprocess.run([str(c) for c in cmd], cwd=ROOT, capture_output=True, text=True, env=env)
    tail = (p.stdout + p.stderr).strip().splitlines()[-12:]
    for line in tail:
        say("    " + line)
    if p.returncode != 0:
        say(f"[{step}] FAIL (exit {p.returncode}). Send Claude B the last 25 lines of out\\b_run_all.log")
        raise SystemExit(1)
    say(f"[{step}] PASS")


def sha(p: Path) -> str:
    h = hashlib.sha256()
    with open(p, "rb") as f:
        for b in iter(lambda: f.read(1 << 20), b""):
            h.update(b)
    return h.hexdigest()


def git_hash() -> str:
    try:
        return subprocess.run(["git", "rev-parse", "--short", "HEAD"], cwd=ROOT, capture_output=True, text=True).stdout.strip() or "uncommitted"
    except OSError:
        return "uncommitted"


def main(argv=None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--zip", required=True, help="path to LA.zip")
    ap.add_argument("--n-dev", type=int, default=60, help="real and fake clips each from dev")
    ap.add_argument("--n-eval", type=int, default=100, help="real and fake clips each from eval")
    ap.add_argument("--far", type=float, default=0.05)
    ap.add_argument("--aasist-repo", default=os.environ.get("VERIQ_AASIST_REPO", str(ROOT / "external" / "aasist")))
    ap.add_argument("--force", action="store_true")
    ap.add_argument("--skip-selfcheck", action="store_true")
    a = ap.parse_args(argv)

    env = dict(os.environ, VERIQ_AASIST_REPO=a.aasist_repo)
    out, sub = ROOT / "out", ROOT / "data" / "subsets"
    cal = out / "calibration_asvspoof_dev.json"   # NOT installed into voice/: see docs/history/HANDOFF_B_FINAL.md
    say(f"=== b_run_all {datetime.now():%Y-%m-%d %H:%M:%S} local, commit {git_hash()}, python {sys.version.split()[0]} ===")

    if not a.skip_selfcheck:
        run([PY, "-m", "voice.detector", "--selfcheck"], "1 selfcheck", env)

    def subset(split, n, seed, name):
        d = sub / name
        if (d / "labels.csv").is_file() and not a.force:
            say(f"[subset {name}] exists, skipped")
            return
        shutil.rmtree(d, ignore_errors=True)
        run([PY, "scripts/make_asvspoof_subset.py", "--zip", a.zip, "--split", split, "--n-real", n, "--n-fake", n,
             "--seed", seed, "--codecs", "opus,mp3", "--out", d], f"subset {name}")

    subset("dev", a.n_dev, 1234, "dev")
    subset("eval", a.n_eval, 4321, "eval")

    def score(name, folder, calibration=None):
        csvp = out / f"{name}.csv"
        if csvp.is_file() and not a.force:
            say(f"[score {name}] exists, skipped")
            return
        cmd = [PY, "-m", "eval", "--input", folder, "--out", csvp, "--labels", Path(folder) / "labels.csv"]
        if calibration:
            cmd += ["--calibration", calibration]
        run(cmd, f"score {name}", env)

    score("asv_dev", sub / "dev")
    if not cal.is_file() or a.force:
        run([PY, "-m", "eval.fit_threshold", "--preds", out / "asv_dev.csv", "--far", a.far, "--out", cal,
             "--calibrated-on",
             f"ASVspoof2019 LA dev subset ({a.n_dev} real + {a.n_dev} fake, clean+opus+mp3, seed 1234), {datetime.now():%Y-%m-%d}"],
            "5 fit threshold (dev only)", env)
    else:
        say("[fit] calibration file exists, skipped")
    score("asv_eval", sub / "eval", cal)

    # length sweep: same clean dev clips, first N seconds only
    lens = [1, 2, 4]
    lab_rows = [l.split(",") for l in (sub / "dev" / "labels.csv").read_text(encoding="utf-8").splitlines()[1:]]
    clean = [r for r in lab_rows if r[3] == "clean"]
    for n in lens:
        d = sub / "dev_len" / f"{n}s"
        if (d / "labels.csv").is_file() and not a.force:
            continue
        (d / "real").mkdir(parents=True, exist_ok=True)
        (d / "fake").mkdir(parents=True, exist_ok=True)
        keep = []
        for rel, lab, ds, codec, lang in clean:
            r = subprocess.run(["ffmpeg", "-nostdin", "-y", "-loglevel", "error", "-i", str(sub / "dev" / rel), "-t", str(n),
                                str(d / rel)], capture_output=True)
            if r.returncode == 0:
                keep.append([rel, lab, ds, f"clip_{n}s", lang])
        (d / "labels.csv").write_text("file,label,dataset,codec,language\n" + "\n".join(",".join(x) for x in keep) + "\n", encoding="utf-8")
        say(f"[length {n}s] wrote {len(keep)} trimmed clips")
        score(f"asv_len_{n}s", d, cal)

    runs = [("dev", out / "asv_dev.csv"), ("eval", out / "asv_eval.csv")] + [(f"dev_first_{n}s", out / f"asv_len_{n}s.csv") for n in lens]
    cmdline = f"python scripts/b_run_all.py --zip LA.zip --n-dev {a.n_dev} --n-eval {a.n_eval} --far {a.far}"
    run([PY, "scripts/make_results_rows.py", "--command", cmdline, "--commit", git_hash(),
         "--out", out / "B_RESULTS_ROWS_ASVSPOOF.md"] + [x for n, p in runs if p.is_file() for x in ("--run", f"{n}:{p}")], "7 results rows")

    # small, committable copy of the results (no audio, local paths removed)
    import csv
    pub = ROOT / "results" / "asvspoof"
    pub.mkdir(parents=True, exist_ok=True)
    for p in sorted(out.glob("asv_*.csv")):
        with open(p, newline="", encoding="utf-8") as f:
            rd = csv.DictReader(f)
            keep = [c for c in rd.fieldnames if c != "path"]
            rows = [{c: r[c] for c in keep} for r in rd]
        with open(pub / p.name, "w", newline="", encoding="utf-8") as f:
            w = csv.DictWriter(f, fieldnames=keep)
            w.writeheader()
            w.writerows(rows)
    for p in list(out.glob("asv_*.summary.json")) + [out / "B_RESULTS_ROWS_ASVSPOOF.md", cal, out / "b_run_all.log"]:
        if p.is_file():
            shutil.copy(p, pub / p.name)
    say(f"[results] committable copy in {pub} (CSVs without local paths)")

    # bundle for Claude C
    notice = ("Contains information from ASVspoof 2019 (https://doi.org/10.7488/ds/2555), made available under the ODC Attribution License "
              "(https://opendatacommons.org/licenses/by/1.0/). Audio is derived from VCTK; its licence was NOT verified by Claude B. "
              "Internal team use. Do not commit this audio to the repo or publish it without the notice.\n")
    (out / "NOTICE_ASVSPOOF.txt").write_text(notice, encoding="utf-8")
    bundle = out / "veriq_B_results_bundle.zip"
    manifest = {"made": datetime.now().isoformat(timespec="seconds"), "commit": git_hash(), "command": cmdline, "files": {}}
    with zipfile.ZipFile(bundle, "w", zipfile.ZIP_DEFLATED) as z:
        for base in (sub, out):
            for p in sorted(base.rglob("*")):
                if p.is_file() and p != bundle and p.suffix != ".zip" and ".tmp" not in p.parts:
                    arc = p.relative_to(ROOT).as_posix()
                    z.write(p, arc)
                    manifest["files"][arc] = sha(p)
        z.writestr("MANIFEST.json", json.dumps(manifest, indent=2))
    say(f"[8 bundle] PASS {bundle} ({bundle.stat().st_size/1e6:.1f} MB, {len(manifest['files'])} files)")
    say("DONE. Send out\\veriq_B_results_bundle.zip and out\\b_run_all.log to Claude B / Claude C.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
