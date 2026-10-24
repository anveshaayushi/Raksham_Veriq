"""Codec round-trips (Opus / AMR-NB / MP3) via ffmpeg, to simulate WhatsApp-style compression.

Plain words: voice notes are compressed. A detector that only works on clean audio is useless,
so we make compressed copies of test clips and measure on those too.
Which encoders exist depends on your ffmpeg build; `available_codecs()` checks, never assumes.
Only use this on audio you are allowed to use (synthetic, public, or consented).

    python -m voice.augment --input clips/ --out clips_aug/ --codecs opus,mp3
"""
from __future__ import annotations

import argparse
import subprocess
import tempfile
from pathlib import Path
from typing import Dict, List

_ENC: Dict[str, dict] = {
    "opus": {"lib": "libopus", "ext": ".ogg", "args": ["-b:a", "16k", "-application", "voip"], "sr": 16000},
    "mp3": {"lib": "libmp3lame", "ext": ".mp3", "args": ["-b:a", "32k"], "sr": 16000},
    "amrnb": {"lib": "libopencore_amrnb", "ext": ".amr", "args": ["-b:a", "12.2k"], "sr": 8000},
}


def available_codecs() -> List[str]:
    try:
        out = subprocess.run(["ffmpeg", "-hide_banner", "-encoders"], capture_output=True, timeout=20).stdout.decode(errors="replace")
    except (OSError, subprocess.TimeoutExpired):
        return []
    return [k for k, v in _ENC.items() if v["lib"] in out]


def roundtrip(src: Path, dst_wav: Path, codec: str, timeout_s: float = 60.0) -> None:
    """Encode src with the codec, decode back to 16 kHz mono wav at dst_wav. Raises on failure."""
    spec = _ENC[codec]
    with tempfile.TemporaryDirectory() as td:
        mid = Path(td) / f"mid{spec['ext']}"
        subprocess.run(
            ["ffmpeg", "-nostdin", "-y", "-loglevel", "error", "-i", f"file:{src}", "-ac", "1",
             "-ar", str(spec["sr"]), "-c:a", spec["lib"], *spec["args"], str(mid)],
            check=True, capture_output=True, timeout=timeout_s)
        subprocess.run(
            ["ffmpeg", "-nostdin", "-y", "-loglevel", "error", "-i", str(mid), "-ac", "1",
             "-ar", "16000", str(dst_wav)],
            check=True, capture_output=True, timeout=timeout_s)


def main(argv=None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--input", required=True)
    ap.add_argument("--out", required=True)
    ap.add_argument("--codecs", default="opus,mp3")
    a = ap.parse_args(argv)
    have = available_codecs()
    want = [c for c in a.codecs.split(",") if c]
    missing = [c for c in want if c not in have]
    if missing:
        print(f"encoder not available in this ffmpeg build: {missing}; available: {have}")
    out = Path(a.out)
    n = 0
    for f in sorted(Path(a.input).rglob("*")):
        if not f.is_file() or f.suffix.lower() not in {".wav", ".flac", ".mp3", ".ogg", ".opus", ".m4a"}:
            continue
        for c in [c for c in want if c in have]:
            dst = out / c / f.relative_to(a.input).with_suffix(".wav")
            dst.parent.mkdir(parents=True, exist_ok=True)
            try:
                roundtrip(f, dst, c)
                n += 1
            except Exception as e:
                print(f"skip {f} [{c}]: {type(e).__name__}")
    print(f"wrote {n} compressed copies to {out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
