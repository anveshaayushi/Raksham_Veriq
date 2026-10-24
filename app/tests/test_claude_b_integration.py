"""Runs the app with a test double of Claude B's voice/ package (stub_result only, no analyse()), on Claude A's contract."""
import json
import os
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
FAKE = Path(__file__).resolve().parent / "fake_b"

SCRIPT = r"""
import json
from app.contracts import SCHEMA_SOURCE
from app.adapters import voice as va
from app.case import UserCheck, build_case, demo_inputs, load_demo
out = {"source": SCHEMA_SOURCE}
for sid in "ABC":
    fx = load_demo(sid); di = demo_inputs(fx)
    checks = {k: UserCheck(v["name"], v["source"], v["date"]) for k, v in di["checks"].items()}
    c = build_case(case_id=di["case_id"], chat_text=di["chat_text"], claimed_firm=di["claimed_firm"], checks=checks,
                   transcripts=di["transcripts"], fixture=fx)
    out[sid] = {"result": c.case_result(), "voice": [(v.state, v.model_version, v.file_id) for v in c.voice],
                "display": [va.score_display(v) for v in c.voice], "golden": "golden fixture" in c.bundle.source}
vr, stub = va.analyse("x.opus", b"OggS", "x.opus")
out["upload"] = [vr.state, stub, list(vr.reasons)]
print(json.dumps(out))
"""


def run_with_fake_b():
    env = {**os.environ, "PYTHONPATH": os.pathsep.join([str(FAKE), str(ROOT)])}
    r = subprocess.run([sys.executable, "-c", SCRIPT], cwd=ROOT, env=env, capture_output=True, text=True, timeout=60)
    assert r.returncode == 0, r.stderr
    return json.loads(r.stdout)


def test_shared_contract_is_claude_a_core():
    assert run_with_fake_b()["source"] == "core.schemas (shared contract)"


def test_demos_use_claude_b_stub_when_valid_and_never_show_a_score():
    out = run_with_fake_b()
    assert out["A"]["voice"][0][1] == "voice-stub-b"            # B's stub used, file id set to the demo's voice note
    assert out["A"]["voice"][0][2] != "stub-A"
    assert out["B"]["voice"][0][1] != "voice-stub-b"            # B's stub broke A's contract: fixture voice used instead
    assert all("no score shown" in d for sid in "ABC" for d in out[sid]["display"])
    assert (out["A"]["result"], out["B"]["result"], out["C"]["result"]) == ("NAME_DISCREPANCY", "NO_MAJOR_ISSUE", "INCONCLUSIVE")
    assert not any(out[s]["golden"] for s in "ABC")  # computed by the engine, not replayed


def test_upload_without_analyse_entry_point_is_cant_assess():
    state, is_stub, reasons = run_with_fake_b()["upload"]
    assert state == "cant_assess" and is_stub and "no analyse() entry point" in reasons[0]


def test_flagged_voice_turns_a_clean_demo_into_human_review(monkeypatch):
    from app.adapters import voice as va
    from app.case import UserCheck, build_case, demo_inputs, load_demo
    from app.contracts import VoiceResult

    fx = load_demo("B")
    di = demo_inputs(fx)
    monkeypatch.setattr(va, "demo_stub", lambda s, f: VoiceResult(file_id=f, state="flagged", score=0.9, threshold=0.5,
                                                                    speech_seconds=5.0, reasons=["x"], model_version="b"))
    checks = {k: UserCheck(v["name"], v["source"], v["date"]) for k, v in di["checks"].items()}
    c = build_case(case_id=di["case_id"], chat_text=di["chat_text"], claimed_firm=di["claimed_firm"], checks=checks,
                   transcripts=di["transcripts"], fixture=fx)
    assert c.case_result() == "HUMAN_REVIEW" and c.decisions[0].rule_id == "REVIEW"  # a flag can only add caution
