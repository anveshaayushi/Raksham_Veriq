"""Q2 evaluation scripts on small mock inputs: name pairs, SMS cue check, blind-set runner (run-once guard)."""
from __future__ import annotations

import csv
import json
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]


def test_name_pair_set_results_match_the_committed_file(tmp_path):
    from bench.names.run import main
    out = tmp_path / "n.json"
    assert main(["--out", str(out)]) == 0
    r = json.loads(out.read_text(encoding="utf-8"))
    committed = json.loads((ROOT / "bench" / "names" / "results.json").read_text(encoding="utf-8"))
    assert {k: r[k] for k in ("false_discrepancy_on_same_entity", "discrepancy_found_on_unrelated_business",
                              "dangerous_match_on_not_same")} == \
           {k: committed[k] for k in ("false_discrepancy_on_same_entity", "discrepancy_found_on_unrelated_business",
                                      "dangerous_match_on_not_same")}
    assert r["dangerous_match_on_not_same"] == 0  # a name that is not the firm is never called a match


def test_sms_cue_check_on_a_mock_file(tmp_path):
    from bench.sms.run import main
    f = tmp_path / "SMSSpamCollection"
    f.write_text("ham\tOk see you at 5\nham\tSend me the OTP you got\nspam\tURGENT! Claim your guaranteed prize now\n"
                 "junk line without a tab\n", encoding="utf-8")
    out = tmp_path / "s.json"
    assert main(["--data", str(f), "--out", str(out)]) == 0
    r = json.loads(out.read_text())
    assert r["messages"] == 3 and r["n"] == {"ham": 2, "spam": 1}
    assert r["ham_hard_cue"]["count"] == 1 and r["ham_hard_cue_examples"][0]["cues"] == ["otp_pin_request"]
    assert main(["--data", str(tmp_path / "missing"), "--out", str(out)]) == 2


def test_blind_runner_counts_outcomes_and_runs_only_once(tmp_path):
    from bench.blind.run import main, parse_names
    d = tmp_path / "blind"
    d.mkdir()
    (d / "a_01.txt").write_text("13/10/2026, 6:02 pm - Ravi: Sir pay ₹20,000 to ravi.k@okaxis today only, guaranteed 3x\n",
                                encoding="utf-8")
    (d / "a_02.txt").write_text("14/10/2026, 10:00 am - Desk: Please add funds to aarohan.sec@icici for your account\n",
                                encoding="utf-8")
    (d / "a_03.txt").write_text("no timestamps here at all\n", encoding="utf-8")
    with open(d / "labels.csv", "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerows([["file", "label", "claimed_firm", "bank_app_names"],
                     ["a_01.txt", "scam", "Navyug Capital", "ravi.k@okaxis=RAVI KUMAR STORES"],
                     ["a_02.txt", "genuine", "Aarohan Securities", "aarohan.sec@icici=AAROHAN SECURITIES PVT LTD"],
                     ["a_03.txt", "scam", "X Ltd", ""], ["missing.txt", "genuine", "Y", ""]])
    out = tmp_path / "b.json"
    assert main(["--data", str(d), "--out", str(out)]) == 0
    r = json.loads(out.read_text(encoding="utf-8"))
    assert r["chats"] == 4 and r["scam_warned"]["count"] == 1 and r["genuine_false_alarm"]["count"] == 0
    assert r["outcomes"]["genuine: clear"] == 1 and r["outcomes"]["scam: no answer"] == 1
    assert main(["--data", str(d), "--out", str(out)]) == 3  # second run refused
    assert main(["--data", str(d), "--out", str(out), "--force"]) == 0 and out.with_suffix(".previous.json").is_file()
    assert main(["--data", str(tmp_path / "none"), "--out", str(out)]) == 2
    assert parse_names("A@x = N1 ; 1234 5678 9=N2;bad") == {"a@x": "N1", "123456789": "N2"}


def _rows(tmp_path, run, polarity):
    import sys
    sys.path.insert(0, str(ROOT / "scripts"))
    import make_results_rows as MR
    out = tmp_path / "rows.md"
    assert MR.main(["--run", run, "--polarity", polarity, "--command", "x", "--out", str(out)]) == 0
    return out.read_text(encoding="utf-8")


def test_asvspoof_rows_recompute_from_the_committed_predictions(tmp_path):
    """C-29: B's ASVspoof numbers are re-derived from the committed prediction CSVs (no model, no audio needed)."""
    md = _rows(tmp_path, f"eval:{ROOT / 'results/asvspoof/asv_eval.csv'}", "higher_is_real")
    assert "| eval | n=600 (real 300, fake 300) | AUC 0.766 | EER 0.317 | genuine flagged 0.157 [0.120, 0.202]" in md


def test_head_cross_dataset_rows_recompute_and_head_is_off_by_default(tmp_path, monkeypatch):
    """C-30: the head's cross-dataset collapse is re-derived from its committed predictions, and the app keeps it off."""
    md = _rows(tmp_path, f"x:{ROOT / 'results/asvspoof/head_v1_eval.csv'}", "higher_is_fake")
    assert "AUC 0.457 | EER 0.527 | genuine flagged 0.540 [0.483, 0.596]" in md
    from app.adapters import voice_head as vh
    monkeypatch.delenv("VERIQ_VOICE_HEAD", raising=False)
    monkeypatch.setattr(vh, "_state", {"tried": False, "active": False, "reason": ""})
    assert vh.ensure_installed()["active"] is False
