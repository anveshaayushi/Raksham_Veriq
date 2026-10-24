import csv, os, random, re
import d4
rows = list(d4.ROWS)
assert len(rows) == 60 and sum(r[1]=="scam_like" for r in rows) == 30
random.Random(20261024).shuffle(rows)
PAYEE = re.compile(r"\b(dot|underscore)\b.*\bat\b|\bat\b \w+ par|शून्य शून्य|zero zero zero zero|डॉट|एट ", re.I)
os.makedirs("out/data/voice_scripts", exist_ok=True)
out, issues, payee_n = [], [], {"scam_like": 0, "genuine": 0}
for i, (lang, typ, text) in enumerate(rows, 1):
    words = len(text.split())
    secs = round(words / (2.2 if lang == "hi" else 2.5))
    if not 5 <= secs <= 25: issues.append((i, words, secs))
    if PAYEE.search(text): payee_n[typ] += 1
    if re.search(r"meera|rahul|navyug|sunita|ramesh", text, re.I): issues.append((i, "forbidden"))
    out.append([f"v{i:03d}", lang, typ, secs, text])
with open("out/data/voice_scripts/scripts.csv", "w", newline="", encoding="utf-8") as f:
    w = csv.writer(f); w.writerow(["id","language","type","seconds_target","text"]); w.writerows(out)
print("issues", issues, "payee-mentioning", payee_n)
from collections import Counter
print(Counter((r[1], r[2]) for r in out)); print("seconds range", min(r[3] for r in out), max(r[3] for r in out))
