"""Core paths that earlier tests did not reach (Q1 test completeness): the fixture validator rejecting broken
fixtures, the contract fallback, the registry seed command and failure modes, QR edge cases, chat date handling."""
from __future__ import annotations

import copy
import importlib.util
import json
import runpy
import sqlite3
import sys
import types
from pathlib import Path

import pytest

from core import validate as V

ROOT = Path(__file__).resolve().parents[2]
FIX_A = json.loads((ROOT / "fixtures" / "scenario_A_suspicious.json").read_text(encoding="utf-8"))
pytestmark = pytest.mark.filterwarnings("ignore:.*found in sys.modules:RuntimeWarning")


# ------------------------------------------------------------------ fixture validator ----
def _ev(d, eid):
    return next(e for e in d["expected"]["evidence"] if e["evidence_id"] == eid)


def _dec(d, pid):
    return next(x for x in d["expected"]["decisions"] if x["payee_id"] == pid)


def _set_result(d, pid, result, evidence_ids=None):
    """Change a decision's result consistently (rule id and wording), so only the evidence rule is broken."""
    from core.schemas import NOT_A_GUARANTEE, RESULT_TO_RULE
    x = _dec(d, pid)
    x.update(result=result, rule_id=RESULT_TO_RULE[result])
    if result == "NO_MAJOR_ISSUE":
        x["next_step"] = "Proceed with care. " + NOT_A_GUARANTEE
    if evidence_ids is not None:
        x["evidence_ids"] = evidence_ids


BREAKS = {
    "not synthetic": (lambda d: d.update(synthetic=False), "synthetic=true"),
    "extra top key": (lambda d: d.update(extra=1), "top-level keys differ"),
    "missing expected key": (lambda d: d["expected"].pop("variants"), "expected keys differ"),
    "chat line edited": (lambda d: d["input"].update(chat_txt=d["input"]["chat_txt"].replace("Meera", "Mira")),
                         "not found in chat_txt"),
    "transcript differs": (lambda d: d["input"]["transcripts"].update({k: "changed" for k in d["input"]["transcripts"]}),
                           "must equal transcripts"),
    "messages out of order": (lambda d: d["expected"]["messages"].reverse(), "ascending msg_id"),
    "span points elsewhere": (lambda d: d["expected"]["indicators"][2].update(span=[0, 3]), "!= value_raw"),
    "indicator on unknown message": (lambda d: d["expected"]["indicators"][2].update(msg_id=99), "does not exist"),
    "voice indicator marked high confidence": (lambda d: d["expected"]["indicators"][3].update(confidence="high"),
                                               "must not be confidence=high"),
    "ifsc malformed": (lambda d: d["expected"]["indicators"][5].update(value_norm="HDFC123"), "ifsc value_norm"),
    "amount on a non-payee": (lambda d: d["expected"]["amounts"][0].update(payee_id="A_meera-I1"),
                              "is not a payee indicator"),
    "cue excerpt not in text": (lambda d: d["expected"]["cues"][0].update(excerpt="not in the chat"),
                                "excerpt not found"),
    "voice result missing": (lambda d: d["expected"]["voice_results"].clear(), "voice_results file_ids"),
    "duplicate evidence id": (lambda d: d["expected"]["evidence"].append(copy.deepcopy(d["expected"]["evidence"][0])),
                              "duplicate evidence_id"),
    "user check name differs from class A evidence": (lambda d: d["user_checks"][0].update(observed_name="OTHER"),
                                                      "class A payee_name evidence"),
    "decision cites unknown evidence": (lambda d: _dec(d, "A_meera-I3").update(evidence_ids=["A_meera-E99"]),
                                        "cites unknown evidence"),
    "name discrepancy decided on class D": (lambda d: _ev(d, "A_meera-E1").update({"class": "D"}),
                                            "NAME_DISCREPANCY needs class A"),
    "voice model clears a payee": (lambda d: _set_result(d, "A_meera-I4", "NO_MAJOR_ISSUE", ["A_meera-E2", "A_meera-E5"]),
                                   "model output (class E) must not be cited"),
    "linked without registry evidence": (lambda d: _set_result(d, "A_meera-I3", "LINKED"),
                                         "LINKED needs class C"),
    "registry stub disagrees": (lambda d: d["registry_stub"].update({"A_meera-I3": "linked"}), "is linked but"),
    "bad registry status": (lambda d: d["registry_stub"].update({"A_meera-I3": "maybe"}), "must be 'clean' or 'linked'"),
    "wrong case result": (lambda d: d["expected"]["case_result"].update(deciding_payee_id="A_meera-I5"),
                          "!= worst payee"),
    "money-sent variant missing 1930": (lambda d: d["expected"]["variants"]["money_already_sent_true"].update(
        next_step_must_contain=[]), "variants.money_already_sent_true"),
}


