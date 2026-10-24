#!/usr/bin/env python3
"""Build a small, labelled, seeded subset of ASVspoof 2019 LA for veriq-eval.

STATUS: drafted by Claude B; tested only on a synthetic mock of the folder layout, NOT on the real
dataset. The layout and protocol format below are recalled from memory and from the dataset README
(README.txt lists ASVspoof2019_LA_cm_protocols, _dev, _eval, _train). If the real files differ, the
script says what it could not find; send me that message.

Why a subset: the full set is huge and CPU scoring is slow. A seeded balanced sample is enough for a
first honest number. State the sample size in RESULTS.md.

Use of splits (brief section 7 / 11): `dev` -> fit the threshold. `eval` -> report results (it contains
attacks that are not in train/dev). NEVER fit the threshold on `eval`.

    python scripts/make_asvspoof_subset.py --root data/raw/asvspoof2019_la --split dev  --n-real 100 --n-fake 100 --out data/subsets/dev
    python scripts/make_asvspoof_subset.py --root data/raw/asvspoof2019_la --split eval --n-real 100 --n-fake 100 --out data/subsets/eval

Add --codecs opus,mp3 to also write compressed copies (simulating chat-app voice notes).
Output: <out>/real/*.wav, <out>/fake/*.wav and <out>/labels.csv (file,label,dataset,codec,language).
"""
from __future__ import annotations

import argparse
import csv
import random
import subprocess
import sys
from pathlib import Path

REAL = {"bonafide", "bona-fide", "genuine"}
FAKE = {"spoof"}
HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent))


def find_protocol(root: Path, split: str) -> Path:
    hits = sorted(root.rglob(f"ASVspoof2019.LA.cm.{split}*.txt"))
    if not hits:
        raise SystemExit(f"no protocol file like ASVspoof2019.LA.cm.{split}*.txt under {root}. "
                         f"Did you unzip LA.zip into that folder? Run: dir /s /b {root}\\*cm*")
    return hits[0]


def find_audio_dir(root: Path, split: str) -> Path:
    hits = [p for p in root.rglob(f"ASVspoof2019_LA_{split}") if p.is_dir()]
    if not hits:
        raise SystemExit(f"no folder named ASVspoof2019_LA_{split} under {root}")
    d = hits[0] / "flac"
    return d if d.is_dir() else hits[0]


def read_protocol(path: Path):
    """Each line: SPEAKER FILE - ATTACK LABEL. Be tolerant: file = column 2, label = last column."""
    rows = []
    for line in path.read_text(encoding="utf-8", errors="replace").splitlines():
        parts = line.split()
        if len(parts) < 3:
            continue
        label = parts[-1].lower()
        if label in REAL:
            rows.append((parts[1], "real"))
        elif label in FAKE:
            rows.append((parts[1], "fake"))
    return rows


class ZipSource:
    """Read the protocol and single flac files straight out of LA.zip: no need to extract 7 GB."""

    def __init__(self, zip_path: Path):
        import zipfile
        self.z = zipfile.ZipFile(zip_path)
        self.names = {n for n in self.z.namelist()}

    def protocol_lines(self, split: str) -> list:
        want = f"ASVspoof2019.LA.cm.{split}."
        hits = sorted(n for n in self.names if n.rsplit("/", 1)[-1].startswith(want) and n.endswith(".txt"))
        if not hits:
            raise SystemExit(f"no protocol like {want}*.txt inside the zip")
        return self.z.read(hits[0]).decode("utf-8", errors="replace").splitlines(), hits[0]

    def flac_member(self, split: str, name: str):
        for pat in (f"LA/ASVspoof2019_LA_{split}/flac/{name}.flac",):
            if pat in self.names:
                return pat
        hits = [n for n in self.names if n.endswith(f"/ASVspoof2019_LA_{split}/flac/{name}.flac")]
        return hits[0] if hits else None

    def extract_flac(self, member: str, dst: Path) -> None:
        dst.parent.mkdir(parents=True, exist_ok=True)
        with self.z.open(member) as f, open(dst, "wb") as o:
            o.write(f.read())


