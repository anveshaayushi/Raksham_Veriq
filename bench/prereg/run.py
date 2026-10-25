"""Scores the AI-generated datasets exactly as bench/PREREG.md says (metrics fixed BEFORE any run).

    python -m bench.prereg.run d1 [--tag before]   -> results/prereg/d1_blind_ai.<tag>.json
    python -m bench.prereg.run d2 [--tag before]   -> results/prereg/d2_names.<tag>.json
    python -m bench.prereg.run d3 [--tag before]   -> results/prereg/d3_extract.<tag>.json
    python -m bench.prereg.run report              -> results/prereg/PREREG_RESULTS.md (from the saved JSON files)

Each (set, tag) runs ONCE: an existing output is never overwritten (exit 3). The first run of each set uses
tag "before" on the code as committed; after fixes the set is re-run with tag "after" (and "final" after a second
fix); every result after "before" is NOT blind. Nothing here changes the data. Sets are never averaged together.

Labels (bench/PREREG.md addendum): D1 = "AI-generated blind set, n=80, author model not recorded";
D2/D3 = "AI-generated, NOT blind (the writer had seen the engine; results are optimistic)".
D1 caveat: 12 of the 80 chats were run through the Kit tab on 25 Oct ~05:10 IST before this scorer existed
(KIT_SEEN below); metrics are reported for all 80 and for the 68 unseen chats separately.
"""
from __future__ import annotations

import argparse
import csv
import json
import math
import re
import subprocess
from collections import Counter, defaultdict
from datetime import date, datetime, timedelta, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / "results" / "prereg"
ORDER = ["LINKED", "NAME_DISCREPANCY", "REGISTRATION_CONFLICT", "HUMAN_REVIEW", "INCONCLUSIVE", "NO_MAJOR_ISSUE"]
ACCUSING = {"NAME_DISCREPANCY", "REGISTRATION_CONFLICT", "LINKED", "HUMAN_REVIEW"}
KIT_SEEN = {"c001.txt", "c002.txt", "c003.txt", "c004.txt", "c005.txt", "c007.txt", "c008.txt", "c009.txt", "c012.txt",
            "c013.txt", "c018.txt", "c024.txt"}
D1_LABEL = "AI-generated blind set, n=80, author model not recorded, 25 Oct 2026"
NOT_BLIND = "AI-generated, NOT blind (the writer had seen the engine; results are optimistic)"


def wilson(k, n, z=1.96):
    if not n:
        return None
    p = k / n
    d = 1 + z * z / n
    c = (p + z * z / (2 * n)) / d
    h = z * math.sqrt(p * (1 - p) / n + z * z / (4 * n * n)) / d
    return [round(max(0.0, c - h), 3), round(min(1.0, c + h), 3)]


def frac(k, n):
    return {"count": k, "of": n, "rate": round(k / n, 3) if n else None, "wilson95": wilson(k, n)}


def stamp() -> dict:
    try:
        commit = subprocess.run(["git", "rev-parse", "--short", "HEAD"], cwd=ROOT, capture_output=True, text=True).stdout.strip()
        dirty = bool(subprocess.run(["git", "status", "--porcelain", "--", "app", "extract", "parsing", "match", "rules",
                                     "core", "registry"], cwd=ROOT, capture_output=True, text=True).stdout.strip())
    except OSError:
        commit, dirty = "unknown", None
    return {"run_at_ist": datetime.now(timezone(timedelta(hours=5, minutes=30))).strftime("%Y-%m-%d %H:%M IST"),
            "commit": commit, "engine_files_uncommitted": dirty}


def norm_id(kind: str, value: str) -> str:
    v = (value or "").strip()
    if kind in ("account", "bank_account"):
        return re.sub(r"\D", "", v)
    if kind == "phone":
        return re.sub(r"\D", "", v)[-10:]
    return v.lower().replace(" ", "")


