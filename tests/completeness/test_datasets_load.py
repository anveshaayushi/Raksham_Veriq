"""Part A: load-only checks of the blind datasets find malformed rows and wrong counts (nothing is scored)."""
from __future__ import annotations

import csv
import json

from bench import datasets as D


def test_blind_ai_loader_joins_and_reports_problems(tmp_path):
    root = tmp_path / "blind_ai"
    root.mkdir()
    rows = [["file", "label", "claimed_firm", "bank_app_names"]]
    ext = []
    for i in range(80):
        f = f"c{i:02d}.txt"
        (root / f).write_text("13/10/2026, 6:02 pm - A: hi\n", encoding="utf-8")
        rows.append([f, "scam" if i < 40 else "genuine", "Firm", f"a{i}@upi=SHOP {i}; 1234567890{i % 10}=X"])
        ext.append({"file": f, "language": "en"})
    with open(root / "labels.csv", "w", newline="", encoding="utf-8") as fh:
        csv.writer(fh).writerows(rows)
    (root / "labels_extended.json").write_text(json.dumps(ext), encoding="utf-8")
    items, problems = D.load_blind_ai(root)
    assert len(items) == 80 and problems == []
    assert items[0]["bank_app_names_parsed"] == {"a0@upi": "SHOP 0", "12345678900": "X"} and items[0]["extended"]["language"] == "en"
    rows[1][1] = "maybe"
    rows[2][3] = "no-equals-sign"
    rows[3][0] = "missing.txt"
    with open(root / "labels.csv", "w", newline="", encoding="utf-8") as fh:
        csv.writer(fh).writerows(rows)
    _, problems = D.load_blind_ai(root)
    text = " ".join(problems)
    assert "not scam/genuine" in text and "without 'identifier=NAME'" in text and "not found" in text and "expected 80" in text


def test_other_loaders_and_missing_sets(tmp_path):
    p = tmp_path / "pairs.csv"
    with open(p, "w", newline="") as fh:
        w = csv.writer(fh)
        w.writerow(["claimed_firm", "shown_name", "relation"])
        for rel, n in (("same_entity", 70), ("different_entity", 70), ("lookalike_of_different_entity", 30), ("cannot_tell", 30)):
            w.writerows([["F", "S", rel]] * n)
    assert D.load_names_blind(p)[1] == []
    e = tmp_path / "cases.jsonl"
    e.write_text("\n".join([json.dumps({"id": "x", "text": "pay x@upi", "expected": {"payees": [{"kind": "upi", "value": "x@upi"}]}})] * 60
                           + [json.dumps({"id": "y", "text": "hello", "expected": {"payees": [], "should_not_extract": ["123"]}})] * 40 + ["{bad"]))
    items, problems = D.load_extract_blind(e)
    assert len(items) == 100 and any("not JSON" in x for x in problems)
    assert D.load_voice_scripts(tmp_path / "none")[1][0].startswith("missing")
    r = D.check_all()
    assert set(r) == {"blind_ai", "names_blind", "extract_blind", "voice_scripts"}


def test_payment_link_identifiers_with_equals_sign_are_parsed():
    names, bad = D.parse_bank_app_names("https://fees.x.test/pay?inv=2291=PAYSPHERE SCHOOL COLLECT;a@upi=SHOP")
    assert bad == [] and names == {"https://fees.x.test/pay?inv=2291": "PAYSPHERE SCHOOL COLLECT", "a@upi": "SHOP"}


def test_the_committed_ai_generated_set_loads_cleanly():
    import pytest
    items, problems = D.load_blind_ai()
    if not items:
        pytest.skip("data/blind_ai not present")
    assert len(items) == 80 and problems == []

