#!/usr/bin/env python3
"""Offline bundle (Q4 item a): everything needed to install VERIQ on a computer with no internet.

    python scripts/make_offline_bundle.py [--voice] [--platform win_amd64 --python 3.11] [--out veriq_offline.zip]

Downloads the pinned wheels (requirements.txt; with --voice also the voice extras) into wheelhouse/ for the TARGET
computer's platform and Python version, then zips the repo (without .git, caches, data/raw) plus the wheelhouse.
On the offline computer:  unzip, then  install_offline.ps1  (Windows) or  bash install_offline.sh.
ffmpeg is not a pip package: copy its installer separately (Windows: the Gyan.FFmpeg zip) if voice notes are needed.
"""
from __future__ import annotations

import argparse
import subprocess
import sys
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SKIP_DIRS = {".git", ".venv", "__pycache__", ".pytest_cache", "external", "wheelhouse", "secrets"}
SKIP_PREFIX = ("data/raw", "data/subsets", "results/regenerated")


def main(argv=None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--voice", action="store_true")
    ap.add_argument("--platform", action="append", default=[],
                    help="repeatable; e.g. win_amd64, or manylinux_2_28_x86_64 plus manylinux_2_17_x86_64")
    ap.add_argument("--python", default=None, help="target Python version, e.g. 3.11")
    ap.add_argument("--out", default=str(ROOT.parent / "veriq_offline.zip"))
    a = ap.parse_args(argv)
    wh = ROOT / "wheelhouse"
    wh.mkdir(exist_ok=True)
    reqs = ["-r", str(ROOT / "requirements.txt")]
    cmd = [sys.executable, "-m", "pip", "download", "-d", str(wh), "--only-binary=:all:", *reqs]
    for plat in a.platform:
        cmd += ["--platform", plat]
    if a.python:
        cmd += ["--python-version", a.python]
    print(" ".join(cmd))
    if subprocess.run(cmd).returncode != 0:
        print("pip download failed (internet needed on THIS computer)")
        return 1
    if a.voice:
        vcmd = cmd[:cmd.index("-r")] + ["torch", "torchaudio", "soundfile", "scikit-learn"] + cmd[cmd.index("-r") + 2:]
        if subprocess.run(vcmd).returncode != 0:
            print("voice extras download failed; the bundle will work without the voice model")
    n = 0
    with zipfile.ZipFile(a.out, "w", zipfile.ZIP_DEFLATED) as z:
        for p in sorted(ROOT.rglob("*")):
            if p.is_dir():
                continue
            rel = p.relative_to(ROOT).as_posix()
            parts = p.relative_to(ROOT).parts
            if not rel.startswith("wheelhouse/") and (any(x in SKIP_DIRS for x in parts) or rel.startswith(SKIP_PREFIX)):
                continue
            z.write(p, "veriq/" + rel)
            n += 1
    print(f"wrote {a.out}: {n} files ({len(list(wh.iterdir()))} wheels)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
