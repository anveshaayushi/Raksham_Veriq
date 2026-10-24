"""App-side upload guard: type, size, count, magic bytes, safe ZIP reading, SHA-256.

Nothing here writes to disk: files stay in memory. ZIP members are read in memory with limits on member count,
per-member and total uncompressed size, and compression ratio; paths are never used to create files, so ZIP-slip
cannot write anywhere. Claude A owns the full validation spec (brief section 9); this guard can be replaced by it.
"""

from __future__ import annotations

import hashlib
import io
import zipfile
from dataclasses import dataclass, field

MAX_CHAT_BYTES = 2 * 1024 * 1024
MAX_AUDIO_BYTES = 20 * 1024 * 1024
MAX_AUDIO_FILES = 10
MAX_ZIP_BYTES = 60 * 1024 * 1024
MAX_ZIP_MEMBERS = 50
MAX_ZIP_TOTAL_UNCOMPRESSED = 80 * 1024 * 1024
MAX_ZIP_RATIO = 100  # uncompressed / compressed, per member
AUDIO_EXT = {".opus", ".ogg", ".m4a", ".mp3", ".wav", ".aac"}
IMAGE_EXT = {".jpg", ".jpeg", ".png", ".webp"}
MAX_IMAGE_BYTES = 8 * 1024 * 1024
MAX_IMAGES = 10


class IntakeError(ValueError):
    """Plain-language reason shown to the user."""


@dataclass
class IntakeFile:
    name: str
    kind: str  # chat | audio
    data: bytes
    sha256: str
    note: str = ""


@dataclass
class Intake:
    chat: IntakeFile | None = None
    audio: list[IntakeFile] = field(default_factory=list)
    images: list[IntakeFile] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)


def sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def safe_name(name: str) -> str:
    base = name.replace("\\", "/").rsplit("/", 1)[-1]
    clean = "".join(c if c.isalnum() or c in "._-" else "_" for c in base)[:120]
    return clean or "file"


def _ext(name: str) -> str:
    return "." + name.rsplit(".", 1)[-1].lower() if "." in name else ""


def looks_like_text(data: bytes) -> bool:
    if data.startswith((b"\xff\xfe", b"\xfe\xff")):
        return True
    if b"\x00" in data[:4096]:
        return False
    try:
        data[:4096].decode("utf-8")
        return True
    except UnicodeDecodeError as e:  # a multi-byte char cut at the 4096 boundary is fine
        return e.start >= 4090


def looks_like_audio(data: bytes) -> bool:
    head = data[:12]
    return (head.startswith(b"OggS") or head.startswith(b"RIFF") and head[8:12] == b"WAVE" or head.startswith(b"ID3")
            or head[:2] in (b"\xff\xfb", b"\xff\xf3", b"\xff\xf2", b"\xff\xf1", b"\xff\xf9") or head[4:8] == b"ftyp")


def looks_like_image(data: bytes) -> bool:
    return (data[:3] == b"\xff\xd8\xff" or data[:8] == b"\x89PNG\r\n\x1a\n"
            or (data[:4] == b"RIFF" and data[8:12] == b"WEBP"))


def add_image(intake: Intake, name: str, data: bytes) -> None:
    """Screenshots / QR images. Only QR codes are read from them (no OCR, no image-forensics model)."""
    if len(intake.images) >= MAX_IMAGES:
        raise IntakeError(f"At most {MAX_IMAGES} images.")
    if _ext(name) not in IMAGE_EXT:
        raise IntakeError(f"'{safe_name(name)}' is not a supported image type ({', '.join(sorted(IMAGE_EXT))}).")
    if not data:
        raise IntakeError(f"'{safe_name(name)}' is empty.")
    if len(data) > MAX_IMAGE_BYTES:
        raise IntakeError(f"'{safe_name(name)}' is larger than {MAX_IMAGE_BYTES // (1024 * 1024)} MB.")
    if not looks_like_image(data):
        raise IntakeError(f"'{safe_name(name)}' does not look like a JPEG, PNG or WebP image.")
    intake.images.append(IntakeFile(safe_name(name), "image", data, sha256(data)))


