"""C-31: privacy proof. Delete-my-data empties the session and VERIQ's temp folders; a voice note leaves no file;
the registry file holds no raw identifiers."""
from __future__ import annotations

import io
import tempfile
import wave
from pathlib import Path

import numpy as np

from app.views import privacy as P


def _wav(seconds=2.0, sr=16000):
    t = np.arange(int(sr * seconds)) / sr
    x = (0.2 * np.sin(2 * np.pi * 200 * t)).astype(np.float32)
    b = io.BytesIO()
    with wave.open(b, "wb") as w:
        w.setnchannels(1)
        w.setsampwidth(2)
        w.setframerate(sr)
        w.writeframes((x * 32767).astype("<i2").tobytes())
    return b.getvalue()


def test_delete_my_data_empties_session_and_temp_folders():
    leftover = Path(tempfile.mkdtemp(prefix="veriq_voice_"))  # e.g. left by a crashed run
    (leftover / "clip.opus").write_bytes(b"OggS")
    S = {"intake": object(), "chat_text": "13/10/2026, 6:02 pm - X: pay ramesh.k@upi", "case": object(), "page": "x"}
    r = P.delete_everything(S)
    assert any("chat_text" in x for x in r["before"]["session"]) and leftover.name in r["before"]["temp_folders"]
    assert r["after"] == {"session": [], "temp_folders": []} and S == {} and not leftover.exists()


def test_voice_note_leaves_no_file_and_registry_has_no_raw_identifier():
    from app.case import build_case
    before = set(P.veriq_temp_folders())
    chat = "13/10/2026, 6:02 pm - Rahul: Pay ₹5,000 to ramesh.k@upi\n13/10/2026, 6:03 pm - Rahul: PTT-1.wav (file attached)\n"
    build_case(case_id="priv", chat_text=chat, claimed_firm="Navyug", checks={}, audio={"PTT-1.wav": _wav()})
    assert set(P.veriq_temp_folders()) == before  # the voice service deleted its temp folder
    reg = P.demo_registry_rows()
    assert reg["rows"] and not any(reg["raw_identifier_found_in_file"].values())
    assert all(len(r["indicator_hash"]) >= 32 for r in reg["rows"])
    assert not set(P.veriq_temp_folders()) - before  # the demo registry folder is gone too
