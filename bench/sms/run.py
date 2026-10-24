"""Pressure-cue check on a PUBLIC labelled text dataset: the UCI SMS Spam Collection (Q2 item b).

Plain words: VERIQ's chat cues (urgency, guaranteed returns, fee to withdraw, OTP/PIN request, remote access,
secrecy, ...) are run on 5,574 real SMS messages that other people labelled "ham" (normal) or "spam". We count how
often a cue fires on normal messages (false alarms) and on spam (recall).

IMPORTANT LIMIT: this is NOT Indian UPI investment fraud. The SMS set is mostly UK/Singapore texts from ~2011; spam
there is prize/ringtone marketing, not "pay 18% tax to withdraw". So spam recall here is expected to be LOW and is
reported only to be honest about scope; the useful number is the false-alarm rate on normal messages, especially
for the HARD cues that can push an answer to "Inconclusive".

Download (laptop): the UCI page for "SMS Spam Collection" (dataset 228), file smsspamcollection.zip; unzip so that
data/raw/sms_spam/SMSSpamCollection exists (tab-separated: label<TAB>text). Licence as shown on the UCI page:
record it with `python scripts/datasets.py record ...` (CC BY 4.0 on the current UCI site; verify on the page).

    python -m bench.sms.run --data data/raw/sms_spam/SMSSpamCollection --out results/q2/sms.json
"""
from __future__ import annotations

import argparse
import hashlib
import json
import math
from collections import Counter
from pathlib import Path

from extract import CUE_RX, DEFAULT_CUE_SEVERITY, deobfuscate


def wilson(k: int, n: int, z: float = 1.96):
    if n == 0:
        return None
    p = k / n
    d = 1 + z * z / n
    c = (p + z * z / (2 * n)) / d
    h = z * math.sqrt(p * (1 - p) / n + z * z / (4 * n * n)) / d
    return [round(max(0.0, c - h), 4), round(min(1.0, c + h), 4)]


def cues_in(text: str) -> set[str]:
    d = deobfuscate(text)
    return {t for t, rx in CUE_RX if rx.search(text) or rx.search(d)}


def evaluate(path: Path) -> dict:
    raw = path.read_bytes()
    rows = []
    for line in raw.decode("utf-8", errors="replace").splitlines():
        if "\t" in line:
            lab, text = line.split("\t", 1)
            if lab in ("ham", "spam"):
                rows.append((lab, text))
    by = {"ham": Counter(), "spam": Counter()}
    any_cue = Counter()
    hard_cue = Counter()
    n = Counter(lab for lab, _ in rows)
    ham_examples = []
    for lab, text in rows:
        c = cues_in(text)
        for t in c:
            by[lab][t] += 1
        any_cue[lab] += bool(c)
        hard = {t for t in c if DEFAULT_CUE_SEVERITY.get(t) == "hard"}
        hard_cue[lab] += bool(hard)
        if lab == "ham" and hard and len(ham_examples) < 15:
            ham_examples.append({"text": text[:160], "cues": sorted(hard)})
    return {
        "dataset": "UCI SMS Spam Collection", "file_sha256": hashlib.sha256(raw).hexdigest(), "messages": len(rows),
        "n": dict(n),
        "ham_any_cue": {"count": any_cue["ham"], "of": n["ham"], "rate": round(any_cue["ham"] / n["ham"], 4) if n["ham"] else None,
                        "wilson95": wilson(any_cue["ham"], n["ham"])},
        "ham_hard_cue": {"count": hard_cue["ham"], "of": n["ham"], "rate": round(hard_cue["ham"] / n["ham"], 4) if n["ham"] else None,
                         "wilson95": wilson(hard_cue["ham"], n["ham"])},
        "spam_any_cue": {"count": any_cue["spam"], "of": n["spam"], "rate": round(any_cue["spam"] / n["spam"], 4) if n["spam"] else None,
                         "wilson95": wilson(any_cue["spam"], n["spam"])},
        "spam_hard_cue": {"count": hard_cue["spam"], "of": n["spam"],
                          "rate": round(hard_cue["spam"] / n["spam"], 4) if n["spam"] else None,
                          "wilson95": wilson(hard_cue["spam"], n["spam"])},
        "per_cue": {lab: dict(c.most_common()) for lab, c in by.items()},
        "ham_hard_cue_examples": ham_examples,
        "limit": "not Indian UPI fraud; spam here is mostly prize/marketing SMS; a cue alone never decides an answer",
    }


def main(argv=None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--data", default="data/raw/sms_spam/SMSSpamCollection")
    ap.add_argument("--out", default="results/q2/sms.json")
    a = ap.parse_args(argv)
    p = Path(a.data)
    if not p.is_file():
        print(f"not found: {p}. Download the UCI SMS Spam Collection first (see this file's docstring).")
        return 2
    r = evaluate(p)
    Path(a.out).parent.mkdir(parents=True, exist_ok=True)
    with open(a.out, "w", encoding="utf-8", newline="\n") as f:
        f.write(json.dumps(r, indent=1, ensure_ascii=False))
    print(f"{r['messages']} messages ({r['n']}). Normal messages with any cue: {r['ham_any_cue']['count']}/{r['ham_any_cue']['of']} "
          f"{r['ham_any_cue']['wilson95']}; with a HARD cue: {r['ham_hard_cue']['count']} {r['ham_hard_cue']['wilson95']}. "
          f"Spam with any cue: {r['spam_any_cue']['count']}/{r['spam_any_cue']['of']} {r['spam_any_cue']['wilson95']}.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
