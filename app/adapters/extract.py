"""Parse + extract adapter.

Uses Claude A's modules when importable (ASSUMED signatures, see CHANGES_REQUESTED.md CR-C2):
    parsing.parse_chat(text: str) -> list[Message]
    extract.extract(messages: list[Message], case_id: str) -> tuple[list[Indicator], list[Cue]]
Otherwise a TEMPORARY STUB below handles Android/iPhone WhatsApp text and a few regexes. The stub is deliberately
small; it is not Claude A's extractor and is labelled as a stub in the UI.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from datetime import datetime

from ..contracts import Cue, Indicator, Message

PAYEE_TYPES = ("upi_vpa", "bank_account")


@dataclass
class Extraction:
    messages: list
    indicators: list
    cues: list
    source: str
    is_stub: bool
    warnings: list[str] = field(default_factory=list)
    qr: dict = field(default_factory=dict)  # {msg_id: [QR payload, ...]} from uploaded images


def _merge_transcripts(msgs: list, transcripts: dict[str, str] | None) -> list:
    """Claude A's CR-8: the parser leaves voice text empty; the transcript is merged in before extraction."""
    import dataclasses

    t = transcripts or {}
    return [dataclasses.replace(m, text=t[m.media_ref]) if getattr(m, "kind", "") == "voice"
            and getattr(m, "media_ref", None) in t and not getattr(m, "text", "") else m for m in msgs]


def _attach_images(msgs: list, images: dict[str, bytes]) -> tuple[list, dict, list[str]]:
    """Decode QR codes in uploaded images. An image named in the chat ("IMG-1.jpg (file attached)") belongs to that
    message; any other uploaded image becomes an extra message marked as uploaded by the user."""
    import dataclasses

    from parsing.qr import decode_qr, parse_upi  # type: ignore

    qr: dict[int, list[str]] = {}
    warns: list[str] = []
    msgs = list(msgs)
    by_ref = {(m.media_ref or "").lower(): m for m in msgs if getattr(m, "kind", "") == "image"}
    for name, data in (images or {}).items():
        m = by_ref.get(name.lower())
        if m is None:
            last_ts = msgs[-1].ts if msgs else None
            if not last_ts:
                warns.append(f"'{name}' was not read: there is no dated chat to attach it to.")
                continue
            m = type(msgs[-1])(msg_id=len(msgs) + 1, ts=last_ts, sender="(image you uploaded)", kind="image",
                               text="", media_ref=name)
            msgs.append(m)
        payloads = decode_qr(data)
        upi = [p for p in payloads if parse_upi(p)]
        if upi:
            qr[m.msg_id] = upi
        elif payloads:
            warns.append(f"'{name}': a QR code was found, but it is not a UPI payment code.")
        else:
            warns.append(f"'{name}': no QR code found. (Reading text from screenshots is not available yet.)")
    return msgs, qr, warns


def run(text: str, case_id: str, transcripts: dict[str, str] | None = None,
        images: dict[str, bytes] | None = None) -> Extraction:
    try:
        import extract as a_extract  # type: ignore  # Claude A
        import parsing as a_parsing  # type: ignore  # Claude A

        if hasattr(a_parsing, "parse_chat") and hasattr(a_extract, "extract"):
            if hasattr(a_parsing, "parse_chat_with_warnings"):
                raw, warns = a_parsing.parse_chat_with_warnings(text)
            else:
                raw, warns = a_parsing.parse_chat(text), []
            msgs = _merge_transcripts(raw, transcripts)
            qr: dict = {}
            if images:
                msgs, qr, iw = _attach_images(msgs, images)
                warns = list(warns) + iw
            inds, cues = a_extract.extract(msgs, case_id, qr=qr) if qr else a_extract.extract(msgs, case_id)
            return Extraction(msgs, inds, cues, "parsing/ + extract/ (FINALE engine)", False, list(warns), qr)
    except ImportError:
        pass
    except Exception as e:  # real module present but contract mismatch: show it, fall back
        res = _stub(text, case_id, transcripts)
        res.warnings.append(f"Claude A's extractor raised {type(e).__name__}; using the stub. See CHANGES_REQUESTED.md.")
        return res
    return _stub(text, case_id, transcripts)


