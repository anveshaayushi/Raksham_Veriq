"""Golden tests: the sync mechanism between Claude A, B and C.

`pytest tests/golden` must pass on every merge. If your module changes behaviour
on a golden fixture, update the fixture on purpose and say why.
"""
import copy
import json
import pathlib

import pytest

from core import schemas as S
from core.validate import validate_fixture, validate_reference

FIX = pathlib.Path(__file__).resolve().parents[2] / "fixtures"
FILES = sorted(FIX.glob("scenario_*.json"))
EXPECTED_CASE = {
    "A_meera": "NAME_DISCREPANCY",
    "B_ankit": "NO_MAJOR_ISSUE",
    "C_priya": "INCONCLUSIVE",
}


def load(path):
    return json.loads(path.read_text(encoding="utf-8"))


@pytest.fixture(params=FILES, ids=lambda p: p.stem)
def fx(request):
    return load(request.param)


# ---------------------------------------------------------------- fixtures valid
def test_three_scenarios_present():
    assert {load(p)["fixture_id"] for p in FILES} == set(EXPECTED_CASE)


def test_fixture_is_valid(fx):
    assert validate_fixture(fx) == []


def test_expected_case_result(fx):
    assert fx["expected"]["case_result"]["result"] == EXPECTED_CASE[fx["fixture_id"]]


def test_reference_snapshot_valid():
    for p in (FIX / "reference").glob("*.json"):
        assert validate_reference(p) == []


def test_scenario_a_shows_rank_and_rotation():
    """A has a REG_CONFLICT-worthy fact AND name discrepancies; the higher rank (R2) must win."""
    a = load(FIX / "scenario_A_suspicious.json")["expected"]
    assert any(e["lane"] == "registration" for e in a["evidence"])
    assert {d["result"] for d in a["decisions"]} == {"NAME_DISCREPANCY"}
    assert len([i for i in a["indicators"] if i["type"] in ("upi_vpa", "bank_account")]) == 3


def test_no_video_anywhere(fx):
    assert all(m["kind"] != "video" for m in fx["expected"]["messages"])


def test_b_clear_includes_disclaimer(fx):
    for d in fx["expected"]["decisions"]:
        if d["result"] == "NO_MAJOR_ISSUE":
            assert S.NOT_A_GUARANTEE in d["next_step"]


def test_voice_never_cited_to_clear(fx):
    ev = {e["evidence_id"]: e for e in fx["expected"]["evidence"]}
    for d in fx["expected"]["decisions"]:
        if d["result"] == "NO_MAJOR_ISSUE":
            assert all(ev[i]["class"] != "E" for i in d["evidence_ids"])


# ------------------------------------------------- validator can actually fail
def _mutated(fx, fn):
    d = copy.deepcopy(fx)
    fn(d)
    return validate_fixture(d)


def test_validator_catches_bad_span(fx):
    def f(d):
        d["expected"]["indicators"][0]["span"] = [0, 3]
    assert any("value_raw" in e for e in _mutated(fx, f))


def test_validator_catches_missing_evidence(fx):
    def f(d):
        d["expected"]["decisions"][0]["evidence_ids"] = ["nope"]
    assert _mutated(fx, f)


def test_validator_catches_wrong_case_result(fx):
    def f(d):
        d["expected"]["case_result"]["result"] = "HUMAN_REVIEW"
        d["expected"]["case_result"]["rule_id"] = "REVIEW"
    assert any("case_result" in e or "worst" in e for e in _mutated(fx, f))


def test_validator_catches_chat_text_drift(fx):
    def f(d):
        d["input"]["chat_txt"] = d["input"]["chat_txt"].replace("Meera", "Mira").replace("Ankit", "Anil").replace("Priya", "Pria")
    assert _mutated(fx, f)


def test_validator_catches_decision_on_class_d_only():
    a = load(FIX / "scenario_A_suspicious.json")
    def f(d):
        # point the discrepancy at registry (class C) evidence only
        d["expected"]["decisions"][0]["evidence_ids"] = ["A_meera-E6"]
    assert any("NAME_DISCREPANCY needs class A" in e for e in _mutated(a, f))