# ---------------------------------------------------------------- D1 ----
def run_d1(folder: Path = ROOT / "data" / "blind_ai") -> dict:
    from app.case import UserCheck, build_case
    from app.intake import decode_text
    from bench.datasets import load_blind_ai
    items, problems = load_blind_ai(folder)
    per = []
    for it in items:
        ext = it["extended"]
        text = decode_text(Path(it["path"]).read_bytes())
        checks = {k: UserCheck(v, "Bank app (beneficiary name)", date(2026, 10, 25)) for k, v in it["bank_app_names_parsed"].items()}
        tr = {t["file"]: t["transcript"] for t in ext.get("voice_transcripts") or []}
        c = build_case(case_id=Path(it["file"]).stem, chat_text=text, claimed_firm=(it.get("claimed_firm") or "").strip(),
                       checks=checks, transcripts=tr or None)
        res = c.case_result()
        found = {p.value_norm.lower(): c.result_for(p.id).result for p in c.payees}
        payees = []
        for p in ext.get("payees") or []:
            key = norm_id(p["kind"], p["identifier"])
            got = found.get(key)
            if got is None and p["kind"] == "phone_upi":
                got = found.get(p["identifier"].lower())
            payees.append({"identifier": p["identifier"], "kind": p["kind"], "intended_risk": p["intended_risk"],
                           "name_relation": p["name_relation"], "result": got or "not extracted"})
        row = {"file": it["file"], "label": it["label"], "language": ext.get("language"), "difficulty": ext.get("difficulty"),
               "result": res, "payees_found": sorted(found), "payees": payees, "kit_seen": it["file"] in KIT_SEEN,
               "warnings": c.extraction.warnings[:3], "why_label": ext.get("why"),
               "payment_links": c.payment_links() if hasattr(c, "payment_links") else []}
        if tr:  # PREREG: voice only escalates. No audio is supplied, so the voice detector does not run; the
            # transcript can only add text. Compare with the same chat scored without transcripts.
            c0 = build_case(case_id=Path(it["file"]).stem, chat_text=text, claimed_firm=(it.get("claimed_firm") or "").strip(),
                            checks=checks)
            r0 = c0.case_result()
            row["without_transcripts"] = r0
            row["voice_made_it_clearer"] = (res in ORDER and r0 in ORDER and ORDER.index(res) > ORDER.index(r0))
        per.append(row)
    return {"set": D1_LABEL, "problems": problems, **stamp(), "all": d1_metrics(per),
            "unseen_by_kit": d1_metrics([r for r in per if not r["kit_seen"]]), "per_chat": per}


def outcome(r) -> str:
    res = r["result"]
    if res is None:
        return "no answer"
    if r["label"] == "scam":
        return "missed" if res == "NO_MAJOR_ISSUE" else ("accusing" if res in ACCUSING else "verify-first")
    return "false alarm" if res in ACCUSING else ("verify-first" if res == "INCONCLUSIVE" else "clear")


