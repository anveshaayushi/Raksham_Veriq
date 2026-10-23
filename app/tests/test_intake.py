import io
import zipfile

import pytest

from app.intake import Intake, IntakeError, add_audio, add_chat, decode_text, sha256

CHAT = "20/10/2026, 8:59 pm - Rahul: Pay to a.b@upi".encode()
OGG = b"OggS" + b"\x00" * 200


def _zip(entries, compress=zipfile.ZIP_DEFLATED):
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w", compress) as z:
        for name, data in entries:
            z.writestr(name, data)
    return buf.getvalue()


def test_txt_accepted_and_hashed():
    i = Intake()
    add_chat(i, "WhatsApp Chat.txt", CHAT)
    assert i.chat.sha256 == sha256(CHAT) and i.chat.name == "WhatsApp_Chat.txt"


@pytest.mark.parametrize("name,data,msg", [("c.pdf", CHAT, "WhatsApp export"), ("c.txt", b"   ", "empty"),
                                           ("c.txt", b"\x00\x01binary", "does not look like text"),
                                           ("c.txt", b"x" * (2 * 1024 * 1024 + 1), "larger")])
def test_bad_chat_rejected(name, data, msg):
    with pytest.raises(IntakeError, match=msg):
        add_chat(Intake(), name, data)


def test_non_utf8_rejected_and_utf16_accepted():
    with pytest.raises(IntakeError, match="UTF-8"):
        decode_text(b"\xc3\x28 bad")
    assert "Rahul" in decode_text("x - Rahul: hi".encode("utf-16"))


def test_audio_checks():
    i = Intake()
    add_audio(i, "v.opus", OGG)
    with pytest.raises(IntakeError, match="not a supported"):
        add_audio(i, "v.exe", OGG)
    with pytest.raises(IntakeError, match="does not look like an audio"):
        add_audio(i, "v.opus", b"hello world")


def test_zip_with_chat_and_voice():
    i = Intake()
    add_chat(i, "export.zip", _zip([("WhatsApp Chat.txt", CHAT), ("PTT-1.opus", OGG), ("photo.jpg", b"x")]))
    assert i.chat is not None and len(i.audio) == 1 and any("photo.jpg" in w for w in i.warnings)


@pytest.mark.parametrize("bad", ["../evil.txt", "/etc/passwd.txt", "a/../../b.txt", "C:evil.txt"])
def test_zip_slip_rejected(bad):
    with pytest.raises(IntakeError, match="unsafe file path"):
        add_chat(Intake(), "x.zip", _zip([(bad, CHAT)]))


def test_zip_bomb_ratio_rejected():
    with pytest.raises(IntakeError, match="compression ratio|too much data"):
        add_chat(Intake(), "x.zip", _zip([("chat.txt", CHAT + b"0" * 5_000_000)]))


def test_zip_too_many_members_and_no_chat():
    with pytest.raises(IntakeError, match="more than"):
        add_chat(Intake(), "x.zip", _zip([(f"f{i}.jpg", b"x") for i in range(51)]))
    with pytest.raises(IntakeError, match="No chat"):
        add_chat(Intake(), "x.zip", _zip([("a.opus", OGG)]))
    with pytest.raises(IntakeError, match="damaged"):
        add_chat(Intake(), "x.zip", b"PK not really")
