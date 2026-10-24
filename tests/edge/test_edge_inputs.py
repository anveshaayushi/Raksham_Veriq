"""Negative and edge inputs (Q1 item i). One test per edge case named in the organisers' checklist:
empty file, huge file, zip bomb, wrong encodings, no timestamps, mixed languages, 0-second audio, corrupt opus,
registry locked. Each checks the user-visible outcome: a clear refusal or an honest "can't assess", never a crash
and never a reassuring answer the evidence does not support."""
from __future__ import annotations

import io
import shutil
import sqlite3
import subprocess
import time
import wave
import zipfile
from datetime import date

import numpy as np
import pytest

from app.case import UserCheck, build_case
from app.intake import (MAX_AUDIO_BYTES, MAX_CHAT_BYTES, MAX_ZIP_MEMBERS, Intake, IntakeError, add_audio, add_chat,
                        add_image)
from voice import service

HAS_FFMPEG = shutil.which("ffmpeg") is not None
CHAT = "13/10/2026, 6:02 pm - Rahul: I am Rahul from Navyug Wealth. Pay ₹10,000 to ramesh.k@upi today\n"
FIRM = "Navyug Wealth Research Pvt Ltd"


def wav(seconds: float, sr=16000) -> bytes:
    n = int(sr * seconds)
    x = (0.2 * np.sin(2 * np.pi * 200 * np.arange(n) / sr)).astype(np.float32)
    b = io.BytesIO()
    with wave.open(b, "wb") as w:
        w.setnchannels(1)
        w.setsampwidth(2)
        w.setframerate(sr)
        w.writeframes((x * 32767).astype("<i2").tobytes())
    return b.getvalue()


@pytest.fixture(autouse=True)
def _no_model():
    service.set_backend(None, None, "no detector in this test")
    yield
    service.reset_backend()


# ------------------------------------------------------------------ 1. empty files ----
@pytest.mark.parametrize("adder,name", [(add_chat, "chat.txt"), (add_audio, "PTT-1.opus"), (add_image, "qr.png")],
                         ids=["chat", "audio", "image"])
def test_empty_file_is_refused_with_a_reason(adder, name):
    with pytest.raises(IntakeError, match="empty"):
        adder(Intake(), name, b"")


def test_empty_chat_text_gives_no_answer_not_a_clean_one():
    c = build_case(case_id="e", chat_text="", claimed_firm=FIRM, checks={})
    assert c.payees == [] and c.case_result() is None


# ------------------------------------------------------------------ 2. huge files ----
def test_oversize_chat_and_audio_are_refused():
    with pytest.raises(IntakeError, match="larger than"):
        add_chat(Intake(), "chat.txt", b"a" * (MAX_CHAT_BYTES + 1))
    with pytest.raises(IntakeError, match="larger than"):
        add_audio(Intake(), "PTT-1.opus", b"OggS" + b"\0" * MAX_AUDIO_BYTES)


