"""voice.transcribe with a FAKE model: proves the plumbing, never-raises behaviour and temp cleanup. Not speech-to-text accuracy."""
from types import SimpleNamespace

import pytest

from voice import transcribe as T


class FakeModel:
    def __init__(self, text="paisa abhi bhejo", lang="hi", prob=0.9, raises=False):
        self.text, self.lang, self.prob, self.raises, self.seen = text, lang, prob, raises, []

    def transcribe(self, path, **kw):
        self.seen.append((path, kw))
        if self.raises:
            raise RuntimeError("boom")
        segs = [SimpleNamespace(text=" " + w + " ") for w in self.text.split()] if self.text else []
        return iter(segs), SimpleNamespace(language=self.lang, language_probability=self.prob)


@pytest.fixture(autouse=True)
def _reset():
    yield
    T.reset_model()


def test_happy_path_returns_text_and_language():
    m = FakeModel()
    T.set_model(m, "fake:1")
    r = T.transcribe("a.opus", b"x" * 100, "a.opus")
    assert (r.text, r.language, r.error, r.file_id, r.model) == ("paisa abhi bhejo", "hi", None, "a.opus", "fake:1")
    assert m.seen[0][1]["vad_filter"] is True


def test_temp_file_is_deleted():
    m = FakeModel()
    T.set_model(m)
    T.transcribe("a", b"x" * 100, "a.wav")
    from pathlib import Path
    assert not Path(m.seen[0][0]).exists()


@pytest.mark.parametrize("bad", [b"", None, "text", 12], ids=["empty", "none", "str", "int"])
def test_bad_input_never_raises(bad):
    T.set_model(FakeModel())
    r = T.transcribe("x", bad, "x.wav")
    assert r.text == "" and r.error


def test_model_unavailable_degrades_with_reason():
    T.set_model(None, "faster-whisper:small", error="ImportError: no module")
    r = T.transcribe("x", b"abc", "x.wav")
    assert r.text == "" and "speech_to_text_unavailable" in r.error


def test_model_exception_is_caught():
    T.set_model(FakeModel(raises=True))
    r = T.transcribe("x", b"abc", "x.wav")
    assert r.text == "" and r.error.startswith("transcription_failed")


def test_blank_file_id_and_silence():
    T.set_model(FakeModel(text=""))
    r = T.transcribe("  ", b"abc", "x.wav")
    assert r.file_id == "unknown-file" and r.text == "" and r.error is None


def test_language_override_from_env(monkeypatch):
    m = FakeModel()
    T.set_model(m)
    monkeypatch.setenv("VERIQ_WHISPER_LANGUAGE", "hi")
    T.transcribe("x", b"abc", "x.wav")
    assert m.seen[0][1]["language"] == "hi"


def test_retry_with_ffmpeg_decoded_audio_when_the_model_cannot_read_the_file(tmp_path, monkeypatch):
    """25 Oct fix for the laptop's 0/6 TypeError: first call (file path) fails, the retry gets a numpy array."""
    import numpy as np

    class PathFails(FakeModel):
        def transcribe(self, audio, **kw):
            self.seen.append((audio, kw))
            if isinstance(audio, str):
                raise TypeError("decode failed inside the model")
            return super().transcribe("array", **kw)

    import voice.audio as A
    monkeypatch.setattr(A, "decode_to_mono16k", lambda p, **k: np.zeros(16000, dtype=np.float32))
    m = PathFails(text="paisa bhejo")
    T.set_model(m, "fake:retry")
    r = T.transcribe("v.opus", b"x" * 100, "v.opus")
    assert r.text == "paisa bhejo" and r.error is None
    assert isinstance(m.seen[1][0], np.ndarray) and "vad_filter" not in m.seen[1][1]


def test_both_attempts_failing_keeps_the_error_message():
    class Always(FakeModel):
        def transcribe(self, audio, **kw):
            raise TypeError("bad argument xyz")

    T.set_model(Always(), "fake:fail")
    r = T.transcribe("v.wav", b"x" * 100, "v.wav")
    assert r.text == "" and "bad argument xyz" in r.error
