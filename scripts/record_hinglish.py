#!/usr/bin/env python3
"""Record the 12 Hinglish prompts from the laptop microphone, from the terminal (Windows, ffmpeg dshow). One person at a time.

    ffmpeg -list_devices true -f dshow -i dummy                     (find the microphone name, e.g. "Microphone Array (Realtek...)")
    python scripts\\record_hinglish.py --name anvesha --device "Microphone Array (Realtek(R) Audio)"

For each sentence: it prints it, you press Enter, speak for up to 8 seconds, then it checks the loudness and offers a retry if the clip
is too quiet (silent clips are useless: they have no speech for the detector). Files go to data/hinglish/real/<name>_01.wav ...
The speaker must consent to the clips being used for this test set and shared with the team.
"""
from __future__ import annotations

import argparse
import re
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "scripts"))


def mean_volume_db(path: Path):
    r = subprocess.run(["ffmpeg", "-nostdin", "-i", str(path), "-af", "volumedetect", "-f", "null", "-"], capture_output=True, text=True)
    m = re.search(r"mean_volume:\s*(-?[\d.]+) dB", r.stderr)
    return float(m.group(1)) if m else None


def record(device: str, dst: Path, seconds: float, gain_db: float) -> bool:
    dst.parent.mkdir(parents=True, exist_ok=True)
    cmd = ["ffmpeg", "-nostdin", "-y", "-loglevel", "error", "-f", "dshow", "-i", f"audio={device}", "-t", str(seconds),
           "-af", f"volume={gain_db}dB", "-ac", "1", "-ar", "16000", str(dst)]
    return subprocess.run(cmd).returncode == 0 and dst.is_file()


def main(argv=None) -> int:
    from hinglish_build import SENTENCES
    ap = argparse.ArgumentParser()
    ap.add_argument("--name", required=True, help="your first name, lower case, no spaces")
    ap.add_argument("--device", required=True)
    ap.add_argument("--seconds", type=float, default=8.0)
    ap.add_argument("--gain-db", type=float, default=0.0, help="boost if clips come out too quiet, e.g. 15")
    ap.add_argument("--quiet-below-db", type=float, default=-40.0)
    ap.add_argument("--start", type=int, default=1)
    a = ap.parse_args(argv)
    if not re.fullmatch(r"[a-z0-9]+", a.name):
        print("--name must be lower-case letters/digits only")
        return 2
    print(f"Recording for {a.name}. Consent: by continuing you agree these clips are used for the VERIQ test set and shared with the team.")
    input("Press Enter to agree and start (Ctrl+C to stop): ")
    for i, (dev, rom, _k) in enumerate(SENTENCES, 1):
        if i < a.start:
            continue
        dst = ROOT / "data" / "hinglish" / "real" / f"{a.name}_{i:02d}.wav"
        while True:
            print(f"\n[{i:02d}/12]  {dev}\n        {rom}")
            input(f"Press Enter, then read it aloud ({a.seconds:g} s window): ")
            if not record(a.device, dst, a.seconds, a.gain_db):
                print("recording failed: check --device (run: ffmpeg -list_devices true -f dshow -i dummy)")
                return 1
            v = mean_volume_db(dst)
            print(f"   saved {dst.name}, average loudness {v} dB")
            if v is None or v < a.quiet_below_db:
                if input("   too quiet. Retry? [Y/n] ").strip().lower() != "n":
                    continue
            break
    print(f"\nDone: 12 clips in data\\hinglish\\real\\ for {a.name}.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
