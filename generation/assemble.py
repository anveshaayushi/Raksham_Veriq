import csv, json, os, random, shutil, collections, re, zipfile
import d2
R = random.Random(20261024)
OUT = "out/data"; os.makedirs(OUT + "/names_blind", exist_ok=True)
# ---- D2
rows = [(c, b, "same_entity", n) for c, b, n in d2.SAME] + [(c, b, "different_entity", n) for c, b, n in d2.DIFF] + \
       [(c, b, "lookalike_of_different_entity", n) for c, b, n in d2.LOOK] + [(c, b, "cannot_tell", n) for c, b, n in d2.CANT]
assert collections.Counter(r[2] for r in rows) == {"same_entity": 70, "different_entity": 70, "lookalike_of_different_entity": 30, "cannot_tell": 30}
R.shuffle(rows)
with open(OUT + "/names_blind/pairs.csv", "w", newline="", encoding="utf-8") as f:
    w = csv.writer(f); w.writerow(["id", "claimed_firm", "bank_app_name", "relation", "note"])
    for i, r in enumerate(rows, 1): w.writerow([f"n{i:03d}", *r[:3], r[3]])
# ---- D4 extras
vs = OUT + "/voice_scripts"
open(vs + "/audio_labels_template.csv", "w", encoding="utf-8", newline="").write("file,label,source,language,script_id\n")
open(vs + "/RECORDING_GUIDE.md", "w", encoding="utf-8").write("""# Voice recording guide (3 teammates)

All scripts are fictional (`scripts.csv`). `type` says whether the *script* reads like a scam or a genuine message; the audio label (real/fake) is separate.

## 1. Consent and privacy (read first)
- Record **only your own voice**, and only after you have given **written consent** (a message in the team chat is enough) for it to be used in this event's test set.
- **Never clone, imitate or record anyone else's voice**, including family, friends, celebrities or officials. An `own_voice_clone` clip means a clone of **your own** voice, made with your own consent.
- Do not say real names, real phone numbers, real UPI IDs or real account numbers. Read the script exactly as written: its identifiers are fictional.
- Keep clips on the team's shared folder only. **Delete all clips (originals and copies, including phone and chat backups) after the event.** Do not upload them to any public site.
- If anyone withdraws consent, remove their clips immediately and record the removal.

## 2. Recording genuine voice notes on a phone
1. Find a quiet room: door closed, fan/AC off, no TV. Sit still, phone about a hand-span from your mouth.
2. Use the WhatsApp voice-note button in a chat with yourself (or the phone's voice recorder), so the clip is a normal compressed voice note. Do not use studio/denoise apps.
3. Read the script at your normal pace, once, in a natural voice, in the language of the script. If you stumble, record again; keep only the clean take.
4. Each clip should last about the `seconds_target` in `scripts.csv` (5 to 25 s).
5. Export the voice note as `.opus` (WhatsApp's own format). Do not rename other formats to `.opus`.

## 3. File names
- Genuine human clips: `genuine_<name>_<scriptid>.opus` (example `genuine_asha_v014.opus`). `<name>` is your first name, lowercase.
- Open text-to-speech fakes: `fake_tts_<tool>_<scriptid>.opus`.
- Clones of your own voice: `fake_clone_<name>_<scriptid>.opus`.

## 4. Labels
Fill `audio_labels_template.csv` (columns `file,label,source,language,script_id`): label is `real` or `fake`; source is `human`, `open_tts` or `own_voice_clone`; language is `en`, `hi` or `hinglish`.
Record scripts of **both** types (scam_like and genuine) in your real voice so the detector cannot learn "scam script = fake".
""")
# ---- GENERATION.md
ext = json.load(open("/home/claude/d/data/blind_ai/labels_extended.json", encoding="utf-8"))
d1_lang = collections.Counter((e["label"], e["language"]) for e in ext)
d1_diff = collections.Counter((e["label"], e["difficulty"]) for e in ext)
d3 = [json.loads(l) for l in open(OUT + "/extract_blind/cases.jsonl", encoding="utf-8")]
d3_pos = sum(1 for c in d3 if c["expected"]["payees"]); d3_neg = len(d3) - d3_pos
d3_kinds = collections.Counter(p["kind"] for c in d3 for p in c["expected"]["payees"])
d4 = list(csv.DictReader(open(vs + "/scripts.csv", encoding="utf-8")))
d4c = collections.Counter((r["type"], r["language"]) for r in d4)
def tbl(c, keys_a, keys_b):
    s = "| | " + " | ".join(keys_b) + " |\n|---|" + "---|" * len(keys_b) + "\n"
    for a in keys_a: s += f"| {a} | " + " | ".join(str(c.get((a, b), 0)) for b in keys_b) + " |\n"
    return s