def test_valid_fixture_has_no_problems():
    assert V.validate_fixture(copy.deepcopy(FIX_A)) == []


@pytest.mark.parametrize("name", sorted(BREAKS))
def test_validator_rejects_each_broken_fixture(name):
    d = copy.deepcopy(FIX_A)
    fn, expected = BREAKS[name]
    fn(d)
    errs = V.validate_fixture(d)
    assert errs and any(expected in e for e in errs), errs


def test_validator_on_non_object_and_schema_error():
    assert V.validate_fixture([]) == ["fixture is not a JSON object"]
    d = copy.deepcopy(FIX_A)
    d["expected"]["messages"][0]["ts"] = "yesterday"
    assert V.validate_fixture(d)[0].startswith("schema:")


def test_validator_command(tmp_path, capsys, monkeypatch):
    assert V.main([]) == 0 and "ALL VALID" in capsys.readouterr().out
    bad = tmp_path / "bad.json"
    d = copy.deepcopy(FIX_A)
    d["synthetic"] = False
    bad.write_text(json.dumps(d), encoding="utf-8")
    assert V.main([str(bad)]) == 1 and "FAIL bad.json" in capsys.readouterr().out
    monkeypatch.setattr(V, "ROOT", tmp_path)
    assert V.main([]) == 1 and "no fixtures found" in capsys.readouterr().out


def test_reference_snapshot_must_be_marked_synthetic(tmp_path):
    p = tmp_path / "ref.json"
    p.write_text(json.dumps({"as_of": "2026-10-01", "source": "real list", "entries": []}))
    assert V.validate_reference(p) and "AssertionError" in V.validate_reference(p)[0]
    p.write_text(json.dumps({"as_of": "2026-10-01", "source": "SYNTHETIC", "entries": [{"reg_no": "X", "entity": "Y"}]}))
    assert V.validate_reference(p) == []


def test_reference_failure_is_reported_by_the_command(tmp_path, capsys, monkeypatch):
    (tmp_path / "fixtures" / "reference").mkdir(parents=True)
    (tmp_path / "fixtures" / "scenario_A.json").write_text(json.dumps(FIX_A), encoding="utf-8")
    (tmp_path / "fixtures" / "reference" / "r.json").write_text("{}")
    monkeypatch.setattr(V, "ROOT", tmp_path)
    assert V.main([]) == 1 and "FAIL reference/r.json" in capsys.readouterr().out


# ------------------------------------------------------------------ contract fallback ----
def _fresh_contracts():
    spec = importlib.util.spec_from_file_location("app._contracts_probe", ROOT / "app" / "contracts.py")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def test_contracts_say_when_they_fall_back(monkeypatch):
    import core.schemas as real
    monkeypatch.setitem(sys.modules, "core.schemas", None)  # core/schemas.py missing
    m = _fresh_contracts()
    assert m.PROVISIONAL and m.SCHEMA_SOURCE.startswith("PROVISIONAL") and set(m.ORIGIN.values()) == {"provisional"}
    partial = types.ModuleType("core.schemas")
    partial.Message = real.Message
    monkeypatch.setitem(sys.modules, "core.schemas", partial)
    import core
    monkeypatch.setattr(core, "schemas", partial)
    m = _fresh_contracts()
    assert m.SCHEMA_SOURCE.startswith("core.schemas for Message; PROVISIONAL for Indicator")


