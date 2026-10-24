"""C-39: pretrained AASIST + Claude B's ASVspoof-dev threshold as a WEAK review cue (Prompt 2, block B).
A flag only sends the payee to human review; 'no_signal' never clears a payee; VERIQ_VOICE_CALIBRATION=none abstains."""
from __future__ import annotations

import json
from pathlib import Path

import numpy as np

from app import config
from voice import service
from voice.calibration import load_calibration

ROOT = Path(__file__).resolve().parents[2]
CAL = ROOT / "results" / "asvspoof" / "calibration_asvspoof_dev.json"


class FixedAasist:
    """Stand-in with pretrained AASIST's interface (higher score = more real); returns a fixed raw logit."""
    name, chunk_samples, native_polarity = "aasist", 16000, "higher_is_real"
    model_version = json.loads(CAL.read_text())["model_version"]

    def __init__(self, score):
        self.score = score

    def score_chunks(self, chunks):
        return [self.score] * len(chunks)


def _case(score, names=None):
    from datetime import date
    from app.case import UserCheck, build_case
    service.set_backend(FixedAasist(score), load_calibration(CAL))
    try:
        clip = (ROOT / "app" / "demo_media" / "demo_voice_real_human.wav").read_bytes()
        chat = ("13/10/2026, 6:02 pm - Desk: Add funds to navyug.brk@validhdfc\n"
                "13/10/2026, 6:03 pm - Desk: PTT-1.wav (file attached)\n")
        checks = {k: UserCheck(v, "Bank app (beneficiary name)", date(2026, 10, 25)) for k, v in (names or {}).items()}
        return build_case(case_id="vc", chat_text=chat, claimed_firm="Navyug Broking Pvt Ltd", checks=checks,
                          audio={"PTT-1.wav": clip})
    finally:
        service.reset_backend()


def test_default_threshold_is_bs_asvspoof_dev_file_and_can_be_switched_off(monkeypatch):
    monkeypatch.delenv("VERIQ_VOICE_CALIBRATION", raising=False)
    assert config.voice_calibration_path() == str(CAL)
    cal = load_calibration(CAL)
    assert cal.polarity == "higher_is_real" and cal.threshold < 0 and cal.target_false_alarm == 0.05
    monkeypatch.setenv("VERIQ_VOICE_CALIBRATION", "none")
    assert config.voice_calibration_path() is None
    assert not (ROOT / "voice" / "calibration.json").exists()  # the file itself is never written


def test_flag_only_escalates_to_review():
    c = _case(-9.0, {"navyug.brk@validhdfc": "NAVYUG BROKING PVT LTD"})  # below threshold -> flagged
    assert [v.state for v in c.voice] == ["flagged"] and c.case_result() == "HUMAN_REVIEW"


def test_no_signal_never_clears_a_payee():
    c = _case(5.0)  # above threshold -> no_signal; no bank-app name check
    assert [v.state for v in c.voice] == ["no_signal"] and c.case_result() == "INCONCLUSIVE"
    c = _case(5.0, {"navyug.brk@validhdfc": "SHREE GANESH TRADERS"})
    assert c.case_result() == "NAME_DISCREPANCY"  # the voice result cannot soften a name discrepancy


def test_kit_tab_uses_the_threshold_when_the_model_loads(monkeypatch, tmp_path):
    import io
    import shutil
    import zipfile
    from app.views import kit
    import eval.cli as cli
    monkeypatch.setattr(cli, "build_detector", lambda args: (FixedAasist(-9.0), None))
    monkeypatch.delenv("VERIQ_VOICE_CALIBRATION", raising=False)
    b = io.BytesIO()
    with zipfile.ZipFile(b, "w") as z:
        z.write(ROOT / "app" / "demo_media" / "demo_voice_real_human.wav", "real/r.wav")
    out = kit.run_kit(b.getvalue())
    if shutil.which("ffmpeg"):
        assert ",flagged,fake," in out["csv"]