def parse_protocol_lines(lines) -> list:
    rows = []
    for line in lines:
        parts = line.split()
        if len(parts) < 3:
            continue
        label = parts[-1].lower()
        if label in REAL:
            rows.append((parts[1], "real"))
        elif label in FAKE:
            rows.append((parts[1], "fake"))
    return rows


def to_wav(src: Path, dst: Path) -> None:
    dst.parent.mkdir(parents=True, exist_ok=True)
    subprocess.run(["ffmpeg", "-nostdin", "-y", "-loglevel", "error", "-i", str(src),
                    "-ac", "1", "-ar", "16000", str(dst)], check=True, capture_output=True, timeout=60)


def main(argv=None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--root", default=None, help="folder with the extracted LA dataset")
    ap.add_argument("--zip", default=None, help="OR path to LA.zip: read clips directly, nothing is extracted")
    ap.add_argument("--split", choices=["train", "dev", "eval"], required=True)
    ap.add_argument("--n-real", type=int, default=100)
    ap.add_argument("--n-fake", type=int, default=100)
    ap.add_argument("--seed", type=int, default=1234)
    ap.add_argument("--codecs", default="", help="comma list, e.g. opus,mp3")
    ap.add_argument("--out", required=True)
    a = ap.parse_args(argv)

    out = Path(a.out)
    zsrc = None
    if bool(a.root) == bool(a.zip):
        print("give exactly one of --root (extracted folder) or --zip (LA.zip)", file=sys.stderr)
        return 2
    if a.zip:
        zsrc = ZipSource(Path(a.zip))
        lines, proto_name = zsrc.protocol_lines(a.split)
        rows = parse_protocol_lines(lines)
        audio = None
        print(f"protocol {proto_name}: reading from zip")
    else:
        root = Path(a.root)
        proto = find_protocol(root, a.split)
        audio = find_audio_dir(root, a.split)
        rows = read_protocol(proto)
    reals = sorted(f for f, l in rows if l == "real")
    fakes = sorted(f for f, l in rows if l == "fake")
    print(f"{len(reals)} real, {len(fakes)} fake in the {a.split} protocol; audio from {'zip' if zsrc else audio}")
    rng = random.Random(a.seed)
    pick = {"real": rng.sample(reals, min(a.n_real, len(reals))),
            "fake": rng.sample(fakes, min(a.n_fake, len(fakes)))}

    codecs = [c for c in a.codecs.split(",") if c]
    if codecs:
        from voice.augment import available_codecs, roundtrip
        have = available_codecs()
        bad = [c for c in codecs if c not in have]
        if bad:
            print(f"warning: encoders not in this ffmpeg build, skipped: {bad}")
        codecs = [c for c in codecs if c in have]

    labels = []
    skipped = 0
    for lab, names in pick.items():
        for n in names:
            rel = f"{lab}/{n}.wav"
            try:
                if zsrc:
                    member = zsrc.flac_member(a.split, n)
                    if member is None:
                        skipped += 1
                        continue
                    tmp = out / ".tmp" / f"{n}.flac"
                    zsrc.extract_flac(member, tmp)
                    src = tmp
                else:
                    src = audio / f"{n}.flac"
                    if not src.is_file():
                        skipped += 1
                        continue
                to_wav(src, out / rel)
                if zsrc:
                    src.unlink(missing_ok=True)
                labels.append((rel, lab, "asvspoof2019_la_" + a.split, "clean", "en"))
                for c in codecs:
                    relc = f"{lab}/{n}__{c}.wav"
                    roundtrip(out / rel, out / relc, c)
                    labels.append((relc, lab, "asvspoof2019_la_" + a.split, c, "en"))
            except Exception as e:
                skipped += 1
                print(f"skip {n}: {type(e).__name__}")
    out.mkdir(parents=True, exist_ok=True)
    try:
        (out / ".tmp").rmdir()
    except OSError:
        pass
    with open(out / "labels.csv", "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(["file", "label", "dataset", "codec", "language"])
        w.writerows(labels)
    print(f"wrote {len(labels)} labelled files to {out} (skipped {skipped}); seed={a.seed}")
    return 0 if labels else 1


if __name__ == "__main__":
    raise SystemExit(main())
