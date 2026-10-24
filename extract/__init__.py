"""Indicator, cue and amount extraction (shared contract: Indicator, Cue, AmountMention).

FINALE, 24 Oct 2026. Claude A's extractor logic (normalisation, account numbers only near account words, hard/soft
cues), ported onto the shared contract by Claude C at the team's request. See CHANGES_REQUESTED.md CR-C13.

extract(messages, case_id) -> (indicators, cues)
amounts(messages, indicators) -> list[AmountMention]
payees(indicators) -> list[Indicator]     one per distinct payment destination, in order of first appearance

Ids are f"{case_id}-I{n}", numbered in chat order (message, then position). Spans index into Message.text.
Indicators from a voice transcript have source "voice" and confidence "medium" (never "high").
"""

from __future__ import annotations

import re

from core.schemas import DEFAULT_CUE_SEVERITY, AmountMention, Cue, Indicator

PAYEE_TYPES = ("upi_vpa", "bank_account")
_DEV_DIGITS = str.maketrans("०१२३४५६७८९", "0123456789")
_LOOKALIKE = str.maketrans({"＠": "@", "﹫": "@", "．": ".", "₹": "₹"})

RX = {
    "upi_vpa": re.compile(r"(?<![\w.@-])([a-z0-9][a-z0-9._-]{1,63}@[a-z][a-z0-9]{1,31})(?![\w@-])(?!\.[a-z])", re.I),
    # Hindi account words added in Q1 after the mixed-language edge test missed "खाता संख्या <digits>"
    "bank_account": re.compile(r"(?:\b(?:a/c|acct|account|khata)|खाता|खाते|अकाउंट)"
                               r"(?:\s*(?:no\.?|number|संख्या|नंबर|नं\.?))?\s*[:#.-]?\s*(\d{9,18})\b", re.I),
    "ifsc": re.compile(r"\b([A-Z]{4}0[A-Z0-9]{6})\b"),
    "sebi_reg": re.compile(r"\b(IN[AHZ][0-9A-Z]{9})\b"),
    "phone": re.compile(r"(?<![\d/])((?:\+91[- ]?)?[6-9]\d{9})(?!\d)"),
    "url": re.compile(r"\b(https?://[^\s<>\"']+|www\.[^\s<>\"']+)", re.I),
}
# "I am X from <Firm>", "head of research at <Firm>", "join <Firm>": capitalised words after a cue word.
_FIRM = re.compile(r"\b(?:from|at|join|with)\s+((?:[A-Z][A-Za-z0-9&]*)(?:\s+(?:[A-Z][A-Za-z0-9&]*|&))*)")
_FIRM_STOP = {"SEBI", "RBI", "UPI", "NSE", "BSE", "WhatsApp", "Telegram", "India", "Monday", "Tuesday", "Wednesday",
              "Thursday", "Friday", "Saturday", "Sunday", "I", "We", "You"}

