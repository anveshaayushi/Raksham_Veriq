"""Name-matcher evaluation on a labelled list of (claimed firm, name the bank app shows) pairs (Q2 item d).

    python -m bench.names.run                         -> bench/names/results.json + a table
    python -m bench.names.run --pairs data/blind/name_pairs_blind.csv --out results/q2/names_blind.json

relation column:
  same       the shown name IS the claimed firm (legal-form, truncation, initials, spelling, Devanagari variants)
             -> wrong answer = "discrepancy" (a FALSE accusation); "lookalike" sends it to review (a milder error)
  different  an unrelated business                -> should be "discrepancy" (a "match" would clear a mule: worst error)
  lookalike  a shell reusing the brand word        -> should be "lookalike" or "unverified", never "match"
  unknown    personal names and payment gateways   -> should be "unverified" (we cannot tell; we must not accuse)

LIMIT: bench/names/name_pairs.csv was written by Claude C (fictional firms) AFTER the matcher, so it is a specification
check, not a blind test. A blind version written by teammates goes in data/blind/name_pairs_blind.csv (same columns).
"""
from __future__ import annotations

import argparse
import csv
import json
import math
from collections import Counter, defaultdict
from pathlib import Path

from match import match_names

HERE = Path(__file__).resolve().parent


def wilson(k: int, n: int, z: float = 1.96) -> list[float] | None:
    if n == 0:
        return None
    p = k / n
    d = 1 + z * z / n
    c = (p + z * z / (2 * n)) / d
    h = z * math.sqrt(p * (1 - p) / n + z * z / (4 * n * n)) / d
    return [round(max(0.0, c - h), 3), round(min(1.0, c + h), 3)]


GOOD = {"same": {"match", "unverified"}, "different": {"discrepancy"}, "lookalike": {"lookalike", "unverified"},
        "unknown": {"unverified"}}


def evaluate(pairs_path: Path) -> dict:
    rows = list(csv.DictReader(open(pairs_path, encoding="utf-8")))
    by_rel: dict[str, Counter] = defaultdict(Counter)
    by_kind: dict[str, Counter] = defaultdict(Counter)
    errors = []
    for r in rows:
        v, why = match_names(r["claimed_firm"], r["shown_name"])
        by_rel[r["relation"]][v] += 1
        ok = v in GOOD[r["relation"]]
        by_kind[f"{r['relation']}: {r['kind']}"]["ok" if ok else "wrong"] += 1
        if not ok:
            errors.append({**r, "verdict": v, "reason": why})
    same, diff = by_rel["same"], by_rel["different"]
    n_same, n_diff = sum(same.values()), sum(diff.values())
    out = {
        "pairs": len(rows), "file": str(pairs_path.name),
        "false_discrepancy_on_same_entity": {"count": same["discrepancy"], "of": n_same,
                                             "rate": round(same["discrepancy"] / n_same, 3) if n_same else None,
                                             "wilson95": wilson(same["discrepancy"], n_same)},
        "same_entity_sent_to_review_as_lookalike": {"count": same["lookalike"], "of": n_same},
        "discrepancy_found_on_unrelated_business": {"count": diff["discrepancy"], "of": n_diff,
                                                    "rate": round(diff["discrepancy"] / n_diff, 3) if n_diff else None,
                                                    "wilson95": wilson(diff["discrepancy"], n_diff)},
        "dangerous_match_on_not_same": sum(by_rel[k]["match"] for k in ("different", "lookalike", "unknown")),
        "verdicts_by_relation": {k: dict(v) for k, v in sorted(by_rel.items())},
        "by_kind": {k: dict(v) for k, v in sorted(by_kind.items())},
        "errors": errors,
        "limit": "pairs written by the team after the matcher (specification check, not blind); fictional firms",
    }
    return out


def main(argv=None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--pairs", default=str(HERE / "name_pairs.csv"))
    ap.add_argument("--out", default=str(HERE / "results.json"))
    a = ap.parse_args(argv)
    r = evaluate(Path(a.pairs))
    Path(a.out).parent.mkdir(parents=True, exist_ok=True)
    with open(a.out, "w", encoding="utf-8", newline="\n") as f:
        f.write(json.dumps(r, indent=1, ensure_ascii=False))
    fd, dd = r["false_discrepancy_on_same_entity"], r["discrepancy_found_on_unrelated_business"]
    print(f"{r['pairs']} pairs. False discrepancy on same-entity names: {fd['count']}/{fd['of']} (95% CI {fd['wilson95']}). "
          f"Unrelated businesses caught: {dd['count']}/{dd['of']} ({dd['wilson95']}). "
          f"'match' given to a name that is not the firm: {r['dangerous_match_on_not_same']}.")
    for e in r["errors"]:
        print(f"  WRONG [{e['relation']}/{e['kind']}] {e['claimed_firm']!r} vs {e['shown_name']!r} -> {e['verdict']}: {e['reason']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