def d1_metrics(per: list[dict]) -> dict:
    scam = [r for r in per if r["label"] == "scam"]
    gen = [r for r in per if r["label"] == "genuine"]
    o = Counter((r["label"], outcome(r)) for r in per)
    warned = sum(1 for r in scam if r["result"] is not None and r["result"] != "NO_MAJOR_ISSUE")
    m = {"n": len(per), "scam": {"n": len(scam),
                                  "warned": frac(warned, len(scam)),
                                  "accusing": frac(o[("scam", "accusing")], len(scam)),
                                  "verify_first": frac(o[("scam", "verify-first")], len(scam)),
                                  "missed": frac(o[("scam", "missed")], len(scam)),
                                  "no_answer": frac(o[("scam", "no answer")], len(scam))},
         "genuine": {"n": len(gen),
                     "false_alarm_accusing": frac(o[("genuine", "false alarm")], len(gen)),
                     "verify_first": frac(o[("genuine", "verify-first")], len(gen)),
                     "clear_no_major_issue": frac(o[("genuine", "clear")], len(gen)),
                     "no_answer": frac(o[("genuine", "no answer")], len(gen))},
         "result_counts": {f"{l}: {res}": v for (l, res), v in sorted(Counter((r["label"], str(r["result"])) for r in per).items())}}
    # payee level against intended_risk; unclear reported separately
    pl = defaultdict(Counter)
    for r in per:
        for p in r["payees"]:
            res = p["result"]
            pl[p["intended_risk"]][res] += 1
    def payee_block(risk):
        c = pl.get(risk, Counter())
        n = sum(c.values())
        accused = sum(v for k, v in c.items() if k in ACCUSING)
        cleared = c.get("NO_MAJOR_ISSUE", 0)
        notx = c.get("not extracted", 0)
        return {"n": n, "results": dict(c), "accusing": frac(accused, n), "cleared": frac(cleared, n),
                "not_extracted": frac(notx, n),
                "warned_or_verify_first": frac(n - cleared - notx, n)}
    m["payees"] = {"risky": payee_block("risky"), "fine": payee_block("fine"), "unclear (separate)": payee_block("unclear")}
    rel = defaultdict(Counter)
    for r in per:
        for p in r["payees"]:
            rel[f"{p['name_relation']} ({p['intended_risk']})"][p["result"]] += 1
    m["payees_by_name_relation"] = {k: dict(v) for k, v in sorted(rel.items())}
    kinds = defaultdict(Counter)
    for r in per:
        for p in r["payees"]:
            kinds[p["kind"]]["extracted" if p["result"] != "not extracted" else "not extracted"] += 1
    m["payees_extracted_by_kind"] = {k: dict(v) for k, v in sorted(kinds.items())}
    for dim in ("language", "difficulty"):
        b = defaultdict(Counter)
        for r in per:
            b[r[dim]][f"{r['label']}: {outcome(r)}"] += 1
        m[f"by_{dim}"] = {k: dict(v) for k, v in sorted(b.items())}
    vt = [r for r in per if "without_transcripts" in r]
    m["voice_transcript_chats"] = {"n": len(vt), "voice_made_it_clearer": sum(r["voice_made_it_clearer"] for r in vt),
                                   "note": "no audio supplied: the voice detector did not run; transcripts add text only"}
    fails = []
    for r in per:
        oc = outcome(r)
        bad_p = [p for p in r["payees"] if (p["intended_risk"] == "risky" and p["result"] in ("NO_MAJOR_ISSUE", "not extracted"))
                 or (p["intended_risk"] == "fine" and p["result"] in ACCUSING)]
        if oc in ("missed", "no answer", "false alarm") or bad_p:
            fails.append({"file": r["file"], "label": r["label"], "veriq": r["result"], "outcome": oc,
                          "payee_problems": [f"{p['identifier']} ({p['kind']}, {p['intended_risk']}, {p['name_relation']}): {p['result']}"
                                             for p in bad_p],
                          "warnings": r["warnings"], "kit_seen": r["kit_seen"]})
    m["failures"] = fails
    return m


# ---------------------------------------------------------------- D2 ----
def run_d2(path: Path = ROOT / "data" / "names_blind" / "pairs.csv") -> dict:
    from bench.datasets import load_names_blind
    from match import match_names
    rows, problems = load_names_blind(path)
    by = defaultdict(Counter)
    per = []
    for r in rows:
        v, why = match_names(r["claimed_firm"], r["bank_app_name"])
        by[r["relation"]][v] += 1
        per.append({**r, "verdict": v, "reason": why})
    n = {k: sum(c.values()) for k, c in by.items()}
    diff, look = by["different_entity"], by["lookalike_of_different_entity"]
    dangerous = diff["match"] + look["match"]
    m = {"set": NOT_BLIND, "problems": problems, **stamp(), "n": len(rows),
         "verdicts_by_relation": {k: dict(v) for k, v in sorted(by.items())},
         "headline_dangerous_matches": frac(dangerous, n.get("different_entity", 0) + n.get("lookalike_of_different_entity", 0)),
         "false_alarm_same_entity_called_discrepancy": frac(by["same_entity"]["discrepancy"], n.get("same_entity", 0)),
         "same_entity_matched": frac(by["same_entity"]["match"], n.get("same_entity", 0)),
         "different_entity_discrepancy": frac(diff["discrepancy"], n.get("different_entity", 0)),
         "lookalike_warned_lookalike_or_discrepancy": frac(look["lookalike"] + look["discrepancy"], n.get("lookalike_of_different_entity", 0)),
         "cannot_tell_unverified": frac(by["cannot_tell"]["unverified"], n.get("cannot_tell", 0))}
    bad = {"same_entity": {"discrepancy"}, "different_entity": {"match"}, "lookalike_of_different_entity": {"match"},
           "cannot_tell": {"match", "discrepancy", "lookalike"}}
    m["failures"] = [{k: p[k] for k in ("id", "claimed_firm", "bank_app_name", "relation", "verdict", "reason", "note")}
                     for p in per if p["verdict"] in bad.get(p["relation"], set())]
    m["per_pair"] = per
    return m


