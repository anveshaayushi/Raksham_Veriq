#!/usr/bin/env python3
"""Speech-to-text re-check with the REAL faster-whisper model (run on the team laptop; downloads the model once).

    pip install faster-whisper
    python scripts/stt_check.py                       # VERIQ_WHISPER_MODEL=small by default; "medium" is better for Hindi

Clips: every file in data/hinglish/real and data/hinglish/fake (12 known sentences, so the text can be compared),
the first 3 ASVspoof eval real clips in data/subsets/eval/real (no reference text), and the demo human clip.
Writes results/asvspoof/B_STT_RECHECK.json and .md: how many clips produced text, every transcript next to the
sentence that was read, and a ROUGH similarity (0-1, best of the Devanagari and the Roman form, character based).
This is not a word error rate and not an accuracy benchmark: few clips, few speakers.
"""
from __future__ import annotations

import json
import re
import statistics
import sys
import time
from datetime import datetime, timedelta, timezone
from difflib import SequenceMatcher
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "scripts"))
AUDIO = {".wav", ".opus", ".ogg", ".m4a", ".mp3", ".flac", ".aac", ".amr", ".webm", ".mp4"}


def norm(s: str) -> str:
    return " ".join(re.sub(r"[^\w\s]", " ", (s or "").lower()).split())


def similarity(text: str, idx: int | None, sentences) -> float | None:
    if idx is None or not text or not (1 <= idx <= len(sentences)):
        return None
    dev, rom = sentences[idx - 1][0], sentences[idx - 1][1]
    t = norm(text)
    return round(max(SequenceMatcher(None, t, norm(dev)).ratio(), SequenceMatcher(None, t, norm(rom)).ratio()), 3)


def clips(root: Path) -> list[tuple[str, Path]]:
    out = []
    for group in ("real", "fake"):
        out += [(f"hinglish_{group}", p) for p in sorted((root / "data" / "hinglish" / group).glob("*")) if p.suffix.lower() in AUDIO]
    out += [("asvspoof_eval_real", p) for p in sorted((root / "data" / "subsets" / "eval" / "real").glob("*"))[:3]
            if p.suffix.lower() in AUDIO]
    demo = root / "app" / "demo_media" / "demo_voice_real_human.wav"
    if demo.is_file():
        out.append(("demo_human", demo))
    return out


def run(root: Path = ROOT) -> dict:
    from hinglish_build import SENTENCES
    from voice.transcribe import transcribe
    rows = []
    for group, p in clips(root):
        m = re.search(r"_(\d{1,2})(?:\D|$)", p.stem)
        idx = int(m.group(1)) if (m and group.startswith("hinglish")) else None
        t0 = time.time()
        tr = transcribe(p.name, p.read_bytes(), p.name)
        rows.append({"group": group, "clip": p.relative_to(root).as_posix(), "sentence": idx, "text": tr.text,
                     "language": tr.language, "error": tr.error, "model": tr.model,
                     "seconds": round(time.time() - t0, 2), "similarity": similarity(tr.text, idx, SENTENCES)})
    by = {}
    for g in sorted({r["group"] for r in rows}):
        rs = [r for r in rows if r["group"] == g]
        sims = [r["similarity"] for r in rs if r["similarity"] is not None]
        by[g] = {"clips": len(rs), "with_text": sum(bool(r["text"]) for r in rs),
                 "median_similarity": statistics.median(sims) if sims else None,
                 "similarity_at_least_0.5": sum(s >= 0.5 for s in sims) if sims else None}
    return {"command": "python scripts/stt_check.py",
            "run_at_ist": datetime.now(timezone(timedelta(hours=5, minutes=30))).strftime("%Y-%m-%d %H:%M IST"),
            "model": rows[0]["model"] if rows else None, "clips": len(rows),
            "with_text": sum(bool(r["text"]) for r in rows), "by_group": by, "rows": rows,
            "limit": "few clips and speakers; similarity is a rough character match, not a word error rate"}


def markdown(r: dict) -> str:
    L = ["## Speech-to-text re-check (real model, team laptop)", "",
         f"`{r['command']}` · {r['run_at_ist']} · model {r['model']} · **{r['with_text']}/{r['clips']} clips produced text**", "",
         "| Group | Clips | With text | Median similarity to the sentence read | Similarity >= 0.5 |", "|---|---|---|---|---|"]
    L += [f"| {g} | {v['clips']} | {v['with_text']} | {v['median_similarity']} | {v['similarity_at_least_0.5']} |" for g, v in r["by_group"].items()]
    L += ["", "| Clip | Text | Similarity | Error |", "|---|---|---|---|"]
    L += [f"| {x['clip']} | {(x['text'] or '')[:80]} | {x['similarity']} | {x['error'] or ''} |" for x in r["rows"]]
    L += ["", r["limit"]]
    return "\n".join(L) + "\n"


def main() -> int:
    r = run()
    out = ROOT / "results" / "asvspoof"
    out.mkdir(parents=True, exist_ok=True)
    (out / "B_STT_RECHECK.json").write_text(json.dumps(r, indent=1, ensure_ascii=False), encoding="utf-8")
    (out / "B_STT_RECHECK.md").write_text(markdown(r), encoding="utf-8")
    print(markdown(r))
    return 0 if r["with_text"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