CUE_RX = [
    ("otp_pin_request", re.compile(r"\b(?:share|send|tell|enter|give)\b[^.\n]{0,20}\b(?:otp|upi pin|m-?pin|cvv|password)\b|\b(?:otp|upi pin|cvv)\b[^.\n]{0,20}\b(?:share|send|batao|bhejo|do)\b", re.I)),
    ("remote_access", re.compile(r"\b(?:anydesk|teamviewer|rustdesk|quick ?support|screen ?share|airdroid)\b", re.I)),
    ("fee_to_withdraw", re.compile(r"\b(?:pay|deposit)?\s?\d*%?\s?(?:tax|fee|charges?|gst)\b[^.\n]{0,40}\bwithdraw\w*|\bwithdraw\w*[^.\n]{0,40}\b(?:tax|fee|charges?|gst)\b|\b(?:unfreeze|unfreezing|release|unlock|clearance)\b[^.\n]{0,15}\b(?:fee|charges?|tax)\b", re.I)),
    ("guaranteed_return", re.compile(r"\bguaranteed?\b[^.\n!]{0,25}\b(?:returns?|profits?|income|gains?)\b|\b\d+\s?%\s?guaranteed?\b|\bassured (?:returns?|profits?)\b|\b\d+\s?x\s(?:returns?|profits?)\b|\bdouble (?:your )?money\b|\brisk[- ]?free\b|\bsure[- ]?shot\b|\bno[- ]loss\b|\bpakka (?:profit|double|return)\w*", re.I)),
    ("secrecy", re.compile(r"\b(?:don'?t tell|do not tell|keep (?:this|it) secret|confidential offer|kisi ko mat batana|kisi ko (?:mat|na) bolna)\b", re.I)),
    ("urgency", re.compile(r"\b(?:today only|urgent(?:ly)?|immediately|last chance|within \d+\s?(?:mins?|minutes|hours?|hrs?)|in (?:the next )?\d+\s?(?:mins?|minutes)|slot (?:will )?(?:be )?cancel\w*|aaj hi|jaldi|turant)\b", re.I)),
    ("authority_claim", re.compile(r"\b(?:we are )?(?:sebi|rbi)[- ]registered\b|\b(?:rbi|government|sebi) approved\b", re.I)),
]

_LEET = str.maketrans({"@": "a", "$": "s", "0": "o", "1": "i", "3": "e", "4": "a", "5": "s", "7": "t"})
_SPACED = re.compile(r"\b(?:[A-Za-z][._\-\s*]){2,}[A-Za-z]\b")


def deobfuscate(text: str) -> str:
    """For cue matching only (never for identifiers or spans): undo l33t inside words ("gu@r@nteed" -> "guaranteed")
    and letter-by-letter spacing ("u_r_g_e_n_t", "P.a.y" -> "urgent", "Pay")."""
    t = re.sub(r"(?<=[A-Za-z])[@$013457]+|[@$013457]+(?=[A-Za-z])", lambda m: m.group(0).translate(_LEET), text)
    return _SPACED.sub(lambda m: re.sub(r"[._\-\s*]", "", m.group(0)), t)


def normalise(text: str) -> str:
    """Same length as the input, so spans stay valid: digit and look-alike substitutions are one-for-one."""
    return (text or "").translate(_DEV_DIGITS).translate(_LOOKALIKE)


def _norm(typ: str, raw: str) -> str:
    if typ in ("upi_vpa", "url"):
        return raw.lower()
    if typ == "phone":
        return re.sub(r"\D", "", raw)[-10:]
    if typ == "firm_name":
        return " ".join(raw.lower().split())
    return raw


def _firm_names(body: str):
    for m in _FIRM.finditer(body):
        words = m.group(1).split()
        while words and words[-1] in _FIRM_STOP | {"&"}:
            words.pop()
        if not words or words[0] in _FIRM_STOP:
            continue
        if len(words) == 1 and not re.search(r"[A-Z].*[A-Z]", words[0]):
            continue  # a single ordinary capitalised word ("from Mumbai") is too weak to be a firm
        raw = " ".join(words)
        start = m.start(1)
        yield raw, start, start + len(raw)


