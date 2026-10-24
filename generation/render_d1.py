#!/usr/bin/env python3
"""Render D1 blind chats from authored sources (generation/d1_batch*.py).

Usage:  python generation/render_d1.py            # render + validate
Outputs (relative to repo root):
  data/blind_ai/chats/cNNN.txt
  data/blind_ai/labels.csv            (file,label,claimed_firm,bank_app_names)
  data/blind_ai/labels_extended.json
The chat TEXT is authored by the language model; this script only formats timestamps,
derives labels from the single source of truth, and checks quotas. It never looks at any
detection tool.
"""
import csv, glob, importlib.util, json, os, random, re, sys
from datetime import date, timedelta

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
BANNED = ["meera", "rahul", "navyug", "sunita", "ramesh"]


def load_chats():
    chats = []
    for path in sorted(glob.glob(os.path.join(ROOT, "generation", "d1_batch*.py"))):
        spec = importlib.util.spec_from_file_location(os.path.basename(path)[:-3], path)
        mod = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(mod)
        chats.extend(mod.CHATS)
    return sorted(chats, key=lambda c: c["id"])


def fmt_time(hhmm, style, rng):
    h, m = map(int, hhmm.split(":"))
    suffix_a = "am" if h < 12 else "pm"
    h12 = h % 12 or 12
    if style == "android":
        return f"{h12}:{m:02d} {suffix_a}"
    return f"{h12}:{m:02d}:{rng.randint(0, 59):02d} {suffix_a.upper()}"


def render_chat(c):
    rng = random.Random(c["id"])
    d0 = date(*c["start"])
    lines = []
    first = c["msgs"][0]
    sys_text = "Messages and calls are end-to-end encrypted. No one outside of this chat, not even WhatsApp, can read or listen to them."
    for i, (day, hhmm, key, text) in enumerate(c["msgs"]):
        d = d0 + timedelta(days=day)
        t = fmt_time(hhmm, c["style"], rng)
        who = c["who"][key]
        if c["style"] == "android":
            stamp = f"{d.day}/{d.month}/{d.year}, {t}"
            if i == 0:
                lines.append(f"{stamp} - {sys_text}")
            lines.append(f"{stamp} - {who}: {text}")
        else:
            stamp = f"{d.day}/{d.month}/{str(d.year)[2:]}, {t}"
            if i == 0:
                lines.append(f"[{stamp}] \u200eMessages and calls are end-to-end encrypted.")
            lines.append(f"[{stamp}] {who}: {text}")
    return "\n".join(lines) + "\n"


def msg_index(c, find):
    f = find.lower()
    for i, (_, _, _, text) in enumerate(c["msgs"], 1):
        if f in text.lower():
            return i
    raise ValueError(f"{c['id']}: payee text not found: {find}")


def main():
    chats = load_chats()
    out_dir = os.path.join(ROOT, "data", "blind_ai", "chats")
    os.makedirs(out_dir, exist_ok=True)
    rows, ext, problems = [], [], []
    for c in chats:
        fname = c["id"] + ".txt"
        with open(os.path.join(out_dir, fname), "w", encoding="utf-8") as fh:
            fh.write(render_chat(c))
        names = ";".join(f"{p['identifier']}={p['bank_name']}" for p in c["payees"] if p["bank_name"])
        rows.append([fname, c["label"], c["firm"] if c["firm"] else "", names])
        ext.append(dict(
            file=fname, label=c["label"], scenario=c["scenario"], language=c["language"],
            difficulty=c["difficulty"], claimed_firm=c["firm"],
            payees=[dict(identifier=p["identifier"], kind=p["kind"],
                         message_index=msg_index(c, p["find"]),
                         name_relation=p["relation"] if p["bank_name"] or p["relation"] else "not_applicable",
                         intended_risk=p["risk"]) for p in c["payees"]],
            voice_transcripts=c["voice"], why=c["why"]))
    with open(os.path.join(ROOT, "data", "blind_ai", "labels.csv"), "w", encoding="utf-8", newline="") as fh:
        w = csv.writer(fh)
        w.writerow(["file", "label", "claimed_firm", "bank_app_names"])
        w.writerows(rows)
    with open(os.path.join(ROOT, "data", "blind_ai", "labels_extended.json"), "w", encoding="utf-8") as fh:
        json.dump(ext, fh, ensure_ascii=False, indent=1)

    # ---- validation ----
    blob = "\n".join(render_chat(c) for c in chats).lower()
    for b in BANNED:
        if re.search(r"\b" + b + r"\b", blob):
            problems.append(f"banned name used: {b}")
    firms = [c["firm"] for c in chats if c["firm"]]
    if len(firms) != len(set(firms)):
        problems.append("duplicate firm names")
    ids = [p["identifier"] for c in chats for p in c["payees"]]
    if len(ids) != len(set(ids)):
        problems.append("duplicate payees")
    openers = [c["msgs"][0][3] for c in chats]
    if len(openers) != len(set(openers)):
        problems.append("duplicate opening lines")
    for c in chats:
        n = len(c["msgs"])
        if not (6 <= n <= 50):
            problems.append(f"{c['id']}: {n} messages (need 6-50)")
        for p in c["payees"]:
            if p["kind"] in ("account",) and not p["identifier"].startswith("0000"):
                problems.append(f"{c['id']}: account does not start 0000")
    obf = sum(1 for c in chats if any(p["find"].lower() != p["identifier"].lower() for p in c["payees"]))
    scam = sum(1 for c in chats if c["label"] == "scam")
    android = sum(1 for c in chats if c["style"] == "android")
    summary = dict(chats=len(chats), scam=scam, genuine=len(chats) - scam, android=android,
                   ios=len(chats) - android, obfuscated_payee_chats=obf,
                   by_language={l: sum(1 for c in chats if c["language"] == l) for l in sorted({c["language"] for c in chats})},
                   by_difficulty={d: sum(1 for c in chats if c["difficulty"] == d) for d in sorted({c["difficulty"] for c in chats})})
    print(json.dumps(summary, indent=1))
    if len(chats) and obf / len(chats) > 0.15:
        problems.append(f"obfuscated payee share {obf}/{len(chats)} exceeds 15%")
    if problems:
        print("PROBLEMS:"); [print(" -", p) for p in problems]; sys.exit(1)
    print("validation ok")


if __name__ == "__main__":
    main()
