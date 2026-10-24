"""VERIQ's trained voice head (app/adapters/voice_head.py): runs through Claude B's Detector/Calibration interfaces."""
import json

import numpy as np
import pytest

from app.adapters import voice_head as vh


class FakeBase:
    model_version = json.loads(vh.HEAD.read_text())["base_model_version"]
    chunk_samples = 64600


def test_head_files_match_and_load_without_torch():
    det, cal = vh.load_head(FakeBase(), embed_fn=lambda chunks: np.zeros((len(chunks), 160)))
    assert cal.model_version == det.model_version and det.native_polarity == "higher_is_fake"
    assert cal.polarity == "higher_is_fake" and 0 < cal.threshold < 1 and cal.target_false_alarm == 0.05
    s = det.score_chunks([np.zeros(64600, dtype=np.float32)] * 2)
    assert len(s) == 2 and all(0 < v < 1 for v in s)


def test_head_refuses_a_different_base_model():
    class Other(FakeBase):
        model_version = "aasist-pretrained@000000000000"
    with pytest.raises(ValueError, match="calibration is for"):
        vh.load_head(Other(), embed_fn=lambda c: np.zeros((len(c), 160)))


def test_flag_is_only_a_review_cue_through_b_pipeline(tmp_path):
    """With a head that always says 'fake', B's pipeline returns 'flagged' (never more), and the rules turn a
    flag into HUMAN_REVIEW at most."""
    from voice import service
    det, cal = vh.load_head(FakeBase(), embed_fn=lambda c: np.zeros((len(c), 160)))
    det._b = 50.0  # force probability ~1
    service.set_backend(det, cal)
    try:
        sr = 16000
        t = np.arange(sr * 4) / sr
        x = (0.2 * np.sin(2 * np.pi * 180 * t) * (1 + 0.5 * np.sin(2 * np.pi * 3 * t))).astype(np.float32)
        import io
        import wave  # standard library: no extra dependency (Q0 clean-install fix)
        buf = io.BytesIO()
        with wave.open(buf, "wb") as w:
            w.setnchannels(1)
            w.setsampwidth(2)
            w.setframerate(sr)
            w.writeframes((x * 32767).astype("<i2").tobytes())
        vr = service.analyse("v.wav", buf.getvalue(), "v.wav")
        assert vr.state in ("flagged", "cant_assess") and vr.file_id == "v.wav"
    finally:
        service.reset_backend()