def extract(messages: list, case_id: str, qr: dict | None = None) -> tuple[list[Indicator], list[Cue]]:
    """qr: optional {msg_id: [decoded QR payload, ...]} for image messages (parsing.qr). A UPI ID inside a QR becomes
    an Indicator with source "image" whose span points into the QR payload text (CR-3)."""
    from parsing.qr import parse_upi

    found: list[tuple[int, int, str, str, str, str]] = []  # (msg_id, start, type, raw, source, end)
    cues: list[Cue] = []
    seen_payees: list[str] = []
    for m in messages:
        body = normalise(m.text)
        src = "voice" if m.kind == "voice" else "text"
        hits: list[tuple[int, int, str, str]] = []
        for typ, rx in RX.items():
            for mt in rx.finditer(body):
                hits.append((mt.start(1), mt.end(1), typ, mt.group(1)))
        if src == "text":
            for raw, s, e in _firm_names(body):
                hits.append((s, e, "firm_name", raw))
        hits.sort()
        for payload in (qr or {}).get(m.msg_id, []):
            u = parse_upi(payload)
            if u:
                s = payload.lower().find(u["pa"])
                hits.append((s, s + len(u["pa"]), "upi_vpa", u["pa"]))
        msg_cues: dict[str, Cue] = {}
        qr_vpas = {parse_upi(x)["pa"] for x in (qr or {}).get(m.msg_id, []) if parse_upi(x)}
        for s, e, typ, raw in hits:
            hsrc = "image" if (m.kind == "image" and typ == "upi_vpa" and raw in qr_vpas) else src
            found.append((m.msg_id, s, typ, raw, hsrc, e))
            norm = _norm(typ, raw)
            if typ in PAYEE_TYPES and norm not in seen_payees:
                if seen_payees and "payee_change" not in msg_cues:
                    lead = max(body.rfind("\n", 0, s) + 1, s - 30)
                    if lead > 0 and body[lead - 1] not in " \n":
                        sp = body.find(" ", lead, s)
                        lead = sp + 1 if sp != -1 else s
                    excerpt = f"QR code in an image: {raw}" if hsrc == "image" else body[lead:e].strip()
                    msg_cues["payee_change"] = Cue(msg_id=m.msg_id, type="payee_change", severity="soft",
                                                   excerpt=excerpt or raw)
                seen_payees.append(norm)
        plain = deobfuscate(body)
        for typ, rx in CUE_RX:
            mt = rx.search(body) or rx.search(plain)
            if mt and typ not in msg_cues:
                msg_cues[typ] = Cue(msg_id=m.msg_id, type=typ, severity=DEFAULT_CUE_SEVERITY[typ],
                                    excerpt=mt.group(0).strip())
        cues.extend(sorted(msg_cues.values(), key=lambda c: c.type))
    inds = [Indicator(id=f"{case_id}-I{n}", case_id=case_id, msg_id=mid, type=typ, value_norm=_norm(typ, raw),
                      value_raw=raw, source=src, confidence="medium" if src == "voice" else "high", span=[s, e])
            for n, (mid, s, typ, raw, src, e) in enumerate(found, start=1)]
    return inds, cues


def qr_details(qr: dict | None, indicators: list) -> dict[str, dict]:
    """{payee indicator id: parsed UPI QR fields} for payees that came from a QR code (source "image")."""
    from parsing.qr import parse_upi

    out = {}
    for i in indicators:
        if i.source != "image" or i.type != "upi_vpa":
            continue
        for payload in (qr or {}).get(i.msg_id, []):
            u = parse_upi(payload)
            if u and u["pa"] == i.value_norm:
                out[i.id] = u
                break
    return out


def payees(indicators: list) -> list:
    out, seen = [], set()
    for i in indicators:
        if i.type in PAYEE_TYPES and i.value_norm not in seen:
            seen.add(i.value_norm)
            out.append(i)
    return out


_AMT = re.compile(r"(?:₹|\brs\.?|\binr)\s?(\d{1,3}(?:,\d{2,3})+|\d+)(?:\.\d{1,2})?(?!\s?%)", re.I)


def amounts(messages: list, indicators: list) -> list[AmountMention]:
    """Rupee amounts tied to the first new payee named in the same message (CR-5). Amounts in a message with no
    payee are not attached to anyone."""
    by_msg: dict[int, str] = {}
    for p in payees(indicators):
        by_msg.setdefault(p.msg_id, p.id)
    out = []
    for m in messages:
        pid = by_msg.get(m.msg_id)
        if not pid:
            continue
        body = normalise(m.text)
        for mt in _AMT.finditer(body):
            out.append(AmountMention(msg_id=m.msg_id, payee_id=pid, value_inr=int(mt.group(1).replace(",", "")),
                                     raw=mt.group(0).strip(), span=[mt.start(), mt.end()]))
            break  # first amount in the message
    return out