def decode_text(data: bytes) -> str:
    if data.startswith((b"\xff\xfe", b"\xfe\xff")):
        return data.decode("utf-16")
    try:
        return data.decode("utf-8-sig")
    except UnicodeDecodeError as e:
        raise IntakeError("The chat file is not UTF-8 text. Export the chat again as .txt.") from e


def add_chat(intake: Intake, name: str, data: bytes) -> None:
    ext = _ext(name)
    if ext == ".zip":
        _add_zip(intake, name, data)
        return
    if ext != ".txt":
        raise IntakeError("The chat must be a WhatsApp export: a .txt file or the .zip WhatsApp creates.")
    if not data.strip():
        raise IntakeError("The chat file is empty.")
    if len(data) > MAX_CHAT_BYTES:
        raise IntakeError(f"The chat file is larger than {MAX_CHAT_BYTES // (1024 * 1024)} MB.")
    if not looks_like_text(data):
        raise IntakeError("This file does not look like text. Export the chat again as .txt.")
    intake.chat = IntakeFile(safe_name(name), "chat", data, sha256(data))


def add_audio(intake: Intake, name: str, data: bytes) -> None:
    if len(intake.audio) >= MAX_AUDIO_FILES:
        raise IntakeError(f"At most {MAX_AUDIO_FILES} voice notes.")
    if _ext(name) not in AUDIO_EXT:
        raise IntakeError(f"'{safe_name(name)}' is not a supported voice-note type ({', '.join(sorted(AUDIO_EXT))}).")
    if not data:
        raise IntakeError(f"'{safe_name(name)}' is empty.")
    if len(data) > MAX_AUDIO_BYTES:
        raise IntakeError(f"'{safe_name(name)}' is larger than {MAX_AUDIO_BYTES // (1024 * 1024)} MB.")
    if not looks_like_audio(data):
        raise IntakeError(f"'{safe_name(name)}' does not look like an audio file.")
    intake.audio.append(IntakeFile(safe_name(name), "audio", data, sha256(data)))


def _add_zip(intake: Intake, name: str, data: bytes) -> None:
    if len(data) > MAX_ZIP_BYTES:
        raise IntakeError("The .zip is too large.")
    try:
        zf = zipfile.ZipFile(io.BytesIO(data))
    except zipfile.BadZipFile as e:
        raise IntakeError("The .zip file is damaged or not a zip.") from e
    infos = [i for i in zf.infolist() if not i.is_dir()]
    if len(infos) > MAX_ZIP_MEMBERS:
        raise IntakeError(f"The .zip has more than {MAX_ZIP_MEMBERS} files.")
    total = 0
    chat_found = False
    for info in infos:
        n = info.filename
        if n.startswith(("/", "\\")) or ".." in n.replace("\\", "/").split("/") or ":" in n:
            raise IntakeError("The .zip contains an unsafe file path and was rejected.")
        if info.flag_bits & 0x1:
            raise IntakeError("Encrypted .zip files are not supported.")
        total += info.file_size
        if total > MAX_ZIP_TOTAL_UNCOMPRESSED:
            raise IntakeError("The .zip expands to too much data and was rejected.")
        if info.compress_size and info.file_size / info.compress_size > MAX_ZIP_RATIO:
            raise IntakeError("The .zip has a suspicious compression ratio and was rejected.")
    for info in infos:
        ext = _ext(info.filename)
        if ext == ".txt" and not chat_found:
            add_chat(intake, info.filename, zf.read(info))
            chat_found = True
        elif ext in AUDIO_EXT and len(intake.audio) < MAX_AUDIO_FILES:
            add_audio(intake, info.filename, zf.read(info))
        elif ext in IMAGE_EXT and len(intake.images) < MAX_IMAGES:
            try:
                add_image(intake, info.filename, zf.read(info))
            except IntakeError as e:
                intake.warnings.append(str(e))
        else:
            intake.warnings.append(f"Skipped '{safe_name(info.filename)}' from the .zip (not a chat, voice note or image).")
    if not chat_found:
        raise IntakeError("No chat .txt was found inside the .zip.")
    intake.chat.note = f"from {safe_name(name)}"
