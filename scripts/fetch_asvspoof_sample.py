#!/usr/bin/env python3
"""Fetch a SMALL labelled sample of ASVspoof 2019 LA without downloading the 7 GB LA.zip.

Plain words: a zip file keeps an index at its end. With HTTP range requests we read the index, then pull
only the audio files we choose. Needs `pip install remotezip` and a server that supports range requests.
STATUS: logic unit-tested against a local fake zip; NOT yet run against the real server.

    python scripts/fetch_asvspoof_sample.py --url "<direct LA.zip link>" --out data/raw/asvspoof2019_la_sample --n-per-class 500
    add --dry-run first to see what it would take.

Get the link: on the Edinburgh DataShare page, right-click "LA.zip" > Copy link address.
Output: <out>/dev/{real,fake}/*.flac and <out>/eval/{real,fake}/*.flac, plus labels.csv in each partition
(columns file,label,dataset,codec,language). Samples are class-balanced, so the real/fake ratio is NOT the
natural one; say so when reporting.

Licence: ODC-By (README COPYING section, read 2026-10-23). When you publicly show results, include:
"Contains information from ASVspoof 2019 (https://doi.org/10.7488/ds/2555), made available under the ODC Attribution License
(https://opendatacommons.org/licenses/by/1.0/)". Cite Todisco et al., Interspeech 2019.
"""
from __future__ import annotations

import argparse
import csv
import random
import sys
from pathlib import Path
from typing import List, Tuple

ATTRIBUTION = ("Contains information from ASVspoof 2019 (https://doi.org/10.7488/ds/2555), made available under "
               "the ODC Attribution License (https://opendatacommons.org/licenses/by/1.0/).")


def open_zip(url: str):
    try:
        from remotezip import RemoteZip
    except ImportError:
        sys.exit("missing package: pip install remotezip")
    return RemoteZip(url)


def parse_protocol(text: str) -> List[Tuple[str, str]]:
    """Lines look like: 'LA_0069 LA_D_1047731 - A07 spoof'. Return (file_id, 'bonafide'|'spoof')."""
    rows = []
    for line in text.splitlines():
        p = line.split()
        if len(p) >= 5 and p[-1].lower() in ("bonafide", "spoof"):
            rows.append((p[1], p[-1].lower()))
    return rows


def pick(rows: List[Tuple[str, str]], n_per_class: int, seed: int) -> List[Tuple[str, str]]:
    rng = random.Random(seed)
    out: List[Tuple[str, str]] = []
    for lab in ("bonafide", "spoof"):
        pool = sorted(i for i, l in rows if l == lab)
        rng.shuffle(pool)
        out += [(i, lab) for i in pool[:n_per_class]]
    return out


def fetch(zf, out_root: Path, n_per_class: int, seed: int, dry_run: bool) -> int:
    names = zf.namelist()
    flac = {Path(n).name[:-5]: n for n in names if n.lower().endswith(".flac")}
    total = 0
    for part in ("dev", "eval"):
        proto = [n for n in names if f".cm.{part}." in n.lower() and n.lower().endswith(".txt")]
        if not proto:
            print(f"no {part} protocol file found in the zip; skipping {part}")
            continue
        rows = parse_protocol(zf.read(proto[0]).decode("utf-8", "replace"))
        chosen = [(i, l) for i, l in pick(rows, n_per_class, seed) if i in flac]
        print(f"{part}: protocol rows={len(rows)}, selected={len(chosen)}")
        if dry_run:
            continue
        base = out_root / part
        labels = []
        for fid, lab in chosen:
            sub = "real" if lab == "bonafide" else "fake"
            dst = base / sub / f"{fid}.flac"
            dst.parent.mkdir(parents=True, exist_ok=True)
            if not dst.exists():
                try:
                    with zf.open(flac[fid]) as f:
                        dst.write_bytes(f.read())
                except Exception as e:
                    print(f"  skip {fid}: {type(e).__name__}")
                    continue
            labels.append([f"{sub}/{fid}.flac", sub, f"asvspoof2019_la_{part}", "flac", "en"])
            total += 1
        with open(base / "labels.csv", "w", newline="", encoding="utf-8") as f:
            w = csv.writer(f)
            w.writerow(["file", "label", "dataset", "codec", "language"])
            w.writerows(labels)
    return total


def main(argv=None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--url", required=True)
    ap.add_argument("--out", required=True)
    ap.add_argument("--n-per-class", type=int, default=500)
    ap.add_argument("--seed", type=int, default=1234)
    ap.add_argument("--dry-run", action="store_true")
    a = ap.parse_args(argv)
    try:
        zf = open_zip(a.url)
    except Exception as e:
        print(f"could not open remote zip ({type(e).__name__}: {e}). The server may not support range requests; "
              f"fall back to downloading LA.zip in the browser.")
        return 1
    n = fetch(zf, Path(a.out), a.n_per_class, a.seed, a.dry_run)
    print(f"done: {n} files written" if not a.dry_run else "dry run only, nothing written")
    print(ATTRIBUTION)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