# ---------------------------------------------------------------- D3 ----
KIND = {"upi": "upi_vpa", "account": "bank_account", "ifsc": "ifsc", "phone": "phone", "link": "url"}


def amounts_of(msgs) -> list[int]:
    from app.adapters.extract import amount_in
    out = []
    for m in msgs:
        a = amount_in(m.text or "")
        if not a:
            continue
        mm = re.match(r"₹([\d,]+(?:\.\d+)?)\s?(k|lakh|lac)?", a, re.I)
        if mm:
            v = float(mm.group(1).replace(",", ""))
            unit = (mm.group(2) or "").lower()
            v *= 1000 if unit == "k" else 100000 if unit in ("lakh", "lac") else 1
            out.append(int(round(v)))
    return out


def run_d3(path: Path = ROOT / "data" / "extract_blind" / "cases.jsonl") -> dict:
    from app.adapters.extract import run as extract_run
    from bench.datasets import load_extract_blind
    items, problems = load_extract_blind(path)
    tp, fp, fn = Counter(), Counter(), Counter()
    exact = Counter()
    amt = Counter()
    snx_total = snx_bad = 0
    per = []
    for d in items:
        ex = extract_run(d["text"], d["id"])
        got = defaultdict(set)
        for i in ex.indicators:
            got[i.type].add(norm_id({"bank_account": "account", "phone": "phone"}.get(i.type, i.type), i.value_norm))
        exp = defaultdict(set)
        for p in d["expected"]["payees"]:
            exp[KIND[p["kind"]]].add(norm_id(p["kind"], p["value"]))
        row_ok = True
        for k in KIND.values():
            t = got[k] & exp[k]
            tp[k] += len(t)
            fp[k] += len(got[k] - exp[k])
            fn[k] += len(exp[k] - got[k])
            if exp[k]:
                exact[(k, got[k] >= exp[k])] += 1
            if got[k] != exp[k]:
                row_ok = False
        want_amt = sorted(d["expected"].get("amounts_inr") or [])
        have_amt = sorted(set(amounts_of(ex.messages)))
        amt["tp"] += len(set(want_amt) & set(have_amt))
        amt["fp"] += len(set(have_amt) - set(want_amt))
        amt["fn"] += len(set(want_amt) - set(have_amt))
        bad_snx = []
        for s in d["expected"].get("should_not_extract") or []:
            snx_total += 1
            sv, sd = s.lower().replace(" ", ""), re.sub(r"\D", "", s)
            hit = any(v == sv or (k in ("bank_account", "phone") and sd and v == sd[-10:] if k == "phone" else
                                  k == "bank_account" and sd and v == sd)
                      for k, vs in got.items() for v in vs)
            if hit:
                snx_bad += 1
                bad_snx.append(s)
        per.append({"id": d["id"], "expected": {k: sorted(v) for k, v in exp.items() if v},
                    "got": {k: sorted(v) for k, v in got.items() if v}, "all_payee_kinds_exact": row_ok,
                    "amounts_expected": want_amt, "amounts_got": have_amt, "should_not_extract_but_did": bad_snx,
                    "messages_parsed": len(ex.messages)})
    kinds = {}
    for k in KIND.values():
        p = tp[k] + fp[k]
        r = tp[k] + fn[k]
        kinds[k] = {"tp": tp[k], "fp": fp[k], "fn": fn[k], "precision": frac(tp[k], p), "recall": frac(tp[k], r),
                    "cases_with_this_kind_all_found": frac(exact[(k, True)], exact[(k, True)] + exact[(k, False)])}
    PAY = ("upi_vpa", "bank_account")
    ptp, pfp, pfn = sum(tp[k] for k in PAY), sum(fp[k] for k in PAY), sum(fn[k] for k in PAY)
    m = {"set": NOT_BLIND, "problems": problems, **stamp(), "n": len(items), "by_kind": kinds,
         "payees_upi_and_account": {"precision": frac(ptp, ptp + pfp), "recall": frac(ptp, ptp + pfn)},
         "amounts (display helper amount_in, first amount per message)": {
             "precision": frac(amt["tp"], amt["tp"] + amt["fp"]), "recall": frac(amt["tp"], amt["tp"] + amt["fn"])},
         "false_extraction_on_should_not_extract": frac(snx_bad, snx_total),
         "cases_exact_all_kinds": frac(sum(1 for r in per if r["all_payee_kinds_exact"]), len(per)),
         "no_dated_message_parsed": sum(1 for r in per if r["messages_parsed"] == 0)}
    m["failures"] = [r for r in per if not r["all_payee_kinds_exact"] or r["should_not_extract_but_did"]]
    m["per_case"] = per
    return m


