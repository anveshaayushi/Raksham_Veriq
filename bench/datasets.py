"""Load-only checks for the blind datasets (Prompt 2, message 1 part A). NOTHING IS SCORED HERE.

Rule: fix the loaders, never the data. Each loader returns (items, problems): problems lists malformed rows so they
can be regenerated in the dataset chat. Expected sizes come from the dataset brief and are checked, not assumed.

  data/blind_ai/        AI-generated blind chats: labels.csv (file,label,claimed_firm,bank_app_names,...) joined with
                        labels_extended.json by file; expected 80 chats, 40 scam / 40 genuine
  data/names_blind/pairs.csv      name pairs; expected 200 rows, relation classes 70/70/30/30
  data/extract_blind/cases.jsonl  extraction cases; expected 100, 60 with something to extract / 40 without
  data/voice_scripts/             voice scripts (text only); expected 60, 30 real / 30 fake
"""
from __future__ import annotations

import csv
import json
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def parse_bank_app_names(s: str) -> tuple[dict, list[str]]:
    """'identifier=NAME; identifier2=NAME2' -> {identifier_normalised: NAME}; returns problems for bad parts."""
    out, bad = {}, []
    for part in (s or "").split(";"):
        if not part.strip():
            continue
        if "=" not in part:
            bad.append(part.strip())
            continue
        k, v = part.split("=", 1)
        k = k.strip().lower().replace(" ", "")
        if not k or not v.strip():
            bad.append(part.strip())
        else:
            out[k] = v.strip()
    return out, bad


def _rel(p: Path) -> str:
    try:
        return p.resolve().relative_to(ROOT).as_posix()
    except ValueError:
        return str(p)


def _csv(path: Path) -> list[dict]:
    with open(path, newline="", encoding="utf-8-sig") as f:
        return list(csv.DictReader(f))


def load_blind_ai(root: Path = ROOT / "data" / "blind_ai") -> tuple[list[dict], list[str]]:
    problems: list[str] = []
    if not (root / "labels.csv").is_file():
        return [], [f"missing {_rel(root / 'labels.csv')}"]
    rows = _csv(root / "labels.csv")
    ext = {}
    if (root / "labels_extended.json").is_file():
        raw = json.loads((root / "labels_extended.json").read_text(encoding="utf-8"))
        recs = raw if isinstance(raw, list) else raw.get("chats", raw.get("items", list(raw.values()) if isinstance(raw, dict) else []))
        for r in recs:
            if isinstance(r, dict) and r.get("file"):
                ext[r["file"]] = r
    else:
        problems.append("labels_extended.json missing (join skipped)")
    items = []
    for i, r in enumerate(rows, 2):
        f = (r.get("file") or "").strip()
        lab = (r.get("label") or "").strip().lower()
        names, bad = parse_bank_app_names(r.get("bank_app_names", ""))
        if not f or not (root / f).is_file():
            problems.append(f"labels.csv line {i}: file {f!r} not found")
        if lab not in ("scam", "genuine"):
            problems.append(f"labels.csv line {i}: label {lab!r} is not scam/genuine")
        if bad:
            problems.append(f"labels.csv line {i}: bank_app_names parts without 'identifier=NAME': {bad}")
        if f and ext and f not in ext:
            problems.append(f"labels.csv line {i}: {f} has no entry in labels_extended.json")
        items.append({**r, "file": f, "label": lab, "bank_app_names_parsed": names, "extended": ext.get(f, {})})
    c = Counter(it["label"] for it in items)
    if len(items) != 80 or c.get("scam") != 40 or c.get("genuine") != 40:
        problems.append(f"expected 80 chats (40 scam / 40 genuine), found {len(items)} {dict(c)}")
    extra = sorted(set(ext) - {it["file"] for it in items})
    if extra:
        problems.append(f"labels_extended.json has {len(extra)} files not in labels.csv: {extra[:5]}")
    return items, problems


def load_names_blind(path: Path = ROOT / "data" / "names_blind" / "pairs.csv") -> tuple[list[dict], list[str]]:
    if not path.is_file():
        return [], [f"missing {_rel(path)}"]
    rows = _csv(path)
    problems = []
    rel_col = next((c for c in ("relation", "name_relation", "label") if rows and c in rows[0]), None)
    if rel_col is None:
        return rows, [f"no relation column; columns are {list(rows[0]) if rows else []}"]
    for i, r in enumerate(rows, 2):
        if not (r.get("claimed_firm") or r.get("claimed")) or not (r.get("shown_name") or r.get("observed") or r.get("bank_app_name")):
            problems.append(f"line {i}: claimed or shown name missing")
    c = Counter(r[rel_col] for r in rows)
    if len(rows) != 200 or sorted(c.values()) != [30, 30, 70, 70]:
        problems.append(f"expected 200 pairs split 70/70/30/30, found {len(rows)} {dict(c)}")
    return rows, problems


def load_extract_blind(path: Path = ROOT / "data" / "extract_blind" / "cases.jsonl") -> tuple[list[dict], list[str]]:
    if not path.is_file():
        return [], [f"missing {_rel(path)}"]
    items, problems = [], []
    for i, line in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
        if not line.strip():
            continue
        try:
            d = json.loads(line)
        except json.JSONDecodeError as e:
            problems.append(f"line {i}: not JSON ({e.msg})")
            continue
        if not isinstance(d, dict) or not any(k in d for k in ("text", "chat", "message")):
            problems.append(f"line {i}: no text/chat/message field")
        items.append(d)
    neg = sum(1 for d in items if d.get("should_not_extract") or d.get("expected") in ([], {}, None) and "should_not_extract" in d)
    if len(items) != 100 or neg != 40:
        problems.append(f"expected 100 cases (60 to extract / 40 should_not_extract), found {len(items)} ({neg} negative)")
    return items, problems


def load_voice_scripts(root: Path = ROOT / "data" / "voice_scripts") -> tuple[list[dict], list[str]]:
    if not root.is_dir():
        return [], [f"missing {_rel(root)}"]
    lab = next((p for p in (root / "labels.csv", root / "scripts.csv") if p.is_file()), None)
    if lab is None:
        files = sorted(p.name for p in root.iterdir() if p.is_file())
        return [{"file": f} for f in files], [f"no labels.csv/scripts.csv in {root}; {len(files)} files"]
    rows = _csv(lab)
    c = Counter((r.get("label") or "").lower() for r in rows)
    problems = [] if (len(rows) == 60 and c.get("real") == 30 and c.get("fake") == 30) else \
        [f"expected 60 scripts (30 real / 30 fake), found {len(rows)} {dict(c)}"]
    return rows, problems


def check_all() -> dict:
    out = {}
    for name, fn in (("blind_ai", load_blind_ai), ("names_blind", load_names_blind),
                     ("extract_blind", load_extract_blind), ("voice_scripts", load_voice_scripts)):
        items, problems = fn()
        out[name] = {"loaded": len(items), "problems": problems,
                     "status": "not provided" if items == [] and problems and problems[0].startswith("missing") else
                               ("ok" if not problems else "malformed")}
    return out


if __name__ == "__main__":
    r = check_all()
    for k, v in r.items():
        print(f"{k:14s} {v['status']:13s} loaded={v['loaded']}")
        for p in v["problems"][:20]:
            print("   -", p)
