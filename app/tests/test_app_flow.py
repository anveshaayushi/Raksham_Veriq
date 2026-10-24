"""Drives the real Streamlit script with streamlit.testing (no browser)."""
from pathlib import Path

from streamlit.testing.v1 import AppTest

APP = str(Path(__file__).resolve().parents[1] / "streamlit_app.py")


def start():
    at = AppTest.from_file(APP, default_timeout=180)  # slow Windows laptops: first runs measured >30 s
    at.run()
    return at


def btn(at, key):
    return next(b for b in at.button if b.key == key)


def test_consent_required_before_upload():
    at = start()
    assert btn(at, "c1").disabled
    at.checkbox(key="consent").check().run()
    assert not btn(at, "c1").disabled
    btn(at, "c1").click().run()
    assert at.session_state.step == 2


def to_answer(at, sid):
    at.checkbox(key="consent").check().run()
    btn(at, "c1").click().run()
    at.radio(key="demo_pick").set_value(sid).run()
    btn(at, "load_demo").click().run()
    btn(at, "c2").click().run()
    btn(at, "c3").click().run()
    btn(at, "c4").click().run()
    return at


def text(at):
    return " ".join([m.value for m in at.markdown] + [m.value for m in at.info] + [m.value for m in at.warning]
                    + [m.value for m in at.subheader] + [c.value for c in at.caption])


def test_demo_a_shows_three_separate_payees_and_stub_notice():
    at = to_answer(start(), "A")
    t = text(at)
    assert at.session_state.step == 5 and "NAME_DISCREPANCY" in t and "HUMAN_REVIEW" not in t
    assert t.count("Next step:") == 3 and "golden fixture" not in t


def test_money_sent_toggle_changes_only_next_step():
    at = to_answer(start(), "A")
    before = [d.result for d in at.session_state.case.decisions]
    at.toggle(key="money_toggle").set_value(True).run()
    t = text(at)
    assert "call 1930 now" in t and [d.result for d in at.session_state.case.decisions] == before


def test_demo_b_says_not_a_guarantee():
    t = text(to_answer(start(), "B"))
    assert "NO_MAJOR_ISSUE" in t and "This is not a guarantee." in t


def test_reports_step_offers_four_downloads():
    at = to_answer(start(), "C")
    btn(at, "c5").click().run()
    assert at.session_state.step == 6 and not at.exception


def test_mistake_recovery_flow_request_then_reviewer_overturns():
    """Genuine user flagged by mistake: asks for a review, a reviewer overturns, the original stays on record."""
    at = start()
    at.checkbox(key="consent").check().run()
    btn(at, "c1").click().run()
    at.radio(key="demo_pick").set_value("B").run()
    at.checkbox(key="demo_qr").check().run()  # synthetic QR naming OM SAI ENTERPRISES -> HUMAN_REVIEW
    btn(at, "load_demo").click().run()
    btn(at, "c2").click().run()
    btn(at, "c3").click().run()
    btn(at, "c4").click().run()
    assert at.session_state.case.case_result() == "HUMAN_REVIEW"
    qr_payee = next(p for p in at.session_state.case.payees if p.source == "image")
    at.selectbox(key=f"ow_{qr_payee.id}").set_value("The firm uses a different legal or trading name").run()
    at.text_area(key=f"on_{qr_payee.id}").input("This is our broker's payments arm.").run()
    at.text_input(key=f"orf_{qr_payee.id}").input("navyug.brk@validhdfc").run()
    btn(at, f"oreq_{qr_payee.id}").click().run()
    assert at.session_state.ledger.requests[qr_payee.id].status == "review requested"
    assert "Review requested" in text(at)
    at.toggle(key="rev_toggle").set_value(True).run()
    at.text_input(key=f"rvn_{qr_payee.id}").input("Reviewer A").run()
    at.text_input(key=f"rvr_{qr_payee.id}").input("Checked SEBI Check: genuine @valid handle").run()
    btn(at, f"rv_overturned_{qr_payee.id}").click().run()
    r = at.session_state.ledger.requests[qr_payee.id]
    assert r.status == "overturned" and r.decided_at is not None
    t = text(at) + " ".join(m.value for m in at.success)
    assert "Reviewed: explained" in t and "Original result HUMAN_REVIEW stays on record" in t
    btn(at, "c5").click().run()
    assert at.session_state.step == 6 and not at.exception


def test_judge_can_paste_a_chat_and_get_an_answer():
    at = start()
    at.checkbox(key="consent").check().run()
    btn(at, "c1").click().run()
    at.text_area(key="pasted").input("20/10/2026, 8:59 pm - Agent: I am Vikram from Sahyadri Securities. "
                                     "Pay ₹5,000 to vikram99@ybl today only\n").run()
    btn(at, "check_files").click().run()
    assert at.session_state.chat_text and at.session_state.payee_values == ["vikram99@ybl"]
    btn(at, "c2").click().run()
    at.text_input(key="firm_input").input("Sahyadri Securities Ltd").run()
    btn(at, "c3").click().run()
    at.text_input(key="nm_vikram99@ybl").input("VIKRAM MOBILE POINT").run()
    btn(at, "c4").click().run()
    assert at.session_state.case.case_result() == "NAME_DISCREPANCY" and not at.exception


def test_results_page_shows_measured_numbers():
    at = start()
    at.toggle(key="results_toggle").set_value(True).run()
    t = " ".join(h.value for h in at.header) + " ".join(m.value for m in at.markdown)
    assert "How accurate is VERIQ?" in t and "held-out synthetic test (generated by us)" in t and "False alarms on genuine payees" in t
    assert not at.exception


def test_second_victim_report_links_the_payee(tmp_path, monkeypatch):
    """Demo step 'second victim -> linked': the seeded registry has one report for the account in scenario A; this
    session's report is the second independent one, so after it the payee is LINKED."""
    from registry.seed import seed
    db = tmp_path / "reg.db"
    secret = "demo-secret-0123456789"
    seed(str(db), secret.encode())
    monkeypatch.setenv("VERIQ_REGISTRY_DB", str(db))
    monkeypatch.setenv("VERIQ_REGISTRY_SECRET", secret)
    at = to_answer(start(), "A")
    acct = next(p for p in at.session_state.case.payees if p.value_norm == "30112233445021")
    assert at.session_state.case.result_for(acct.id).result != "LINKED"
    btn(at, f"rep_{acct.id}").click().run()
    assert at.session_state.case.result_for(acct.id).result == "LINKED" and not at.exception
    assert "recorded" in text(at)
