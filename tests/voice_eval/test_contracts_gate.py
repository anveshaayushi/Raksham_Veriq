import dataclasses

import numpy as np
import pytest

from core.schemas import MediaResult, VoiceResult
from voice.gate import GateConfig, run_gate
from voice.stub import stub_result

from helpers import SR, speechlike


def test_voiceresult_fields_match_brief_contract():
    names = [f.name for f in dataclasses.fields(VoiceResult)]
    assert names == ["file_id", "state", "score", "threshold", "speech_seconds", "reasons", "model_version"]


def test_mediaresult_fields_match_brief_contract():
    names = [f.name for f in dataclasses.fields(MediaResult)]
    assert names == ["file_id", "modality", "state", "score", "threshold", "components", "reasons", "model_version"]


def test_invalid_state_rejected():
    with pytest.raises(ValueError):
        VoiceResult("f", "fake", None, None, 0.0, ["x"], "m")
    with pytest.raises(ValueError):
        MediaResult("f", "audio", "real", None, None, [], [], "m")


def test_contract_requires_score_and_threshold_for_flagged_and_no_signal():
    # A's strict contract: guards against us ever emitting a half-filled decision
    for st in ("flagged", "no_signal"):
        with pytest.raises(ValueError):
            VoiceResult("f", st, None, None, 1.0, ["x"], "m")
        with pytest.raises(ValueError):
            VoiceResult("f", st, 0.5, None, 1.0, ["x"], "m")
    with pytest.raises(ValueError):
        VoiceResult("f", "cant_assess", None, None, 0.0, [], "m")  # needs a reason


def test_stubs_valid_under_contract_and_labelled_placeholders():
    for s in ("A", "B", "C", "FLAGGED"):
        r = stub_result(s)  # constructing it already validated it under A's contract
        assert "stub" in r.model_version.lower()
        assert any("stub" in x.lower() for x in r.reasons)
        assert VoiceResult.from_dict(r.to_dict()) == r
    assert stub_result("A").state == "no_signal" and stub_result("A").threshold is not None
    assert stub_result("C").state == "cant_assess"
    assert stub_result("flagged").state == "flagged"
    assert stub_result("flagged", file_id="x.opus").file_id == "x.opus"
    with pytest.raises(ValueError):
        stub_result("Z")


def test_gate_passes_speechlike_clip():
    g = run_gate(speechlike(5.0))
    assert g.passed, g.reasons
    assert g.speech_s >= 1.0


def test_gate_rejects_short_silent_clipped_long():
    assert "too_short" in run_gate(speechlike(0.4)).reasons[0]
    sil = run_gate(np.zeros(SR * 3, dtype=np.float32))
    assert not sil.passed and "silent" in sil.reasons
    clipped = (np.sign(speechlike(5.0)) * 1.0).astype(np.float32)
    assert any(r.startswith("clipping") for r in run_gate(clipped).reasons)
    longc = run_gate(speechlike(10.0), GateConfig(max_duration_s=5.0))
    assert any(r.startswith("exceeds_max_duration") for r in longc.reasons)
    assert run_gate(np.zeros(0, dtype=np.float32)).reasons == ["empty_audio"]


def test_gate_constant_hum_is_not_speech():
    t = np.arange(SR * 4) / SR
    hum = (0.2 * np.sin(2 * np.pi * 100 * t)).astype(np.float32)
    g = run_gate(hum)
    assert not g.passed
    assert any(r.startswith("speech_below_min") for r in g.reasons)
