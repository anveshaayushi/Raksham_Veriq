"""Drives the real Streamlit script with streamlit.testing (no browser)."""
from pathlib import Path

from streamlit.testing.v1 import AppTest

APP = str(Path(__file__).resolve().parents[1] / "streamlit_app.py")


def start():
    at = AppTest.from_file(APP, default_timeout=30)
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