open(OUT + "/GENERATION.md", "w", encoding="utf-8").write(f"""# GENERATION.md: provenance of the blind datasets

**Date: to be filled by the human.**

## Who wrote what
| Dataset | Written by | Notes |
|---|---|---|
| D1 blind chats (`data/blind_ai/`) | A separate AI session (the one that produced `generation/d1_batch*.py`, rendered by `generation/render_d1.py`) | **Model name was not recorded in the delivered files; the human who ran Prompt 1 must fill it in.** |
| D2 name pairs, D3 extraction cases, D4 voice scripts, this file | **Claude Sonnet 5.5 (Anthropic), via claude.ai** | Source: `generation/d2.py`, `d3.py`, `build_d3.py`, `d4.py`, `build_d4.py`, `assemble.py` (seed 20261024). |

## IMPORTANT: D2, D3 and D4 are NOT blind in the way Prompt 1 intends
Prompt 1 asks for a fresh chat with no knowledge of the tool, preferably a different AI from the one that wrote the engine. D2-D4 were written by the **same model, in the same conversation, that wrote VERIQ's parser, extractor, name matcher and rules engine**, and the writer had seen that code and its word lists (for example the matcher's list of generic words and gateway names). Mitigations actually applied: relations/expected values were decided by real-world judgement; the engine was **not run** on D2-D4 and nothing was changed in response to any engine output. Edits that were made came from structural self-checks only (a forbidden name removed, an invalid 20-digit account fixed, two cases dropped to hit the quotas, link cases rewritten to include a scheme, a forbidden name removed from D2); every fictional identifier follows Prompt 1's safety rules. Residual risk: unconscious alignment, e.g. D2's "shares only a generic word" pairs and D3's OTP/ticket-id negatives mirror behaviours the writer knew the engine cares about. Treat results on D2-D4 as **optimistic**, and prefer an independently written set if one can be produced.

## Counts
**D1** (80 chats; label x language):
{tbl(d1_lang, ["scam", "genuine"], ["english", "hinglish", "devanagari_hindi"])}
D1 (label x difficulty):
{tbl(d1_diff, ["scam", "genuine"], ["easy", "medium", "hard", "ambiguous"])}
D1 formats: 58 Android-style, 22 iPhone-style files; voice notes in {sum(1 for e in ext if e.get('voice_transcripts'))} chats.

**D2** (`names_blind/pairs.csv`, 200 pairs): same_entity 70, different_entity 70, lookalike_of_different_entity 30, cannot_tell 30.

**D3** (`extract_blind/cases.jsonl`, 100 cases): designed as 60 positive and 40 negative/tricky cases. Four of the 40 tricky cases also contain a real payee next to distractors, so by "has an expected payee" the split is {d3_pos} with payees and {d3_neg} without. Expected payee kinds: {dict(d3_kinds)}.

**D4** (`voice_scripts/scripts.csv`, 60 scripts; type x language):
{tbl(d4c, ["scam_like", "genuine"], ["en", "hi", "hinglish"])}
10 scam_like and 10 genuine scripts mention a payee spoken aloud. Reading time targets are 8 to 16 s (estimated at about 2.5 words/s, 2.2 for Hindi; not measured by recording).

## Self-checks run on D2-D4 (structure only, engine not used)
Row/quota counts, no forbidden names (Meera, Rahul, Navyug, Sunita, Ramesh), phones follow 5 digits + 000 + 2 digits, accounts begin 0000, every expected account/phone/IFSC in D3 is recoverable from its own text.

## Known weaknesses of this data
- Written by AI: tidier and more varied in a "designed" way than real chats and real voice notes; scams follow familiar scripts.
- D1 was authored as data tables and rendered by code, so message formatting and timing are more regular than real exports.
- D2-D4 are correlated with the engine's author (see above). D1's writer is a different session but may share training-data habits with the engine's author model.
- Relation labels in D2 (and "ambiguous" in D1) are judgement calls; `cannot_tell` and `lookalike` boundaries are fuzzy. A second human labeller is advisable.
- D3: the expected canonical value for links assumes the scheme written in the text; some tricky negatives (a helpline number, a retracted ID) are debatable.
- D4: scripts only; no audio exists. Genuine and scam-like scripts were matched in style by hand, not verified with a classifier. Hindi was written without a native-speaker review.
- All identifiers are fictional but some firm or shop names could coincide with real ones by chance.
""")
print(open(OUT + "/GENERATION.md", encoding="utf-8").read()[:400])