def test_contract_helpers_on_other_shapes():
    from app import contracts as C
    from app import _provisional_schemas as P
    assert C.evidence_class({"klass": "B"}) == "B" and C.evidence_class({}) is None
    assert C.class_kw(dict) == "evidence_class"  # not a dataclass: default name
    ev = C.from_json(P.Evidence, {"evidence_id": "E1", "payee_id": "CASE", "lane": "registration", "class": "B",
                                  "claimed": "x", "observed": "y", "source": "s", "as_of": "2026-10-24",
                                  "limitation": "l"})
    assert C.evidence_class(ev) == "B"
    assert C.to_dict({"a": 1}) == {"a": 1} and C.to_dict(ev)["evidence_id"] == "E1"

    class Pyd:
        def model_dump(self, by_alias):
            return {"by_alias": by_alias}

    assert C.to_dict(Pyd()) == {"by_alias": True}
    with pytest.raises(TypeError, match="cannot serialise"):
        C.to_dict(object())
    assert C.case_result([]) is None


# ------------------------------------------------------------------ registry seed and failures ----
def test_seed_command(tmp_path, monkeypatch, capsys):
    from registry import seed
    assert seed.main(["seed"]) == 2 and "Usage" in capsys.readouterr().out
    monkeypatch.delenv("VERIQ_REGISTRY_SECRET", raising=False)
    monkeypatch.delenv("VERIQ_REGISTRY_SECRET_FILE", raising=False)
    assert seed.main(["seed", str(tmp_path / "r.db")]) == 2 and "Set VERIQ_REGISTRY_SECRET" in capsys.readouterr().out
    monkeypatch.setenv("VERIQ_REGISTRY_SECRET", "test-secret-0123456789")
    db = tmp_path / "r.db"
    assert seed.main(["seed", str(db)]) == 0 and "6 synthetic reports" in capsys.readouterr().out
    from registry.sqlite_registry import SQLiteRegistry
    reg = SQLiteRegistry(db)
    assert reg.lookup("p", "upi_vpa", "sunita.t@upi").status == "linked"
    assert reg.lookup("p", "bank_account", "30112233445021").status == "clean"  # one reporter never links
    monkeypatch.setattr(sys, "argv", ["registry.seed"])
    with pytest.raises(SystemExit):
        runpy.run_module("registry.seed", run_name="__main__")


def test_secret_from_file_and_too_short(tmp_path, monkeypatch):
    from registry.sqlite_registry import load_secret
    monkeypatch.delenv("VERIQ_REGISTRY_SECRET", raising=False)
    f = tmp_path / "s.txt"
    f.write_text("file-secret-0123456789\n")
    monkeypatch.setenv("VERIQ_REGISTRY_SECRET_FILE", str(f))
    assert load_secret() == b"file-secret-0123456789"
    monkeypatch.setenv("VERIQ_REGISTRY_SECRET_FILE", str(tmp_path / "missing.txt"))
    assert load_secret() is None
    monkeypatch.setenv("VERIQ_REGISTRY_SECRET", "short")
    assert load_secret() is None


def test_registry_from_env(tmp_path, monkeypatch):
    from registry.sqlite_registry import SQLiteRegistry, create_db, from_env
    monkeypatch.delenv("VERIQ_REGISTRY_DB", raising=False)
    assert from_env() is None
    db = tmp_path / "r.db"
    create_db(db)
    monkeypatch.setenv("VERIQ_REGISTRY_DB", str(db))
    monkeypatch.setenv("VERIQ_REGISTRY_SECRET", "test-secret-0123456789")
    assert isinstance(from_env(), SQLiteRegistry)


def test_every_registry_call_says_unavailable_when_the_file_is_not_a_database(tmp_path):
    from registry.sqlite_registry import SQLiteRegistry
    bad = tmp_path / "not_a_db.db"
    bad.write_bytes(b"this is not sqlite" * 100)
    reg = SQLiteRegistry(bad, secret=b"test-secret-0123456789")
    assert reg.lookup("p", "upi_vpa", "a.b@upi").status == "unavailable"  # never "clean"
    assert reg.report("upi_vpa", "a.b@upi", "tok").status == "unavailable"
    assert reg.review("upi_vpa", "a.b@upi", "confirmed", "R").status == "unavailable"
    with pytest.raises(ValueError):
        reg.review("upi_vpa", "a.b@upi", "maybe", "R")
    assert reg.review("upi_vpa", "merchant@razorpay", "confirmed", "R").status == "excluded"


