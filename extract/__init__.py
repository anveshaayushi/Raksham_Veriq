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
    "bank_account": re.compile(r"\b(?:a/c|acct|account|khata)(?:\s*(?:no\.?|number))?\s*[:#.-]?\s*(\d{9,18})\b", re.I),
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
    ("otp_pin_request", re.compile(r"\b(?:share|send|tell|enter)\b[^.\n]{0,20}\b(?:otp|upi pin|m-?pin|cvv|password)\b|\b(?:otp|upi pin|cvv)\b[^.\n]{0,20}\b(?:share|send|batao|bhejo)\b", re.I)),
    ("remote_access", re.compile(r"\b(?:anydesk|teamviewer|rustdesk|quick ?support|screen ?share)\b", re.I)),
    ("fee_to_withdraw", re.compile(r"\b(?:pay|deposit)?\s?\d*%?\s?(?:tax|fee|charges?|gst)\b[^.\n]{0,40}\bwithdraw\w*|\bwithdraw\w*[^.\n]{0,40}\b(?:tax|fee|charges?)\b", re.I)),
    ("guaranteed_return", re.compile(r"\bguaranteed\b[^.\n!]{0,25}\breturns?\b|\bassured returns?\b|\b\d+x returns?\b|\bdouble your money\b|\brisk[- ]free\b", re.I)),
    ("secrecy", re.compile(r"\b(?:don'?t tell|do not tell|keep (?:this|it) secret|confidential offer|kisi ko mat batana)\b", re.I)),
    ("urgency", re.compile(r"\b(?:today only|urgent(?:ly)?|immediately|last chance|within \d+ (?:minutes|hours?)|aaj hi|jaldi)\b", re.I)),
    ("authority_claim", re.compile(r"\b(?:we are )?(?:sebi|rbi)[- ]registered\b|\b(?:rbi|government|sebi) approved\b", re.I)),
]


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


def extract(messages: list, case_id: str) -> tuple[list[Indicator], list[Cue]]:
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
        msg_cues: dict[str, Cue] = {}
        for s, e, typ, raw in hits:
            found.append((m.msg_id, s, typ, raw, src, e))
            norm = _norm(typ, raw)
            if typ in PAYEE_TYPES and norm not in seen_payees:
                if seen_payees and "payee_change" not in msg_cues:
                    lead = max(body.rfind("\n", 0, s) + 1, s - 30)
                    if lead > 0 and body[lead - 1] not in " \n":
                        sp = body.find(" ", lead, s)
                        lead = sp + 1 if sp != -1 else s
                    msg_cues["payee_change"] = Cue(msg_id=m.msg_id, type="payee_change", severity="soft",
                                                   excerpt=body[lead:e].strip())
                seen_payees.append(norm)
        for typ, rx in CUE_RX:
            mt = rx.search(body)
            if mt and typ not in msg_cues:
                msg_cues[typ] = Cue(msg_id=m.msg_id, type=typ, severity=DEFAULT_CUE_SEVERITY[typ],
                                    excerpt=mt.group(0).strip())
        cues.extend(sorted(msg_cues.values(), key=lambda c: c.type))
    inds = [Indicator(id=f"{case_id}-I{n}", case_id=case_id, msg_id=mid, type=typ, value_norm=_norm(typ, raw),
                      value_raw=raw, source=src, confidence="medium" if src == "voice" else "high", span=[s, e])
            for n, (mid, s, typ, raw, src, e) in enumerate(found, start=1)]
    return inds, cues


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
