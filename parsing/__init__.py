"""WhatsApp chat parser (shared contract: core.schemas.Message).

FINALE, 24 Oct 2026. Claude A's parser logic, ported onto the shared contract by Claude C at the team's request
(A's delivery used types that core/schemas.py does not define). See CHANGES_REQUESTED.md CR-C13.

parse_chat(text) -> list[Message]
parse_chat_with_warnings(text) -> (list[Message], list[str])

- Android ("13/10/2026, 6:02 pm - Name: text") and iPhone ("[13/10/26, 6:02:11 PM] Name: text") exports.
- Day/month order decided per file (Indian day-first by default; month-first only if the file proves it).
- Multi-line messages are joined; system lines ("Messages and calls are end-to-end encrypted ...") are skipped.
- Voice notes: kind "voice", media_ref = file name, text "" (transcripts are merged later, CR-8).
- Times are IST (+05:30) because WhatsApp exports carry local time without a zone.
- Exports without any timestamps are refused with a warning (the contract needs a time per message, CR-C6).
"""

from __future__ import annotations

import re
from datetime import datetime

from core.schemas import Message

TZ = "+05:30"
_INV = {ord(c): None for c in "‎‏​‌‍﻿⁦⁧⁨⁩"}
_ANDROID = re.compile(
    r"^(\d{1,2})/(\d{1,2})/(\d{2,4}),? (\d{1,2}):(\d{2})(?::\d{2})?(?:\s?([ap])\.?m\.?)? - ([^:]{1,80}?): (.*)$", re.I)
_IOS = re.compile(
    r"^\[(\d{1,2})/(\d{1,2})/(\d{2,4}),? (\d{1,2}):(\d{2})(?::\d{2})?(?:\s?([ap])\.?m\.?)?\] ([^:]{1,80}?): (.*)$", re.I)
_DATED_SYSTEM = re.compile(r"^\[?\d{1,2}/\d{1,2}/\d{2,4},? \d{1,2}:\d{2}")
_VOICE = re.compile(r"(\S+\.(?:opus|ogg|m4a|mp3|wav|aac)) \(file attached\)|<attached: (\S+\.(?:opus|ogg|m4a|mp3|wav|aac))>", re.I)
_IMAGE = re.compile(r"(\S+\.(?:jpg|jpeg|png|webp)) \(file attached\)|<attached: (\S+\.(?:jpg|jpeg|png|webp))>", re.I)


def _clean(line: str) -> str:
    return line.translate(_INV).replace(" ", " ").replace(" ", " ").rstrip()


def _date_order(lines: list[str]) -> tuple[str, str | None]:
    firsts, seconds = [], []
    for ln in lines:
        m = _ANDROID.match(ln) or _IOS.match(ln)
        if m:
            firsts.append(int(m.group(1)))
            seconds.append(int(m.group(2)))
    if any(f > 12 for f in firsts):
        return "dmy", None
    if any(s > 12 for s in seconds):
        return "mdy", "Dates in this file are month-first (US style); they were read that way."
    if firsts:
        return "dmy", "Every date in this file could be day-first or month-first; they were read day-first (Indian style)."
    return "dmy", None


def _iso(d: str, mo: str, y: str, hh: str, mi: str, ap: str | None) -> str:
    year = int(y) + (2000 if len(y) == 2 else 0)
    h = int(hh)
    if ap:
        h = h % 12 + (12 if ap.lower() == "p" else 0)
    return datetime(year, int(mo), int(d), h, int(mi)).strftime("%Y-%m-%dT%H:%M:%S") + TZ


def parse_chat_with_warnings(text: str) -> tuple[list[Message], list[str]]:
    lines = [ln for ln in (_clean(x) for x in (text or "").splitlines()) if ln.strip()]
    order, warn = _date_order(lines)
    warnings = [warn] if warn else []
    rows: list[dict] = []
    cur: dict | None = None
    for ln in lines:
        m = _ANDROID.match(ln) or _IOS.match(ln)
        if m:
            a, b, y, hh, mi, ap, sender, body = m.groups()
            d, mo = (a, b) if order == "dmy" else (b, a)
            try:
                ts = _iso(d, mo, y, hh, mi, ap)
            except ValueError:
                warnings.append(f"Unreadable date, line skipped: {ln[:40]}")
                cur = None
                continue
            cur = {"ts": ts, "sender": sender.strip(), "text": body}
            rows.append(cur)
        elif _DATED_SYSTEM.match(ln):
            cur = None  # dated line without "Name:" = WhatsApp system line
        elif cur is not None:
            cur["text"] += "\n" + ln.strip()
    if not rows:
        if lines:
            warnings.append("No dated WhatsApp messages found. The shared contract needs a time for every message, so "
                            "exports without dates can't be read (CR-C6). Export the chat again from WhatsApp.")
        return [], warnings
    msgs: list[Message] = []
    for r in rows:
        kind, media_ref, body = "text", None, r["text"]
        v, im = _VOICE.search(body), _IMAGE.search(body)
        if v:
            kind, media_ref, body = "voice", v.group(1) or v.group(2), ""
        elif im:
            kind, media_ref = "image", im.group(1) or im.group(2)
        msgs.append(Message(msg_id=len(msgs) + 1, ts=r["ts"], sender=r["sender"], kind=kind, text=body,
                            media_ref=media_ref))
    return msgs, warnings


def parse_chat(text: str) -> list[Message]:
    return parse_chat_with_warnings(text)[0]