def test_registry_missing_file_is_unavailable_not_clean(tmp_path):
    from registry.sqlite_registry import SQLiteRegistry
    reg = SQLiteRegistry(tmp_path / "missing.db", secret=b"test-secret-0123456789")
    assert reg.lookup("p", "upi_vpa", "a.b@upi").status == "unavailable"
    assert reg.report("upi_vpa", "a.b@upi", "tok").status == "unavailable"
    assert reg.review("upi_vpa", "a.b@upi", "rejected", "R").status == "unavailable"


# ------------------------------------------------------------------ QR edge cases ----
def test_qr_without_opencv_finds_nothing(monkeypatch):
    from parsing import qr
    monkeypatch.setitem(sys.modules, "cv2", None)
    assert qr.decode_qr(b"\x89PNG anything") == []


def test_qr_in_a_huge_screenshot_and_cv2_errors(monkeypatch):
    cv2 = pytest.importorskip("cv2")
    import numpy as np
    from parsing import qr
    code = cv2.QRCodeEncoder.create().encode("upi://pay?pa=big.shot@ybl&pn=BIG")
    code = cv2.resize(code, (900, 900), interpolation=cv2.INTER_NEAREST)
    canvas = np.full((3000, 1600), 255, dtype=np.uint8)
    canvas[1000:1900, 300:1200] = code
    png = cv2.imencode(".png", canvas)[1].tobytes()
    assert qr.decode_qr(png) == ["upi://pay?pa=big.shot@ybl&pn=BIG"]  # downscaled to <= 2200 px first

    class Det:
        def detectAndDecodeMulti(self, img):
            raise cv2.error("boom")

        def detectAndDecode(self, img):
            raise cv2.error("boom")

    monkeypatch.setattr(cv2, "QRCodeDetector", Det)
    assert qr.decode_qr(png) == []


def test_upi_link_odd_fields():
    from parsing.qr import parse_upi
    u = parse_upi("Pay here: UPI://pay?PA=Shop.One@okaxis&PN=Shop+One&AM=abc")
    assert u["pa"] == "shop.one@okaxis" and u["pn"] == "Shop One" and u["am"] is None
    assert parse_upi(None) is None


# ------------------------------------------------------------------ chat dates ----
def test_us_style_and_ambiguous_dates_are_explained():
    from parsing import parse_chat_with_warnings
    us = "10/13/2026, 6:02 PM - Rahul: pay ramesh.k@upi\n10/14/2026, 9:00 AM - Rahul: now\n"
    msgs, w = parse_chat_with_warnings(us)
    assert msgs[0].ts.startswith("2026-10-13T18:02") and "month-first" in w[0]
    amb = "05/06/2026, 6:02 pm - Rahul: hello\n"
    msgs, w = parse_chat_with_warnings(amb)
    assert msgs[0].ts.startswith("2026-06-05") and "read day-first" in w[0]
    bad = "31/02/2026, 6:02 pm - Rahul: impossible date\n01/03/2026, 6:03 pm - Rahul: fine\n"
    msgs, w = parse_chat_with_warnings(bad)
    assert [m.text for m in msgs] == ["fine"] and any("Unreadable date" in x for x in w)


def test_locked_sqlite_is_detected_by_sqlite_itself(tmp_path):
    """Sanity check of the test method used in registry tests: an exclusive lock blocks other connections."""
    db = tmp_path / "x.db"
    a = sqlite3.connect(db)
    a.execute("CREATE TABLE t (x)")
    a.execute("BEGIN EXCLUSIVE")
    b = sqlite3.connect(db, timeout=0.05)
    with pytest.raises(sqlite3.OperationalError, match="locked"):
        b.execute("SELECT * FROM t").fetchall()
    a.rollback()
    a.close()
    b.close()