# ---------------------------------------------------------------- TEMPORARY STUB (replace with Claude A) ----
_INV = dict.fromkeys(map(ord, "‎‏‪‫‬‭‮﻿"), None)
_ANDROID = re.compile(r"^(\d{1,2})/(\d{1,2})/(\d{2,4}),? (\d{1,2}):(\d{2})(?:\s?([ap])\.?m\.?)? - ([^:]{1,80}?): (.*)$", re.I)
_IOS = re.compile(r"^\[(\d{1,2})/(\d{1,2})/(\d{2,4}),? (\d{1,2}):(\d{2})(?::\d{2})?(?:\s?([AP])M)?\] ([^:]{1,80}?): (.*)$", re.I)
_SYSTEM = re.compile(r"^(\d{1,2})/(\d{1,2})/(\d{2,4}),? \d{1,2}:\d{2}.* - [^:]*$")
_ATTACH = re.compile(r"(\S+\.(?:opus|ogg|m4a|mp3|wav|aac)) \(file attached\)|<attached: (\S+\.(?:opus|ogg|m4a|mp3|wav|aac))>", re.I)
_MEDIA = re.compile(r"(\S+\.(?:jpg|jpeg|png|webp)) \(file attached\)|<attached: (\S+\.(?:jpg|jpeg|png|webp))>", re.I)
RX = {
    "upi_vpa": re.compile(r"(?<![\w.@-])([a-z0-9][a-z0-9._-]{1,63}@[a-z][a-z0-9]{1,31})(?![\w@-])(?!\.[a-z])", re.I),
    "bank_account": re.compile(r"\b(?:a/c|acct|account)(?:\s*(?:no\.?|number))?\s*[:#.-]?\s*(\d{9,18})\b", re.I),
    "ifsc": re.compile(r"\b([A-Z]{4}0[A-Z0-9]{6})\b"),
    "sebi_reg": re.compile(r"\b(IN[AHZ][0-9A-Z]{9})\b"),
    "phone": re.compile(r"(?<!\d)((?:\+?91[- ]?)?[6-9]\d{9})(?!\d)"),
    "url": re.compile(r"\b(https?://[^\s<>\"']+|www\.[^\s<>\"']+)", re.I),
}
CUE_RX = [
    ("otp_pin_request", "hard", re.compile(r"\b(otp|upi pin|m-?pin|cvv|password)\b", re.I)),
    ("remote_access", "hard", re.compile(r"\b(anydesk|teamviewer|quick ?support|screen ?share)\b", re.I)),
    ("fee_to_withdraw", "hard", re.compile(r"\b(?:tax|fee|charges?|gst)\b[^.\n]{0,40}\bwithdraw\w*|\bwithdraw\w*[^.\n]{0,40}\b(?:tax|fee|charges?)\b", re.I)),
    ("guaranteed_return", "hard", re.compile(r"\b(guaranteed|assured returns?|\d+x returns?|double your money|risk[- ]free)\b", re.I)),
    ("secrecy", "hard", re.compile(r"\b(don'?t tell|keep (?:this|it) secret|confidential offer)\b", re.I)),
    ("urgency", "soft", re.compile(r"\b(today only|urgent(?:ly)?|immediately|last chance|aaj hi|jaldi)\b", re.I)),
    ("authority_claim", "soft", re.compile(r"\b(sebi[- ]registered|rbi approved|government approved)\b", re.I)),
]


def _ts(d, m, y, hh, mm, ap) -> str:
    year = int(y) + (2000 if len(y) == 2 else 0)
    h = int(hh)
    if ap:
        h = h % 12 + (12 if ap.lower() == "p" else 0)
    return datetime(year, int(m), int(d), h, int(mm)).isoformat(timespec="minutes")


_PLAIN = re.compile(r"^([A-Za-z][\w .()'&-]{0,60}): (.+)$")


def date_order(lines: list[str]) -> tuple[str, str | None]:
    """Per-file day/month order (brief section 9). Returns ('dmy'|'mdy', warning or None)."""
    firsts, seconds = [], []
    for ln in lines:
        m = _ANDROID.match(ln) or _IOS.match(ln)
        if m:
            firsts.append(int(m.group(1)))
            seconds.append(int(m.group(2)))
    if any(f > 12 for f in firsts):
        return "dmy", None
    if any(x > 12 for x in seconds):
        return "mdy", "Dates in this file are month-first (US style); they were read that way."
    if firsts:
        return "dmy", "Every date in this file could be day-first or month-first; they were read day-first (Indian style)."
    return "dmy", None


