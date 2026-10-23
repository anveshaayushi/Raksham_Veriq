"""Runs the app code against test doubles of Claude B's 23 Oct files (partial core/schemas.py, voice/stub.py)."""
import json
import os
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
FAKE = Path(__file__).resolve().parent / "fake_b"

SCRIPT = r"""
import json
from datetime import date
from app.contracts import ORIGIN, SCHEMA_SOURCE, VoiceResult
from app.adapters import voice as va
from app.case import UserCheck, build_case, load_demo
out = {"origin": ORIGIN, "source": SCHEMA_SOURCE, "voice_type": VoiceResult.__module__}
for sid in "ABC":
    fx = load_demo(sid)
    checks = {k: UserCheck(v[0], v[1], date.fromisoformat(fx["as_of"])) for k, v in fx["checks"].items()}
    c = build_case(case_id="t", chat_text=fx["chat"], claimed_firm=fx["claimed_firm"], checks=checks, transcripts=fx["transcripts"], fixture=fx)
    out[sid] = {"result": c.case_result(), "voice": [(v.state, v.model_version, v.file_id) for v in c.voice], "display": [va.score_display(v) for v in c.voice]}
vr, stub = va.analyse("x.opus", b"OggS", "x.opus")
out["upload"] = [vr.state, stub, list(vr.reasons)]
print(json.dumps(out))
"""


def run_with_fake_b():
    env = {**os.environ, "PYTHONPATH": os.pathsep.join([str(FAKE), str(ROOT)])}
    r = subprocess.run([sys.executable, "-c", SCRIPT], cwd=ROOT, env=env, capture_output=True, text=True, timeout=60)
    assert r.returncode == 0, r.stderr
    return json.loads(r.stdout)


def test_partial_core_schemas_is_merged_per_type():
    out = run_with_fake_b()
    assert out["origin"]["VoiceResult"] == "core.schemas" and out["origin"]["Decision"] == "provisional"
    assert out["voice_type"] == "core.schemas" and "PROVISIONAL for" in out["source"]


def test_demos_use_claude_b_stub_and_never_show_a_score():
    out = run_with_fake_b()
    assert out["A"]["voice"][0][1] == "voice-stub-b" and out["A"]["voice"][0][2] == "PTT-20261005-WA0012.opus"
    assert all("no score shown" in d for sid in "ABC" for d in out[sid]["display"])
    assert out["A"]["result"] == "NAME_DISCREPANCY" and out["B"]["result"] == "NO_MAJOR_ISSUE" and out["C"]["result"] == "INCONCLUSIVE"


def test_upload_without_analyse_entry_point_is_cant_assess():
    out = run_with_fake_b()
    state, is_stub, reasons = out["upload"]
    assert state == "cant_assess" and is_stub and "no analyse() entry point" in reasons[0]


def test_fixture_results_dropped_when_voice_state_disagrees(monkeypatch):
    from datetime import date

    from app.adapters import voice as va
    from app.case import UserCheck, build_case, load_demo
    from app.contracts import VoiceResult

    fx = load_demo("B")
    monkeypatch.setattr(va, "demo_stub", lambda s, f: VoiceResult(file_id=f, state="flagged", score=None, threshold=None,
                                                                    speech_seconds=5.0, reasons=("x",), model_version="b"))
    checks = {k: UserCheck(v[0], v[1], date.fromisoformat(fx["as_of"])) for k, v in fx["checks"].items()}
    c = build_case(case_id="t", chat_text=fx["chat"], claimed_firm=fx["claimed_firm"], checks=checks, transcripts=fx["transcripts"], fixture=fx)
    assert c.case_result() == "INCONCLUSIVE" and c.decisions[0].rule_id == "STUB-NO-ENGINE"