def test_largest_allowed_chat_is_processed_in_reasonable_time():
    line = "14/10/2026, 10:11 am - Rahul: market update, nothing to pay here, just checking in with you\n"
    big = CHAT + line * ((MAX_CHAT_BYTES - 200) // len(line.encode()))
    assert len(big.encode()) <= MAX_CHAT_BYTES
    t0 = time.perf_counter()
    c = build_case(case_id="big", chat_text=big, claimed_firm=FIRM, checks={})
    assert [p.value_norm for p in c.payees] == ["ramesh.k@upi"]
    assert time.perf_counter() - t0 < 60  # ~20k messages; measured ~2-5 s on a laptop


# ------------------------------------------------------------------ 3. zip bombs ----
def _zip(members: dict, method=zipfile.ZIP_DEFLATED) -> bytes:
    b = io.BytesIO()
    with zipfile.ZipFile(b, "w", method) as z:
        for n, d in members.items():
            z.writestr(n, d)
    return b.getvalue()


@pytest.mark.parametrize("members,msg", [
    ({"chat.txt": CHAT, "bomb.txt": b"\0" * (20 * 1024 * 1024)}, "compression ratio"),
    ({f"f{i}.txt": "x" for i in range(MAX_ZIP_MEMBERS + 1)}, "more than"),
    ({"../../evil.txt": CHAT}, "unsafe file path"),
    ({"PTT-1.opus": b"OggS"}, "No chat .txt"),
], ids=["ratio_bomb", "too_many_members", "path_traversal", "no_chat_inside"])
def test_hostile_zip_is_refused(members, msg):
    with pytest.raises(IntakeError, match=msg):
        add_chat(Intake(), "WhatsApp Chat.zip", _zip(members))


def test_damaged_zip_is_refused():
    with pytest.raises(IntakeError, match="damaged"):
        add_chat(Intake(), "chat.zip", b"PK\x03\x04 truncated")


# ------------------------------------------------------------------ 4. encodings ----
@pytest.mark.parametrize("encoding", ["utf-8", "utf-8-sig", "utf-16"])
def test_supported_encodings_are_read(encoding):
    it = Intake()
    add_chat(it, "chat.txt", CHAT.encode(encoding))
    from app.intake import decode_text
    assert "ramesh.k@upi" in decode_text(it.chat.data)


@pytest.mark.parametrize("encoding", ["cp1252", "latin-1"])
def test_legacy_encodings_are_refused_with_a_fix(encoding):
    data = CHAT.replace("₹", "Rs ").replace("Rahul", "Raúl").encode(encoding)
    from app.intake import decode_text
    with pytest.raises(IntakeError, match="not UTF-8"):
        decode_text(data)


def test_binary_named_txt_is_refused():
    with pytest.raises(IntakeError, match="does not look like text"):
        add_chat(Intake(), "chat.txt", bytes(range(256)) * 10)


# ------------------------------------------------------------------ 5. no timestamps ----
def test_text_without_timestamps_is_explained_not_guessed():
    c = build_case(case_id="nt", chat_text="Rahul: pay 5000 to ramesh.k@upi now\nok\n", claimed_firm=FIRM, checks={})
    assert c.payees == [] and c.case_result() is None
    assert any("No dated WhatsApp messages" in w for w in c.extraction.warnings)


# ------------------------------------------------------------------ 6. mixed languages ----
def test_mixed_hindi_hinglish_english_chat():
    chat = ("13/10/2026, 6:02 pm - Rahul: नमस्ते जी, मैं Navyug Wealth से Rahul बोल रहा हूँ\n"
            "13/10/2026, 6:03 pm - Rahul: Bhai aaj hi ₹25,000 bhejo sunita.t@upi pe, slot cancel ho jayega\n"
            "13/10/2026, 6:04 pm - Rahul: Guaranteed 3x returns, no loss pakka\n"
            "13/10/2026, 6:05 pm - Rahul: खाता संख्या 30112233445021 में भी डाल सकते हो\n")
    checks = {"sunita.t@upi": UserCheck("SUNITA TRADERS", "UPI app (payee name before paying)", date(2026, 10, 24))}
    c = build_case(case_id="mix", chat_text=chat, claimed_firm=FIRM, checks=checks)
    assert {p.value_norm for p in c.payees} == {"sunita.t@upi", "30112233445021"}
    cues = {x.type for x in c.extraction.cues}
    assert {"urgency", "guaranteed_return"} <= cues
    assert c.result_for(c.payees[0].id).result == "NAME_DISCREPANCY"
    assert c.result_for(c.payees[1].id).result != "NO_MAJOR_ISSUE"


# ------------------------------------------------------------------ 7. 0-second audio ----
def test_zero_second_audio_cannot_be_assessed():
    vr = service.analyse("PTT-0.wav", wav(0.0), "PTT-0.wav")
    assert vr.state == "cant_assess" and vr.score is None and vr.reasons
    vr = service.analyse("PTT-1.wav", wav(0.3), "PTT-1.wav")  # 0.3 s: too little speech
    assert vr.state == "cant_assess" and vr.score is None


# ------------------------------------------------------------------ 8. corrupt opus ----
def test_garbage_with_an_opus_header_cannot_be_assessed():
    vr = service.analyse("PTT-2.opus", b"OggS" + bytes(range(256)) * 40, "PTT-2.opus")
    assert vr.state == "cant_assess" and vr.score is None and vr.file_id == "PTT-2.opus"


@pytest.mark.skipif(not HAS_FFMPEG, reason="ffmpeg not installed")
def test_truncated_real_opus_never_crashes(tmp_path):
    src = tmp_path / "a.wav"
    src.write_bytes(wav(3.0))
    dst = tmp_path / "a.opus"
    r = subprocess.run(["ffmpeg", "-nostdin", "-y", "-loglevel", "error", "-i", str(src), "-c:a", "libopus",
                        "-b:a", "16k", str(dst)], capture_output=True)
    if r.returncode != 0:
        pytest.skip("this ffmpeg build has no libopus encoder")
    data = dst.read_bytes()
    for cut in (len(data) // 2, 200, 60):
        vr = service.analyse("PTT-3.opus", data[:cut], "PTT-3.opus")
        assert vr.state == "cant_assess" and vr.score is None  # no detector here: never a verdict


# ------------------------------------------------------------------ 9. registry locked ----
def test_locked_registry_is_shown_as_unavailable_in_a_case(tmp_path, monkeypatch):
    from registry.sqlite_registry import create_db
    db = tmp_path / "r.db"
    create_db(db)
    monkeypatch.setenv("VERIQ_REGISTRY_DB", str(db))
    monkeypatch.setenv("VERIQ_REGISTRY_SECRET", "test-secret-0123456789")
    lock = sqlite3.connect(db)
    lock.execute("BEGIN EXCLUSIVE")
    try:
        checks = {"ramesh.k@upi": UserCheck("NAVYUG WEALTH RESEARCH PVT LTD", "UPI app (payee name before paying)",
                                            date(2026, 10, 24))}
        c = build_case(case_id="lk", chat_text=CHAT, claimed_firm=FIRM, checks=checks)
        assert [r.status for r in c.registry] == ["unavailable"]  # never "clean"
        assert "unavailable" in c.registry[0].note
    finally:
        lock.rollback()
        lock.close()
