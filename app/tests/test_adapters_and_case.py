from datetime import date

from app.adapters import decide as decide_adapter
from app.adapters import voice as voice_adapter
from app.case import UserCheck, build_case, demo_inputs, load_demo, report_data
from app.contracts import evidence_class

UPLOAD = ("20/10/2026, 8:59 pm - Agent: I am Vikram from Sahyadri Securities. Pay ₹5,000 to vikram99@ybl\n"
          "21/10/2026, 9:05 am - Agent: Now pay ₹9,000 to A/c 123456789012 IFSC HDFC0004321 today only\n")


def upload_case(checks=None):
    return build_case(case_id="u1", chat_text=UPLOAD, claimed_firm="Sahyadri Securities Pvt Ltd", checks=checks or {})


def test_upload_is_computed_by_the_engine_and_inconclusive_without_name_checks():
    c = upload_case()
    assert c.case_result() == "INCONCLUSIVE" and [d.rule_id for d in c.decisions] == ["INCONCL", "INCONCL"]
    assert all(any("No class A evidence" in r for r in d.reasons) for d in c.decisions)
    assert not c.bundle.is_stub and "rules/" in c.bundle.source


def test_upload_without_engine_falls_back_to_the_labelled_stub(monkeypatch):
    import app.case as case_mod
    monkeypatch.setattr(case_mod, "engine_available", lambda: False)
    import rules
    monkeypatch.delattr(rules, "decide")
    c = upload_case()
    assert c.case_result() == "INCONCLUSIVE" and all(decide_adapter.STUB_REASON in d.reasons for d in c.decisions)
    assert "STUB" in c.bundle.source and c.bundle.is_stub


def test_payees_stay_separate_with_own_amounts():
    c = upload_case()
    assert [p.value_norm for p in c.payees] == ["vikram99@ybl", "123456789012"]
    assert [c.amounts[p.id] for p in c.payees] == ["₹5,000", "₹9,000"]


def test_user_reported_evidence_is_class_a_and_labelled():
    c = upload_case({"vikram99@ybl": UserCheck("VIKRAM TRADERS", "UPI app (payee name before paying)", date(2026, 10, 21))})
    e = c.evidence[0]
    assert evidence_class(e) == "A" and e.lane == "payee_name" and "user-reported" in e.source
    assert c.decisions[0].result == "NAME_DISCREPANCY" and c.decisions[0].evidence_ids == [e.evidence_id]
    assert c.decisions[1].result == "INCONCLUSIVE"


def test_voice_stub_never_returns_no_signal():
    vr, is_stub = voice_adapter.analyse("v.opus", b"OggS....", "v.opus")
    assert vr.state == "cant_assess" and vr.score is None  # real voice.analyse() now exists, so is_stub is False (CR-B1)


def test_voice_referenced_but_not_uploaded_is_cant_assess():
    c = build_case(case_id="u2", chat_text="20/10/2026, 8:59 pm - A: PTT-1.opus (file attached)\n", claimed_firm="X", checks={})
    assert [v.state for v in c.voice] == ["cant_assess"]


def test_scores_and_stub_numbers_are_hidden():
    from app.contracts import VoiceResult
    real = VoiceResult(file_id="f", state="no_signal", score=1.2, threshold=0.5, speech_seconds=3.0, reasons=[], model_version="aasist-cal-v1")
    stub = VoiceResult(file_id="f", state="no_signal", score=0.12, threshold=0.5, speech_seconds=3.0, reasons=[], model_version="stub-fixture-v0")
    assert "1.2" in voice_adapter.score_display(real) and "0.12" not in voice_adapter.score_display(stub)
    assert "0.12" not in voice_adapter.observed_for_display("voice", "no_signal (stub score 0.12 vs stub threshold 0.50)")
    assert voice_adapter.observed_for_display("payee_name", "X (2)") == "X (2)"


def test_report_data_keeps_blanks_blank():
    fx = load_demo("A")
    di = demo_inputs(fx)
    c = build_case(case_id=di["case_id"], chat_text=di["chat_text"], claimed_firm=di["claimed_firm"],
                   checks={k: UserCheck(v["name"], v["source"], v["date"]) for k, v in di["checks"].items()},
                   transcripts=di["transcripts"], fixture=fx)
    data = report_data(c, money_sent=True)
    assert data.complainant_mobile == "" and all(p.utr == "" and p.paid_on == "" for p in data.payees)
    assert all("1930" in p.next_step for p in data.payees)