PAYEE_LIKE = ("upi_vpa", "bank_account", "phone", "url", "ifsc")


# ---------------------------------------------------------------- report ----
def _f(x):
    if not x or x.get("of") in (0, None):
        return "n/a"
    return f"{x['count']}/{x['of']} ({x['rate']:.0%}) [{x['wilson95'][0]:.2f}, {x['wilson95'][1]:.2f}]"


def report() -> str:
    L = ["# Pre-registered dataset results", "",
         "Metrics fixed in `bench/PREREG.md` before any run. Each line gives the command, date, commit and dataset. "
         "Intervals: 95% Wilson. Sets are never averaged together.", ""]
    for tag in ("before", "after", "final"):
        f1, f2, f3 = (OUT / f"d1_blind_ai.{tag}.json", OUT / f"d2_names.{tag}.json", OUT / f"d3_extract.{tag}.json")
        if not any(p.is_file() for p in (f1, f2, f3)):
            continue
        L += [{"before": "## BEFORE any fix (as committed)",
               "after": "## AFTER the first fixes (NOT blind: we saw the failures first)",
               "final": "## FINAL, after a second fix (NOT blind). The first fixes let one-letter copycat names "
                        "('COBOLT' for 'Cobalt') count as a match, so spelling variants now give 'can't tell'"}[tag], ""]
        if f1.is_file():
            d = json.loads(f1.read_text(encoding="utf-8"))
            L += [f"### D1 chats: {d['set']}", f"`python -m bench.prereg.run d1 --tag {tag}` · {d['run_at_ist']} · commit {d['commit']}", ""]
            for name, m in (("all 80", d["all"]), ("68 not seen in the Kit tab", d["unseen_by_kit"])):
                s, g = m["scam"], m["genuine"]
                L += [f"**{name}**: scams warned {_f(s['warned'])}; accusing {_f(s['accusing'])}; verify-first {_f(s['verify_first'])}; "
                      f"missed (called no major issue) {_f(s['missed'])}; no answer {_f(s['no_answer'])}. "
                      f"Genuine: false alarms (accusing) {_f(g['false_alarm_accusing'])}; verify-first {_f(g['verify_first'])}; "
                      f"no major issue {_f(g['clear_no_major_issue'])}; no answer {_f(g['no_answer'])}.", ""]
            per = d["per_chat"]
            gen_none = [r for r in per if r["label"] == "genuine" and r["result"] is None]
            L.append(f"Of the genuine 'no answer' chats, {sum(1 for r in gen_none if not r['payees'])}/{len(gen_none)} contain "
                     "no payment request at all (nothing to check: the correct outcome).")
            sc_none = [r for r in per if r["label"] == "scam" and r["result"] is None]
            L.append(f"Of the scam 'no answer' chats, {sum(1 for r in sc_none if r.get('payment_links'))}/{len(sc_none)} now get "
                     "the 'asked to pay through a link: check before you pay' answer (not counted as warned above)."
                     if tag != "before" else f"Scam 'no answer' chats: {len(sc_none)} (payment link only: "
                     f"{sum(1 for r in sc_none if any(p['kind'] == 'link' for p in r['payees']))}).")
            L.append("")
            p = d["all"]["payees"]
            L += [f"Payees (all 80): risky payees cleared {_f(p['risky']['cleared'])}, not extracted {_f(p['risky']['not_extracted'])}; "
                  f"fine payees accused {_f(p['fine']['accusing'])}; unclear (separate) results {p['unclear (separate)']['results']}.",
                  f"Extraction by kind: {d['all']['payees_extracted_by_kind']}.",
                  f"Voice-transcript chats: {d['all']['voice_transcript_chats']}.", "",
                  f"Failures: {len(d['all']['failures'])} chats (listed in the JSON).", ""]
        if f2.is_file():
            d = json.loads(f2.read_text(encoding="utf-8"))
            L += [f"### D2 name pairs: {d['set']}", f"`python -m bench.prereg.run d2 --tag {tag}` · {d['run_at_ist']} · commit {d['commit']}", "",
                  f"**Dangerous matches** (different or lookalike called 'match'): {_f(d['headline_dangerous_matches'])}. "
                  f"False alarm (same entity called discrepancy): {_f(d['false_alarm_same_entity_called_discrepancy'])}. "
                  f"Same entity matched: {_f(d['same_entity_matched'])}. Different entity -> discrepancy: {_f(d['different_entity_discrepancy'])}. "
                  f"Lookalike warned: {_f(d['lookalike_warned_lookalike_or_discrepancy'])}. Cannot tell -> unverified: {_f(d['cannot_tell_unverified'])}.",
                  f"Verdicts by relation: {d['verdicts_by_relation']}.", ""]
        if f3.is_file():
            d = json.loads(f3.read_text(encoding="utf-8"))
            L += [f"### D3 extraction: {d['set']}", f"`python -m bench.prereg.run d3 --tag {tag}` · {d['run_at_ist']} · commit {d['commit']}", ""]
            for k, v in d["by_kind"].items():
                L.append(f"- {k}: precision {_f(v['precision'])}, recall {_f(v['recall'])}, cases fully found {_f(v['cases_with_this_kind_all_found'])}")
            a = d["amounts (display helper amount_in, first amount per message)"]
            L += [f"- payees (UPI + account): precision {_f(d['payees_upi_and_account']['precision'])}, recall {_f(d['payees_upi_and_account']['recall'])}",
                  f"- amounts (display helper only, first amount per message): precision {_f(a['precision'])}, recall {_f(a['recall'])}",
                  f"- false extraction on should-not-extract strings: {_f(d['false_extraction_on_should_not_extract'])}",
                  f"- cases exact on every kind: {_f(d['cases_exact_all_kinds'])}; cases with no dated message parsed: {d['no_dated_message_parsed']}", ""]
    L += ["D4 (voice scripts): nothing run, by design (no recordings).",
          "Teammate blind set (`data/blind/`): not provided, not run.", ""]
    return "\n".join(L)


def main(argv=None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("what", choices=["d1", "d2", "d3", "report"])
    ap.add_argument("--tag", default="before", choices=["before", "after", "final"])
    a = ap.parse_args(argv)
    OUT.mkdir(parents=True, exist_ok=True)
    if a.what == "report":
        (OUT / "PREREG_RESULTS.md").write_text(report(), encoding="utf-8", newline="\n")
        print(report())
        return 0
    name = {"d1": "d1_blind_ai", "d2": "d2_names", "d3": "d3_extract"}[a.what]
    out = OUT / f"{name}.{a.tag}.json"
    if out.is_file():
        print(f"{out.name} exists: this set was already run with tag '{a.tag}'. Runs are never overwritten.")
        return 3
    r = {"d1": run_d1, "d2": run_d2, "d3": run_d3}[a.what]()
    r["tag"] = a.tag
    out.write_text(json.dumps(r, indent=1, ensure_ascii=False, default=str), encoding="utf-8", newline="\n")
    print(f"wrote {out.relative_to(ROOT)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