def parse_stub(text: str, transcripts: dict[str, str] | None = None) -> tuple[list, list[str]]:
    msgs: list = []
    warnings: list[str] = []
    cur: dict | None = None
    rows: list[dict] = []
    lines = [raw.translate(_INV).replace("\u202f", " ").replace("\u00a0", " ").rstrip() for raw in text.splitlines()]
    lines = [ln for ln in lines if ln.strip()]
    order, warn = date_order(lines)
    if warn:
        warnings.append(warn)
    dated = any(_ANDROID.match(ln) or _IOS.match(ln) for ln in lines)
    for ln in lines:
        m = _ANDROID.match(ln) or _IOS.match(ln)
        if m:
            a, b, y, hh, mi, ap, sender, body = m.groups()
            d, mo = (a, b) if order == "dmy" else (b, a)
            try:
                ts = _ts(d, mo, y, hh, mi, ap)
            except ValueError:
                warnings.append(f"Unreadable date in: {ln[:40]}")
                cur = None
                continue
            cur = {"ts": ts, "sender": sender.strip(), "text": body}
            rows.append(cur)
        elif dated and _SYSTEM.match(ln):
            cur = None
        elif not dated and _PLAIN.match(ln):
            p = _PLAIN.match(ln)
            cur = {"ts": "", "sender": p.group(1).strip(), "text": p.group(2)}  # no time in export: left empty, never invented
            rows.append(cur)
        elif cur is not None:
            cur["text"] += "\n" + ln.strip()
    if rows and not dated:
        warnings.append("This export has no dates or times, so the timeline keeps the file order and shows no times.")
    for i, r in enumerate(rows, start=1):
        a = _ATTACH.search(r["text"])
        kind, media_ref, body = "text", None, r["text"]
        if a:
            kind, media_ref = "voice", a.group(1) or a.group(2)
            body = (transcripts or {}).get(media_ref, "")
        elif _MEDIA.search(r["text"]):
            mm = _MEDIA.search(r["text"])
            kind, media_ref = "image", mm.group(1) or mm.group(2)
        try:
            msgs.append(Message(msg_id=len(msgs) + 1, ts=r["ts"], sender=r["sender"], kind=kind, text=body, media_ref=media_ref))
        except ValueError as e:  # e.g. the shared contract requires a timestamp (CR-C6)
            if not r["ts"]:
                return [], [w for w in warnings if "no dates or times" not in w] + [
                    "This export has no dates or times. The shared contract needs a time for every message, so it can't "
                    "be read yet (CR-C6). Export the chat again from WhatsApp."]
            warnings.append(f"Skipped a message the contract rejected: {e}")
    if not msgs:
        warnings.append("No messages found. Expected lines like '20/10/2026, 8:59 pm - Name: text' (Android) or "
                        "'[20/10/26, 8:59:12 PM] Name: text' (iPhone).")
    return msgs, warnings


def _stub(text: str, case_id: str, transcripts: dict[str, str] | None) -> Extraction:
    msgs, warnings = parse_stub(text, transcripts)
    inds: list = []
    cues: list = []
    seen_payees: list[str] = []
    for m in msgs:
        body = m.text
        src = "voice" if m.kind == "voice" else "text"
        conf = "medium" if src == "voice" else "high"
        for typ, rx in RX.items():
            for mt in rx.finditer(body):
                raw = mt.group(1)
                norm = raw.lower() if typ in ("upi_vpa", "url") else re.sub(r"\D", "", raw)[-10:] if typ == "phone" else raw
                inds.append(Indicator(id=f"{case_id}-I{len(inds) + 1}", case_id=case_id, msg_id=m.msg_id, type=typ,
                                      value_norm=norm, value_raw=raw, source=src, confidence=conf, span=[mt.start(1), mt.end(1)]))
                if typ in PAYEE_TYPES and norm not in seen_payees:
                    if seen_payees:
                        cues.append(Cue(msg_id=m.msg_id, type="payee_change", severity="soft", excerpt=raw))
                    seen_payees.append(norm)
        for typ, sev, rx in CUE_RX:
            mt = rx.search(body)
            if mt:
                cues.append(Cue(msg_id=m.msg_id, type=typ, severity=sev, excerpt=mt.group(0)))
    return Extraction(msgs, inds, cues, "TEMPORARY STUB in app/adapters/extract.py (Claude A's extractor not found)",
                      True, warnings)


def payees(indicators: list) -> list:
    """One entry per distinct payment destination, in order of first appearance. Never merged across values."""
    out, seen = [], set()
    for i in indicators:
        if i.type in PAYEE_TYPES and i.value_norm not in seen:
            seen.add(i.value_norm)
            out.append(i)
    return out


_AMT = re.compile(r"(?:₹|rs\.?|inr)\s?([\d,]+(?:\.\d{1,2})?)\s?(k|lakh|lac)?", re.I)


def amount_in(text: str) -> str | None:
    """Display only: the first rupee amount in a message (not part of the contract; see CR-C3)."""
    m = _AMT.search(text or "")
    if not m:
        return None
    return f"₹{m.group(1)}" + (f" {m.group(2)}" if m.group(2) else "")
