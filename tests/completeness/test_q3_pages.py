"""C-33 and the other Q3 pages, driven through the real Streamlit script (streamlit.testing, no browser)."""
from __future__ import annotations

from pathlib import Path

from streamlit.testing.v1 import AppTest

APP = str(Path(__file__).resolve().parents[2] / "app" / "streamlit_app.py")


def open_page(name: str) -> AppTest:
    at = AppTest.from_file(APP, default_timeout=180)
    at.run()
    at.radio(key="page_radio").set_value(name).run()
    assert not at.exception, at.exception
    return at


def text(at) -> str:
    return " ".join([m.value for m in at.markdown] + [h.value for h in at.header] + [h.value for h in at.subheader]
                    + [x.value for x in at.success] + [x.value for x in at.info])


def btn(at, key):
    return next(b for b in at.button if b.key == key)


def test_scenario_player_plays_and_scenario_d_is_cleared_by_review():
    at = open_page("Scenario player")
    at.radio(key="pl_sid").set_value("D").run()
    assert "Message 1 of 4" in " ".join(c.value for c in at.caption)
    btn(at, "pl_all").click().run()
    assert "NAME_DISCREPANCY" in text(at)  # the false alarm, computed live
    btn(at, "pl_req").click().run()
    assert "Review requested" in text(at)
    btn(at, "pl_over").click().run()
    assert "Overturned by the reviewer" in text(at) and not at.exception
    btn(at, "pl_replay").click().run()
    assert "Message 1 of 4" in " ".join(c.value for c in at.caption)


def test_player_recomputes_after_an_edit():
    at = open_page("Scenario player")
    at.radio(key="pl_sid").set_value("D").run()
    btn(at, "pl_all").click().run()
    at.radio(key="pl_nm_D_sslcap.sec@validicici").set_value("firm").run()
    assert "NO_MAJOR_ISSUE" in text(at)  # the bank app shows the firm's own name: no major issue (not a guarantee)
    at.radio(key="pl_sid").set_value("A").run()
    btn(at, "pl_all").click().run()
    assert "NAME_DISCREPANCY" in text(at)
    ta = at.text_area(key="pl_chat_edit_A")
    ta.set_value(ta.value.replace("ramesh.k@upi", "fresh.mule@ybl")).run()
    assert "fresh.mule@ybl" in text(at) or any("fresh.mule@ybl" in r.label for r in at.radio)


def test_plan_privacy_and_kit_pages_render():
    at = open_page("Plan vs delivered")
    assert "Plan versus delivered" in text(at) and at.dataframe
    at = open_page("Privacy proof")
    btn(at, "priv_reg").click().run()
    assert not at.exception and "not found" in str([j.value for j in at.json])
    btn(at, "priv_delete").click().run()
    assert not at.exception
    at = open_page("Kit runner (judges)")
    assert "Kit runner" in text(at)


def test_results_page_has_cross_dataset_table_and_evasion_lab():
    at = AppTest.from_file(APP, default_timeout=180)
    at.run()
    at.toggle(key="results_toggle").set_value(True).run()
    t = text(at)
    assert "ASVspoof 2019 LA" in t and "Evasion lab" in t and "switched off by default" in t
    at.text_input(key="evade_text").set_value("gu@r@nteed 3x returns").run()
    assert "guaranteed_return" in text(at) and not at.exception
