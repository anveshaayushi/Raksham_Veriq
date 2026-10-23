from datetime import date

from app.adapters import decide as decide_adapter
from app.adapters import voice as voice_adapter
from app.case import UserCheck, build_case, load_demo, report_data
from app.contracts import get


def demo(sid, edit=None):
    fx = load_demo(sid)
    checks = {k: UserCheck(v[0], v[1], date.fromisoformat(fx["as_of"])) for k, v in fx["checks"].items()}
    if edit:
        edit(checks)
    return build_case(case_id=f"demo-{sid}", chat_text=fx["chat"], claimed_firm=fx["claimed_firm"], checks=checks,
                      transcripts=fx["transcripts"], fixture=fx)


def test_three_demo_fixtures_flow_and_are_labelled_stub():
    exp = {"A": "NAME_DISCREPANCY", "B": "NO_MAJOR_ISSUE", "C": "INCONCLUSIVE"}
    for sid, res in exp.items():
        c = demo(sid)
        assert c.case_result() == res and c.bundle.is_stub and "STUB" in c.bundle.source


def test_scenario_a_payees_stay_separate_with_own_results():
    c = demo("A")
    assert [get(c.result_for(p.id), "result") for p in c.payees] == ["HUMAN_REVIEW", "NAME_DISCREPANCY", "NAME_DISCREPANCY"]
    assert len({p.id for p in c.payees}) == 3


def test_changed_inputs_never_reuse_fixture_and_never_clear():
    def edit(ch):
        ch["navyug.brk@validhdfc"] = UserCheck("SOMEONE ELSE", "SEBI Check", date(2026, 10, 8))
    c = demo("B", edit)
    assert c.case_result() == "INCONCLUSIVE" and all(get(d, "rule_id") == decide_adapter.STUB_RULE for d in c.decisions)


def test_upload_without_engine_is_inconclusive_with_missing_evidence():
    fx = load_demo("B")
    c = build_case(case_id="u1", chat_text=fx["chat"], claimed_firm="Navyug Broking Ltd", checks={})
    d = c.decisions[0]
    assert get(d, "result") == "INCONCLUSIVE" and get(d, "evidence_ids") == () and any("missing evidence" in r for r in get(d, "reasons"))


def test_user_reported_evidence_is_class_a_and_labelled():
    c = demo("A")
    assert c.evidence and all(e.evidence_class == "A" and e.source.startswith("User-reported") for e in c.evidence)


def test_voice_stub_never_returns_no_signal():
    vr, is_stub = voice_adapter.analyse("v.opus", b"OggS....", "v.opus")
    assert is_stub and vr.state == "cant_assess" and vr.score is None


def test_voice_referenced_but_not_uploaded_is_cant_assess():
    fx = load_demo("A")
    c = build_case(case_id="u2", chat_text=fx["chat"], claimed_firm="X", checks={})
    assert [v.state for v in c.voice] == ["cant_assess"]


def test_report_data_keeps_blanks_blank():
    data = report_data(demo("A"), money_sent=True)
    assert data.complainant_mobile == "" and all(p.utr == "" and p.paid_on == "" for p in data.payees)
    assert all("1930" in p.next_step for p in data.payees)
    assert [p.result for p in data.payees] == ["HUMAN_REVIEW", "NAME_DISCREPANCY", "NAME_DISCREPANCY"]
