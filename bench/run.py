"""Run VERIQ's chat-side engine on a benchmark split and report measured numbers (FINALE, Claude C).

    python -m bench.run dev
    python -m bench.run test      (the reported numbers; run once, never tuned on)

Measures, on synthetic chats with known ground truth:
  1. payee extraction: precision / recall of payment destinations (UPI IDs, account numbers), with distractors
     (e-mails, phone numbers, order numbers, URLs) that must NOT be picked up
  2. decisions per payee vs the expected answer; confusion matrix
  3. false alarms: legitimate payees given an accusing answer (NAME_DISCREPANCY / LINKED / REG_CONFLICT)
     missed scams: scam payees given NO_MAJOR_ISSUE
  4. time per chat
Writes bench/results_<split>.json and prints failure cases.
"""

from __future__ import annotations

import dataclasses
import json
import sys
import time
from collections import Counter
from pathlib import Path

from core.schemas import Evidence
from extract import extract, payees
from parsing import parse_chat
from registry.stub import StubRegistry
from rules import case_evidence, decide

HERE = Path(__file__).resolve().parent
ACCUSING = {"NAME_DISCREPANCY", "LINKED", "REGISTRATION_CONFLICT"}


def run_case(c: dict) -> dict:
    t0 = time.perf_counter()
    msgs = parse_chat(c["chat_txt"])
    tr = c.get("transcripts") or {}
    msgs = [dataclasses.replace(m, text=tr[m.media_ref]) if m.kind == "voice" and tr.get(m.media_ref) else m
            for m in msgs]
    inds, cues = extract(msgs, c["case_id"])
    pays = payees(inds)
    name_ev = []
    for p in pays:
        if p.value_norm in c["checks"]:
            name_ev.append(Evidence(evidence_id=f"{c['case_id']}-E{len(name_ev) + 1}", payee_id=p.id, lane="payee_name",
                                    class_="A", claimed=f"payee belongs to {c['claimed_firm']}",
                                    observed=c["checks"][p.value_norm], source="user-reported: benchmark",
                                    as_of="2026-10-24", limitation="synthetic"))
    reg = StubRegistry()
    registry = [reg.lookup(p.id, p.type, p.value_norm) for p in pays]
    ev = case_evidence(case_id=c["case_id"], claimed_firm=c["claimed_firm"], messages=msgs, indicators=inds,
                       payees=pays, payee_name_evidence=name_ev, voice=[], registry=registry, as_of="2026-10-24")
    ds = decide(claimed_firm=c["claimed_firm"], payees=pays, indicators=inds, cues=cues, evidence=ev, voice=[],
                registry=registry)
    return {"payees": [p.value_norm for p in pays], "results": {p.value_norm: d.result for p, d in zip(pays, ds)},
            "ms": (time.perf_counter() - t0) * 1000}


def evaluate(split: str, out_dir: Path | None = None, data_dir: Path | None = None) -> dict:
    """out_dir/data_dir default to bench/ and bench/data/ (scripts/reproduce.py writes to results/ instead)."""
    cases = json.loads(((data_dir or HERE / "data") / f"{split}.json").read_text(encoding="utf-8"))
    tp = fp = fn = 0
    confusion: Counter = Counter()
    false_alarm = legit_n = missed = scam_n = 0
    failures, times = [], []
    for c in cases:
        out = run_case(c)
        times.append(out["ms"])
        truth = [p["value_norm"] for p in c["payees"]]
        got = out["payees"]
        tp += len(set(got) & set(truth))
        fp += len(set(got) - set(truth))
        fn += len(set(truth) - set(got))
        for p, exp in zip(truth, c["expected"]):
            res = out["results"].get(p, "NOT_EXTRACTED")
            confusion[(exp, res)] += 1
            if not c["is_scam"]:
                legit_n += 1
                false_alarm += res in ACCUSING
            else:
                scam_n += 1
                missed += res == "NO_MAJOR_ISSUE"
            if res != exp:
                failures.append({"case": c["case_id"], "kind": c["kind"], "payee": p, "expected": exp, "got": res,
                                 "typed_name": c["checks"].get(p), "firm": c["claimed_firm"]})
        for p in set(got) - set(truth):
            failures.append({"case": c["case_id"], "kind": c["kind"], "payee": p, "expected": "not a payee",
                             "got": "extracted as payee"})
    total = sum(confusion.values())
    correct = sum(v for (e, g), v in confusion.items() if e == g)
    times.sort()
    res = {
        "split": split, "chats": len(cases), "payees": total,
        "extraction": {"tp": tp, "fp": fp, "fn": fn, "precision": round(tp / (tp + fp), 4) if tp + fp else None,
                       "recall": round(tp / (tp + fn), 4) if tp + fn else None},
        "decision_accuracy": round(correct / total, 4) if total else None,
        "false_alarms_on_legit_payees": {"count": false_alarm, "of": legit_n},
        "scam_payees_marked_no_major_issue": {"count": missed, "of": scam_n},
        "confusion": {f"{e} -> {g}": v for (e, g), v in sorted(confusion.items())},
        "ms_per_chat": {"median": round(times[len(times) // 2], 2), "max": round(times[-1], 2)},
        "failures": failures[:40], "failure_count": len(failures),
    }
    with open((out_dir or HERE) / f"results_{split}.json", "w", encoding="utf-8", newline="\n") as f:
        f.write(json.dumps(res, indent=1, ensure_ascii=False))
    return res


def main(argv: list[str]) -> int:
    split = argv[1] if len(argv) > 1 else "dev"
    r = evaluate(split)
    print(json.dumps({k: v for k, v in r.items() if k != "failures"}, indent=1, ensure_ascii=False))
    for f in r["failures"][:15]:
        print("FAIL", f)
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
