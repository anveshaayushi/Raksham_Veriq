"""Blind chat set (Q2 item c): chats written by teammates who did NOT read the rules, run ONCE.

    python -m bench.blind.run                 -> results/q2/blind.json (refuses to run twice unless --force)

Input: data/blind/*.txt (WhatsApp "Export chat > Without media" files) and data/blind/labels.csv with columns
    file,label,claimed_firm,bank_app_names
label = scam | genuine; bank_app_names = "<upi or account>=<NAME THE BANK APP SHOWS>; ..." (may be empty).
See data/blind/README.md for the instructions given to the writers.

Counts per chat (case result = worst payee):
  scam    -> "warned" if the answer is anything except "No major issue"; "cleared" (a miss) if "No major issue";
             "no answer" if no payee or no dated message was found
  genuine -> "false alarm" if LINKED / NAME_DISCREPANCY / REGISTRATION_CONFLICT; "review" if HUMAN_REVIEW or
             INCONCLUSIVE; "clear" if "No major issue"
This is the only chat result in the project not written by the people who wrote the rules. Do not tune on it.
"""
from __future__ import annotations

import argparse
import csv
import json
import math
from collections import Counter
from datetime import date, datetime, timedelta, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
ACCUSING = {"LINKED", "NAME_DISCREPANCY", "REGISTRATION_CONFLICT"}


def wilson(k, n, z=1.96):
    if n == 0:
        return None
    p = k / n
    d = 1 + z * z / n
    c = (p + z * z / (2 * n)) / d
    h = z * math.sqrt(p * (1 - p) / n + z * z / (4 * n * n)) / d
    return [round(max(0.0, c - h), 3), round(min(1.0, c + h), 3)]


def parse_names(s: str) -> dict[str, str]:
    out = {}
    for part in (s or "").split(";"):
        if "=" in part:
            k, v = part.split("=", 1)
            k = k.strip().lower().replace(" ", "")
            if k and v.strip():
                out[k] = v.strip()
    return out


def run(folder: Path) -> dict:
    from app.case import UserCheck, build_case
    from app.intake import decode_text
    rows = list(csv.DictReader(open(folder / "labels.csv", encoding="utf-8-sig")))
    per, outcome = [], Counter()
    for r in rows:
        f = folder / r["file"].strip()
        if not f.is_file():
            per.append({"file": r["file"], "label": r["label"], "error": "file not found"})
            outcome[(r["label"], "missing file")] += 1
            continue
        text = decode_text(f.read_bytes())
        names = parse_names(r.get("bank_app_names", ""))
        checks = {k: UserCheck(v, "Bank app (beneficiary name)", date(2026, 10, 25)) for k, v in names.items()}
        c = build_case(case_id=f.stem, chat_text=text, claimed_firm=r.get("claimed_firm", "").strip(), checks=checks)
        res = c.case_result()
        found = [p.value_norm for p in c.payees]
        lab = r["label"].strip().lower()
        if res is None:
            o = "no answer"
        elif lab == "scam":
            o = "cleared (miss)" if res == "NO_MAJOR_ISSUE" else "warned"
        else:
            o = "false alarm" if res in ACCUSING else ("clear" if res == "NO_MAJOR_ISSUE" else "review")
        outcome[(lab, o)] += 1
        per.append({"file": r["file"], "label": lab, "result": res, "outcome": o, "payees_found": found,
                    "names_given_for": sorted(names), "names_not_matched_to_a_found_payee": sorted(set(names) - set(found)),
                    "warnings": c.extraction.warnings[:3]})
    n_scam = sum(v for (l, _), v in outcome.items() if l == "scam")
    n_gen = sum(v for (l, _), v in outcome.items() if l == "genuine")
    warned, missed = outcome[("scam", "warned")], outcome[("scam", "cleared (miss)")]
    fa = outcome[("genuine", "false alarm")]
    return {"chats": len(rows), "scam": n_scam, "genuine": n_gen,
            "scam_warned": {"count": warned, "of": n_scam, "wilson95": wilson(warned, n_scam)},
            "scam_cleared_miss": {"count": missed, "of": n_scam, "wilson95": wilson(missed, n_scam)},
            "genuine_false_alarm": {"count": fa, "of": n_gen, "wilson95": wilson(fa, n_gen)},
            "outcomes": {f"{l}: {o}": v for (l, o), v in sorted(outcome.items())}, "per_chat": per,
            "limit": "small set written by teammates; fictional names; run once, not tuned on"}


def main(argv=None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--data", default=str(ROOT / "data" / "blind"))
    ap.add_argument("--out", default=str(ROOT / "results" / "q2" / "blind.json"))
    ap.add_argument("--force", action="store_true", help="run again (the earlier result is kept as .previous.json)")
    a = ap.parse_args(argv)
    folder, out = Path(a.data), Path(a.out)
    if not (folder / "labels.csv").is_file():
        print(f"no {folder / 'labels.csv'}: blind set not provided yet (see data/blind/README.md)")
        return 2
    if out.is_file() and not a.force:
        print(f"{out} exists: the blind set was already run once. Use --force only if the chats changed.")
        return 3
    if out.is_file():
        out.rename(out.with_suffix(".previous.json"))
    r = run(folder)
    r["run_at_ist"] = datetime.now(timezone(timedelta(hours=5, minutes=30))).strftime("%Y-%m-%d %H:%M IST")
    out.parent.mkdir(parents=True, exist_ok=True)
    with open(out, "w", encoding="utf-8", newline="\n") as f:
        f.write(json.dumps(r, indent=1, ensure_ascii=False))
    print(f"{r['chats']} chats: scams warned {r['scam_warned']['count']}/{r['scam']} {r['scam_warned']['wilson95']}, "
          f"scams cleared {r['scam_cleared_miss']['count']}, genuine false alarms {r['genuine_false_alarm']['count']}/"
          f"{r['genuine']} {r['genuine_false_alarm']['wilson95']}")
    for k, v in r["outcomes"].items():
        print(f"  {k}: {v}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
