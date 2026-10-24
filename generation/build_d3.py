import json, random, re
import d3
R = random.Random(20261024)
DEV = {ord(c): str(i) for i, c in enumerate("०१२३४५६७८९")}
def fmt(msgs, style, day, minute0):
    out, t = [], minute0
    for k, (who, txt) in enumerate(msgs):
        t += R.randint(1, 7); h24, m = (t // 60) % 24, t % 60
        h12 = h24 % 12 or 12
        if style == "android":
            out.append(f"{day:02d}/10/2026, {h12}:{m:02d} {'am' if h24 < 12 else 'pm'} - {who}: {txt}")
        else:
            out.append(f"[{day:02d}/10/26, {h12}:{m:02d}:{R.randint(0,59):02d} {'AM' if h24 < 12 else 'PM'}] {who}: {txt}")
    return "\n".join(out)
rows = [("pos", c) for c in d3.POS] + [("neg", c) for c in d3.NEG]
assert len(d3.POS) == 60 and len(d3.NEG) == 40, (len(d3.POS), len(d3.NEG))
R.shuffle(rows)
lines, problems = [], []
for i, (kind, (msgs, payees, amounts, nots)) in enumerate(rows, 1):
    cid = f"x{i:03d}"
    text = fmt(msgs, "android" if R.random() < .7 else "iphone", R.randint(3, 24), R.randint(540, 1200))
    # self-check: account/phone/ifsc values recoverable from the text itself (digits-only view), when written as digits
    raw = " ".join(t for _, t in msgs).translate(DEV)
    digits = re.sub(r"[^0-9A-Za-z]", "", raw).lower()
    for k, v in payees:
        if k in ("account", "phone", "ifsc") and v.lower() not in digits:
            words = any(w in raw.lower() for w in ("zero", "nine eight"))
            if not words: problems.append((cid, k, v))
        if k == "upi" and "@" in v and not re.search(r"\bat\b|@|\(at\)|\[at\]", raw.lower()) and "pa=" not in raw.lower():
            problems.append((cid, k, v))
    lines.append(json.dumps({"id": cid, "text": text, "expected": {"payees": [{"kind": k, "value": v} for k, v in payees],
                  "amounts_inr": amounts, "should_not_extract": nots}}, ensure_ascii=False))
    assert not re.search(r"meera|rahul|navyug|sunita|ramesh", text, re.I), cid
print("problems:", problems)
import os; os.makedirs("out/data/extract_blind", exist_ok=True)
open("out/data/extract_blind/cases.jsonl", "w", encoding="utf-8").write("\n".join(lines) + "\n")
print(len(lines), "cases;", sum(1 for k, _ in rows if k == "pos"), "positive;", sum(1 for k, _ in rows if k == "neg"), "negative")