# --------------------------------------------------------------- schema strictness
def test_roundtrip_all_objects(fx):
    e = fx["expected"]
    for cls, key in ((S.Message, "messages"), (S.Indicator, "indicators"), (S.Cue, "cues"),
                     (S.VoiceResult, "voice_results"), (S.Evidence, "evidence"), (S.Decision, "decisions")):
        for raw in e[key]:
            assert cls.from_dict(raw).to_dict() == raw


def test_evidence_json_key_is_class_not_class_underscore():
    raw = load(FILES[0])["expected"]["evidence"][0]
    assert "class" in raw and "class_" not in raw
    with pytest.raises(S.SchemaError):
        S.Evidence.from_dict({**{k: v for k, v in raw.items() if k != "class"}, "class_": "A"})


def test_unknown_and_missing_fields_rejected():
    raw = load(FILES[0])["expected"]["cues"][0]
    with pytest.raises(S.SchemaError):
        S.Cue.from_dict({**raw, "extra": 1})
    with pytest.raises(S.SchemaError):
        S.Cue.from_dict({k: v for k, v in raw.items() if k != "severity"})


def test_no_major_issue_requires_disclaimer():
    with pytest.raises(S.SchemaError):
        S.Decision("p", "NO_MAJOR_ISSUE", "CLEAR", ["r"], ["e"], "All fine.")


def test_decision_rule_must_match_result():
    with pytest.raises(S.SchemaError):
        S.Decision("p", "NAME_DISCREPANCY", "CLEAR", ["r"], ["e"], "x")


def test_class_a_name_needs_user_reported_label():
    with pytest.raises(S.SchemaError):
        S.Evidence("e", "p", "payee_name", "A", "c", "o", "bank app", "2026-10-23", "l")


def test_voice_and_registry_class_locked():
    with pytest.raises(S.SchemaError):
        S.Evidence("e", "p", "voice", "A", "c", "o", "s", "2026-10-23", "l")
    with pytest.raises(S.SchemaError):
        S.Evidence("e", "p", "registry", "B", "c", "o", "s", "2026-10-23", "l")


def test_video_rejected():
    with pytest.raises(S.SchemaError):
        S.Message(1, "2026-10-23T10:00:00+05:30", "x", "video", "", "v.mp4")
    with pytest.raises(S.SchemaError):
        S.MediaResult("f", "video", "cant_assess", None, None, [], ["unsupported"], "m")


def test_voice_result_state_rules():
    with pytest.raises(S.SchemaError):
        S.VoiceResult("f", "no_signal", None, None, 3.0, [], "m")      # needs a score
    with pytest.raises(S.SchemaError):
        S.VoiceResult("f", "cant_assess", None, None, 0.2, [], "m")    # needs a reason
    assert S.VoiceResult("f", "cant_assess", None, None, 0.2, ["too_little_speech"], "m")


def test_bad_span_and_date_rejected():
    with pytest.raises(S.SchemaError):
        S.Indicator("i", "c", 1, "upi_vpa", "a@b", "a@b", "text", "high", [5, 5])
    with pytest.raises(S.SchemaError):
        S.Evidence("e", "p", "registration", "B", "c", "o", "s", "23-10-2026", "l")


def test_media_result_roundtrip_with_components():
    raw = {"file_id": "x.png", "modality": "image", "state": "cant_assess", "score": None, "threshold": None,
           "components": [{"name": "ocr", "state": "cant_assess", "score": None}],
           "reasons": ["unreadable"], "model_version": "stub"}
    assert S.MediaResult.from_dict(raw).to_dict() == raw


def test_rank_table_matches_brief():
    order = sorted(S.RESULT_RANK, key=S.RESULT_RANK.get)
    assert order == ["LINKED", "NAME_DISCREPANCY", "REGISTRATION_CONFLICT",
                     "HUMAN_REVIEW", "INCONCLUSIVE", "NO_MAJOR_ISSUE"]
