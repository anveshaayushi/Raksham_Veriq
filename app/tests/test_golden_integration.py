"""The app's COMPUTED answers (parser -> extractor -> evidence -> rules.decide) against the golden fixtures.
Result and rule_id must match exactly; cited evidence must match by (lane, class) because the app numbers its own
evidence. tests/engine/ checks decide() on the fixtures' own evidence with exact evidence ids."""
import pytest

from app.adapters.extract import _stub, payees
from app.case import FIXTURES, UserCheck, build_case, demo_inputs, load_demo, report_data
from app.next_steps import NOT_A_GUARANTEE, with_money_sent
from report.build import filing_sheet_html, filing_sheet_md, summary_html, summary_md

SIDS = list(FIXTURES)


def demo_case(sid):
    fx = load_demo(sid)
    di = demo_inputs(fx)
    checks = {k: UserCheck(v["name"], v["source"], v["date"]) for k, v in di["checks"].items()}
    return fx, build_case(case_id=di["case_id"], chat_text=di["chat_text"], claimed_firm=di["claimed_firm"], checks=checks,
                          transcripts=di["transcripts"], fixture=fx)


@pytest.mark.parametrize("sid", SIDS)
def test_app_shows_the_golden_decisions(sid):
    fx, c = demo_case(sid)
    exp = {d["payee_id"]: d for d in fx["expected"]["decisions"]}
    assert c.case_result() == fx["expected"]["case_result"]["result"]
    assert {p.id for p in c.payees} == set(exp)
    for p in c.payees:
        d = c.result_for(p.id)
        assert d.result == exp[p.id]["result"] and d.rule_id == exp[p.id]["rule_id"]
        got = sorted((e.lane, e.class_) for e in c.evidence if e.evidence_id in d.evidence_ids)
        want = sorted((e["lane"], e["class"]) for e in fx["expected"]["evidence"] if e["evidence_id"] in exp[p.id]["evidence_ids"])
        assert got == want
    assert not c.bundle.is_stub and "rules/" in c.bundle.source


@pytest.mark.parametrize("sid", SIDS)
def test_money_sent_variant(sid):
    fx, c = demo_case(sid)
    var = fx["expected"]["variants"]["money_already_sent_true"]
    for d in c.decisions:
        d2 = with_money_sent(d, True)  # A's schema re-validates on replace()
        assert d2.result == d.result and d2.rule_id == d.rule_id and d2.evidence_ids == d.evidence_ids
        for phrase in var["next_step_must_contain"]:
            assert phrase in d2.next_step


@pytest.mark.parametrize("sid", SIDS)
def test_engine_extraction_equals_golden_and_stub_agrees_except_firm_names(sid):
    fx, c = demo_case(sid)
    e = fx["expected"]
    assert [m.to_dict() for m in c.extraction.messages] == e["messages"]
    assert [i.to_dict() for i in c.extraction.indicators] == e["indicators"]
    assert sorted((x.msg_id, x.type, x.severity) for x in c.extraction.cues) == \
        sorted((x["msg_id"], x["type"], x["severity"]) for x in e["cues"])
    di = demo_inputs(fx)
    st = _stub(di["chat_text"], di["case_id"], di["transcripts"])
    want = {(i.type, i.value_norm) for i in c.extraction.indicators if i.type != "firm_name"}
    assert want == {(i.type, i.value_norm) for i in st.indicators}
    assert [p.value_norm for p in payees(st.indicators)] == [p.value_norm for p in c.payees]


@pytest.mark.parametrize("typed,result", [
    ("SURESH KUMAR", "INCONCLUSIVE"),            # personal-looking name: unverified, never an accusation
    ("GLOBAL TECH TRADERS", "NAME_DISCREPANCY"),  # an unrelated business name
    ("NAVYUG BROKING LTD", "NO_MAJOR_ISSUE"),     # same firm, different legal suffix
    ("Razorpay Software Pvt Ltd", "INCONCLUSIVE"),  # payment gateway: merchant not visible
])
def test_judge_can_vary_the_demo_and_the_engine_recomputes(typed, result):
    fx = load_demo("B")
    di = demo_inputs(fx)
    checks = {k: UserCheck(typed, v["source"], v["date"]) for k, v in di["checks"].items()}
    c = build_case(case_id=di["case_id"], chat_text=di["chat_text"], claimed_firm=di["claimed_firm"], checks=checks,
                   transcripts=di["transcripts"], fixture=fx)
    assert c.case_result() == result


@pytest.mark.parametrize("sid", SIDS)
def test_reports_for_golden_cases(sid):
    fx, c = demo_case(sid)
    for money in (False, True):
        d = report_data(c, money_sent=money)
        outs = [summary_md(d), summary_html(d), filing_sheet_md(d), filing_sheet_html(d)]
        for out in outs:
            plain = out.replace("\\", "")
            assert "VERIQ files no complaints, blocks nothing and contacts no one." in plain
            for stub_number in ("0.12", "0.08", "0.50", "0.5)"):
                assert stub_number not in plain  # stub voice numbers are never quoted
        if fx["expected"]["case_result"]["result"] == "NO_MAJOR_ISSUE":
            assert all(NOT_A_GUARANTEE in o.replace("\\", "") for o in outs)
    if sid == "A":
        assert "30112233445021" not in summary_md(report_data(c, money_sent=False)).replace("\\", "")
        assert "30112233445021" in filing_sheet_md(report_data(c, money_sent=False))


def test_case_level_evidence_is_reported():
    fx, c = demo_case("B")
    assert [e.lane for e in c.case_level_evidence()] == ["registration", "voice"]
    d = report_data(c, money_sent=False)
    assert "whole case" in summary_md(d) and "B_ankit" in d.case_id
