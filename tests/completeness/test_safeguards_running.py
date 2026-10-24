"""Rubric 'alert and response' and 'responsible AI': the safeguards RUN (not just described).
- no raw chat text or audio is left on disk after a full check through the real app
- offline mode: the app works with every outgoing connection blocked
- delete-my-data clears the session
- the alert says why it fired and offers actions (do not pay, verify the name, ask for review, report pack)"""
from __future__ import annotations

import os
import tempfile
import time
from pathlib import Path

from streamlit.testing.v1 import AppTest

ROOT = Path(__file__).resolve().parents[2]
APP = str(ROOT / "app" / "streamlit_app.py")
MARKER = "zqx" + __import__("uuid").uuid4().hex[:10]  # made at run time, so no file can contain it beforehand


def btn(at, key):
    return next(b for b in at.button if b.key == key)


def run_paste_flow(extra_env=None):
    old = {k: os.environ.get(k) for k in (extra_env or {})}
    os.environ.update(extra_env or {})
    try:
        at = AppTest.from_file(APP, default_timeout=180)
        at.run()
        at.checkbox(key="consent").check().run()
        btn(at, "c1").click().run()
        at.text_area(key="pasted").input(f"20/10/2026, 8:59 pm - Agent: {MARKER} here from Sahyadri Securities. "
                                         "Pay ₹5,000 to vikram99@ybl today only\n").run()
        btn(at, "check_files").click().run()
        btn(at, "c2").click().run()
        at.text_input(key="firm_input").input("Sahyadri Securities Ltd").run()
        btn(at, "c3").click().run()
        at.text_input(key="nm_vikram99@ybl").input("VIKRAM MOBILE POINT").run()
        btn(at, "c4").click().run()
        return at
    finally:
        for k, v in old.items():
            if v is None:
                os.environ.pop(k, None)
            else:
                os.environ[k] = v


def _files_touched_since(root: Path, t0: float):
    for dp, dns, fns in os.walk(root):
        dns[:] = [d for d in dns if d not in (".git", "__pycache__", ".pytest_cache", ".venv", "external")]
        for fn in fns:
            p = Path(dp) / fn
            try:
                if p.stat().st_mtime >= t0 - 1:
                    yield p
            except OSError:
                pass


def test_no_raw_chat_or_audio_left_on_disk_after_a_full_check():
    t0 = time.time()
    at = run_paste_flow()
    assert at.session_state.case.case_result() == "NAME_DISCREPANCY"
    leaks = []
    for root in (Path(tempfile.gettempdir()), ROOT):
        for p in _files_touched_since(root, t0):
            try:
                if p.stat().st_size < 50_000_000 and MARKER.encode() in p.read_bytes():
                    leaks.append(str(p))
            except OSError:
                pass
    assert leaks == []
    assert not [p for p in Path(tempfile.gettempdir()).glob("veriq_voice_*")]


def test_offline_mode_full_check_makes_no_outgoing_connection():
    from app import config
    config.blocked.clear()
    try:
        at = run_paste_flow({"VERIQ_OFFLINE": "1"})
        assert at.session_state.case.case_result() == "NAME_DISCREPANCY" and not at.exception
        assert config.blocked == []
    finally:
        config.unblock_network()


def test_alert_says_why_and_offers_actions_and_delete_my_data_clears_everything():
    at = run_paste_flow()
    text = " ".join(m.value for m in at.markdown)
    assert "Why this alert fired" in text and "VIKRAM MOBILE POINT" in text
    keys = {b.key for b in at.button}
    assert {"act_nopay", "act_verify", "act_genuine"} <= keys
    assert any(d.key == "act_pack" for d in at.get("download_button"))
    btn(at, "act_nopay").click().run()
    assert "You decided not to pay for now." in " ".join(s.value for s in at.success)
    btn(at, "reset").click().run()
    assert "case" not in at.session_state and "chat_text" not in at.session_state
