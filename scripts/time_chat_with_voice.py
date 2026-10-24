#!/usr/bin/env python3
"""Deck target "time per chat with voice notes <= 60 s": time one full check of a chat with voice notes.

    python scripts/time_chat_with_voice.py [--notes 3] [--out results/timing_chat_with_voice.json]

Uses scenario A's chat plus N voice notes (the repo's demo clips), through the same build_case() the app calls:
parse, extract, every voice note through ffmpeg + quality gate + AASIST (if AASIST is installed: set
VERIQ_AASIST_REPO), rules, evidence. Records whether the model actually ran, so a fast "no model" time is never
reported as the real one.
"""
from __future__ import annotations

import argparse
import json
import os
import platform
import sys
import time
from datetime import datetime, timedelta, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))


def main(argv=None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--notes", type=int, default=3)
    ap.add_argument("--out", default=str(ROOT / "results" / "timing_chat_with_voice.json"))
    a = ap.parse_args(argv)
    from app.case import build_case, demo_inputs, load_demo
    from voice import service
    di = demo_inputs(load_demo("A"))
    clips = [ROOT / "app" / "demo_media" / n for n in ("demo_voice_synthetic_tts.wav", "demo_voice_real_human.wav")]
    chat = di["chat_text"].rstrip("\n")
    audio = {}
    for i in range(a.notes):
        name = f"PTT-T{i}.wav"
        chat += f"\n18/10/2026, 9:{10 + i:02d} am - Advisor: {name} (file attached)"
        audio[name] = clips[i % 2].read_bytes()
    t0 = time.perf_counter()
    c = build_case(case_id="timing", chat_text=chat + "\n", claimed_firm=di["claimed_firm"], checks={},
                   transcripts=di["transcripts"], audio=audio)
    secs = time.perf_counter() - t0
    b = service._load_backend()
    model = getattr(b.get("detector"), "model_version", None)
    res = {"seconds": round(secs, 2), "messages": len(c.extraction.messages), "voice_notes": a.notes,
           "model_ran": model is not None, "model_version": model or f"none ({b.get('error')})",
           "voice_states": [v.state for v in c.voice],
           "where": f"{platform.system()} {platform.machine()}, {os.cpu_count()} CPUs, Python {platform.python_version()}",
           "run_at_ist": datetime.now(timezone(timedelta(hours=5, minutes=30))).strftime("%Y-%m-%d %H:%M IST")}
    Path(a.out).parent.mkdir(parents=True, exist_ok=True)
    Path(a.out).write_text(json.dumps(res, indent=1), encoding="utf-8")
    print(json.dumps(res, indent=1))
    return 0 if res["model_ran"] else 3


if __name__ == "__main__":
    raise SystemExit(main())
