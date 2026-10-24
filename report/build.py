"""Filing sheet (local, full identifiers) and shareable summary (redacted), brief section 10.

Every value is one of three kinds and is shown as such:
  - from the chat / computed by VERIQ   (known)
  - entered by you                       (user-entered)
  - [BLANK - fill in yourself]           (only the user knows it; never invented)
Formats: Markdown (.md) and HTML (.html). Chat-derived text is escaped in both.
"""

from __future__ import annotations

import html
import re
from dataclasses import dataclass, field
from typing import Any

STANDING_LINE = "VERIQ files no complaints, blocks nothing and contacts no one."
NOT_A_GUARANTEE = "This is not a guarantee."
BLANK = "BLANK (fill in yourself)"
DRAFT_BANNER = ("DRAFT prepared by VERIQ to help you report. This is not an official complaint form and nothing has been "
                "filed. Report at 1930 or cybercrime.gov.in.")

_MD = re.compile(r"([\\`*_{}\[\]()#+\-.!|>~<$&:])")
_PHONE = re.compile(r"(?<!\d)(?:\+?91[- ]?)?[6-9]\d{9}(?!\d)")
_DIGITS = re.compile(r"(?<!\d)\d{9,18}(?!\d)")


_URL = re.compile(r"\b(h)(ttps?)(://)", re.I)
_WWW = re.compile(r"\bwww\.", re.I)


def md(text: Any) -> str:
    """Escape Markdown and defang URLs (hxxp://) so chat links never become clickable in a Markdown viewer."""
    t = _WWW.sub("www[.]", _URL.sub(lambda m: "hxxp" + m.group(2)[3:] + m.group(3), str(text)))
    return _MD.sub(r"\\\1", t).replace("\n", " ")


def redact(text: Any) -> str:
    t = _PHONE.sub(lambda m: "XXXXXX" + m.group(0)[-4:], str(text))
    return _DIGITS.sub(lambda m: "XX" + m.group(0)[-4:], t)


@dataclass
class PayeeRow:
    payee_id: str
    kind: str  # upi_vpa | bank_account
    identifier: str  # full value from the chat
    msg_ids: list[int]
    amount_in_chat: str | None
    result: str
    rule_id: str
    reasons: list[str]
    next_step: str
    findings: list[dict]  # each: claimed, observed, source, as_of, rule, limitation, class, lane
    voice_note: str | None = None
    utr: str = ""  # user-entered
    paid_on: str = ""  # user-entered
    amount_paid: str = ""  # user-entered
    found_in: str = "text"  # text | voice | image (QR code)
    first_seen: str = ""
    qr: dict | None = None  # parsed UPI QR fields when the payee came from a QR code
    review: str = ""  # mistake-recovery status, e.g. "overturned by reviewer X: reason"


@dataclass
class ReportData:
    case_id: str
    generated_at: str
    claimed_firm: str
    case_result: str | None
    decision_source: str
    is_stub: bool
    money_sent: bool
    payees: list[PayeeRow]
    timeline: list[dict]  # msg_id, ts, sender, kind, text
    cues: list[dict]  # msg_id, type, severity, excerpt
    files: list[dict]  # name, kind, sha256
    voice: list[dict]  # file_id, state, reasons, model_version
    complainant_mobile: str = ""
    debited_bank: str = ""
    debited_account: str = ""
    screenshots: str = ""
    case_findings: list[dict] = field(default_factory=list)  # evidence with payee_id "CASE" (registration, voice)
    notes: list[str] = field(default_factory=list)


def _val(v: str, user: bool = True) -> str:
    return f"{v} (entered by you)" if (v and user) else (v if v else BLANK)


def _mdv(v: str) -> str:
    """Markdown cell: user value escaped and marked, or a bold BLANK marker."""
    return f"{md(v)} (entered by you)" if v else f"**{BLANK}**"


def _call_script(d: ReportData) -> list[str]:
    lines = ["\"I want to report an online investment fraud.\"",
             f"\"Someone claiming to be from {d.claimed_firm or 'a firm'} asked me to pay money through WhatsApp.\""]
    for p in d.payees:
        lines.append(f"\"I was asked to pay {p.amount_in_chat or 'an amount'} to {'UPI ID' if p.kind == 'upi_vpa' else 'account'} "
                     f"{p.identifier}. Transaction ID: {p.utr or BLANK}. Date: {p.paid_on or BLANK}.\"")
    lines.append("\"My mobile number is " + (d.complainant_mobile or BLANK) + ". The money left from " + (d.debited_bank or BLANK) + ".\"")
    lines.append("Ask for the complaint/acknowledgement number and write it down.")
    return lines


# ------------------------------------------------------------------ Markdown -------------------------------------
def filing_sheet_md(d: ReportData) -> str:
    out = [f"# VERIQ filing sheet (draft) · case {d.case_id}", "", f"> {DRAFT_BANNER}", "", f"> {STANDING_LINE}", "",
           f"Generated {d.generated_at}. Claimed firm (confirmed by you): **{md(d.claimed_firm or 'not confirmed')}**."]
    if d.is_stub:
        out += ["", f"> **v0 notice:** results come from {md(d.decision_source)}. They are not a real rules-engine decision."]
    out += ["", "## Your details (only you know these)", "", "| Field | Value |", "|---|---|",
            f"| Complainant mobile number | {_mdv(d.complainant_mobile)} |",
            f"| Bank, wallet or merchant debited | {_mdv(d.debited_bank)} |",
            f"| Account or UPI ID debited | {_mdv(d.debited_account)} |",
            f"| Supporting screenshots | {_mdv(d.screenshots)} |", "",
            "## Transactions, one per recipient", ""]
    for i, p in enumerate(d.payees, 1):
        out += [f"### Recipient {i}: {md(p.identifier)}", "", "| Field | Value |", "|---|---|",
                f"| Recipient {'UPI ID' if p.kind == 'upi_vpa' else 'account'} | {md(p.identifier)} (from the chat, message #{', #'.join(map(str, p.msg_ids))}) |",
                f"| Amount requested in the chat | {md(p.amount_in_chat or 'not stated')} (from the chat; not proof of payment) |",
                f"| 12-digit transaction ID (UTR) | {_mdv(p.utr)} |",
                f"| Transaction date | {_mdv(p.paid_on)} |",
                f"| Amount paid | {_mdv(p.amount_paid)} |",
                f"| VERIQ finding | {md(p.result)} (rule {md(p.rule_id)}) |", ""]
    out += _findings_md(d, redacted=False) + _timeline_md(d, redacted=False) + _files_md(d)
    out += ["", "## What to say on the 1930 call", ""] + [f"- {md(x)}" for x in _call_script(d)]
    out += ["", f"_{STANDING_LINE}_", ""]
    return "\n".join(out)


def summary_md(d: ReportData) -> str:
    out = [f"# VERIQ summary (shareable, redacted) · case {d.case_id}", "", f"> {STANDING_LINE}", "",
           f"Generated {d.generated_at}. Claimed firm: **{md(d.claimed_firm or 'not confirmed')}**. "
           f"Overall: **{md(d.case_result or 'no payees found')}**.",
           "", "Account numbers and phone numbers show only their last four digits. Your personal details are left out."]
    if d.case_result == "NO_MAJOR_ISSUE":
        out += ["", f"**{NOT_A_GUARANTEE}**"]
    if d.is_stub:
        out += ["", f"> **v0 notice:** results come from {md(d.decision_source)}. They are not a real rules-engine decision."]
    out += [""] + _findings_md(d, redacted=True) + _timeline_md(d, redacted=True) + _files_md(d) + ["", f"_{STANDING_LINE}_", ""]
    return "\n".join(out)


def _findings_md(d: ReportData, redacted: bool) -> list[str]:
    f = redact if redacted else (lambda x: x)
    out = ["## Per-payee findings", ""]
    for p in d.payees:
        out += [f"### {md(f(p.identifier))}: {md(p.result)} (rule {md(p.rule_id)})", ""]
        out += [f"- {md(f(r))}" for r in p.reasons]
        if p.result == "NO_MAJOR_ISSUE":
            out.append(f"- **{NOT_A_GUARANTEE}**")
        out += [f"- Next step: {md(p.next_step)}", ""]
        if p.findings:
            out += ["| Claimed | Observed | Source | Date | Rule | Limitation |", "|---|---|---|---|---|---|"]
            out += [f"| {md(f(x['claimed']))} | {md(f(x['observed']))} | {md(x['source'])} (class {md(x['class'])}) | {md(x['as_of'])} | "
                    f"{md(x.get('rule', p.rule_id))} | {md(x['limitation'])} |" for x in p.findings]
        else:
            out.append("- Evidence: none entered for this payee (missing, not a match).")
        if p.voice_note:
            out.append(f"- Voice: {md(p.voice_note)}")
        out.append("")
    if d.case_findings:
        out += ["## Evidence about the whole case (not about one payee)", "",
                "| Lane | Claimed | Observed | Source | Date | Limitation |", "|---|---|---|---|---|---|"]
        out += [f"| {md(x['lane'])} (class {md(x['class'])}) | {md(f(x['claimed']))} | {md(f(x['observed']))} | {md(x['source'])} | "
                f"{md(x['as_of'])} | {md(x['limitation'])} |" for x in d.case_findings]
        out.append("")
    return out


def _timeline_md(d: ReportData, redacted: bool) -> list[str]:
    f = redact if redacted else (lambda x: x)
    out = ["## Timeline (what was said, not whether it is true)", ""]
    for m in d.timeline:
        out.append(f"- {md(m['ts'] or 'no time')} · #{m['msg_id']} · {md(m['sender'])} · {md(m['kind'])}: {md(f(m['text'] or '(no text)'))}")
    if d.cues:
        out += ["", "Pressure cues (review only, not proof): " + "; ".join(f"#{c['msg_id']} {md(c['type'])} ({md(c['severity'])}): '{md(f(c['excerpt']))}'" for c in d.cues)]
    return out + [""]


def _files_md(d: ReportData) -> list[str]:
    out = ["## Files and hashes", ""]
    out += [f"- {md(x['name'])} ({md(x['kind'])}) SHA-256 {x['sha256']}" for x in d.files] or ["- none"]
    out.append("- A hash lets anyone check the same file is presented later. It does not prove the file is true.")
    return out


# ------------------------------------------------------------------ HTML ------------------------------------------
_CSS = ("body{font-family:system-ui,sans-serif;max-width:900px;margin:24px auto;padding:0 16px;color:#111;line-height:1.5;font-size:16px}"
        "table{border-collapse:collapse;width:100%;margin:8px 0}td,th{border:1px solid #ccc;padding:6px;text-align:left;vertical-align:top}"
        "th{background:#f2f4f7}.blank{background:#fff3cd;font-weight:600}.banner{background:#eef2ff;border-left:5px solid #3b5bdb;padding:10px}"
        ".stub{background:#fff3cd;border-left:5px solid #b54708;padding:10px}.ng{font-weight:700}")


def _h(v: Any) -> str:
    return html.escape(str(v), quote=True)


def _hv(v: str) -> str:
    return f"{_h(v)} <i>(entered by you)</i>" if v else f"<span class='blank'>{_h(BLANK)}</span>"


def _html_wrap(title: str, body: list[str]) -> str:
    return (f"<!doctype html><html lang='en'><head><meta charset='utf-8'><meta name='viewport' content='width=device-width,initial-scale=1'>"
            f"<title>{_h(title)}</title><style>{_CSS}</style></head><body>{''.join(body)}</body></html>")


def _findings_html(d: ReportData, redacted: bool) -> list[str]:
    f = redact if redacted else (lambda x: x)
    out = ["<h2>Per-payee findings</h2>"]
    for p in d.payees:
        out.append(f"<h3>{_h(f(p.identifier))}: {_h(p.result)} (rule {_h(p.rule_id)})</h3><ul>")
        out += [f"<li>{_h(f(r))}</li>" for r in p.reasons]
        if p.result == "NO_MAJOR_ISSUE":
            out.append(f"<li class='ng'>{_h(NOT_A_GUARANTEE)}</li>")
        out.append(f"<li>Next step: {_h(p.next_step)}</li></ul>")
        if p.findings:
            out.append("<table><tr><th>Claimed</th><th>Observed</th><th>Source</th><th>Date</th><th>Rule</th><th>Limitation</th></tr>")
            out += [f"<tr><td>{_h(f(x['claimed']))}</td><td>{_h(f(x['observed']))}</td><td>{_h(x['source'])} (class {_h(x['class'])})</td>"
                    f"<td>{_h(x['as_of'])}</td><td>{_h(x.get('rule', p.rule_id))}</td><td>{_h(x['limitation'])}</td></tr>" for x in p.findings]
            out.append("</table>")
        else:
            out.append("<p>Evidence: none entered for this payee (missing, not a match).</p>")
        if p.voice_note:
            out.append(f"<p>Voice: {_h(p.voice_note)}</p>")
    if d.case_findings:
        out.append("<h3>Evidence about the whole case (not about one payee)</h3><table><tr><th>Lane</th><th>Claimed</th>"
                   "<th>Observed</th><th>Source</th><th>Date</th><th>Limitation</th></tr>")
        out += [f"<tr><td>{_h(x['lane'])} (class {_h(x['class'])})</td><td>{_h(f(x['claimed']))}</td><td>{_h(f(x['observed']))}</td>"
                f"<td>{_h(x['source'])}</td><td>{_h(x['as_of'])}</td><td>{_h(x['limitation'])}</td></tr>" for x in d.case_findings]
        out.append("</table>")
    return out


def _timeline_html(d: ReportData, redacted: bool) -> list[str]:
    f = redact if redacted else (lambda x: x)
    out = ["<h2>Timeline (what was said, not whether it is true)</h2><ul>"]
    out += [f"<li>{_h(m['ts'] or 'no time')} · #{m['msg_id']} · {_h(m['sender'])} · {_h(m['kind'])}: {_h(f(m['text'] or '(no text)'))}</li>" for m in d.timeline]
    out.append("</ul>")
    if d.cues:
        out.append("<p>Pressure cues (review only, not proof):</p><ul>" + "".join(
            f"<li>#{c['msg_id']} {_h(c['type'])} ({_h(c['severity'])}): '{_h(f(c['excerpt']))}'</li>" for c in d.cues) + "</ul>")
    return out


def _files_html(d: ReportData) -> list[str]:
    rows = "".join(f"<li>{_h(x['name'])} ({_h(x['kind'])}) SHA-256 <code>{_h(x['sha256'])}</code></li>" for x in d.files) or "<li>none</li>"
    return [f"<h2>Files and hashes</h2><ul>{rows}</ul><p>A hash lets anyone check the same file is presented later. It does not prove the file is true.</p>"]


def filing_sheet_html(d: ReportData) -> str:
    b = [f"<h1>VERIQ filing sheet (draft) · case {_h(d.case_id)}</h1>", f"<p class='banner'>{_h(DRAFT_BANNER)}<br><b>{_h(STANDING_LINE)}</b></p>",
         f"<p>Generated {_h(d.generated_at)}. Claimed firm (confirmed by you): <b>{_h(d.claimed_firm or 'not confirmed')}</b>.</p>"]
    if d.is_stub:
        b.append(f"<p class='stub'><b>v0 notice:</b> results come from {_h(d.decision_source)}. They are not a real rules-engine decision.</p>")
    b.append("<h2>Your details (only you know these)</h2><table>"
             f"<tr><th>Complainant mobile number</th><td>{_hv(d.complainant_mobile)}</td></tr>"
             f"<tr><th>Bank, wallet or merchant debited</th><td>{_hv(d.debited_bank)}</td></tr>"
             f"<tr><th>Account or UPI ID debited</th><td>{_hv(d.debited_account)}</td></tr>"
             f"<tr><th>Supporting screenshots</th><td>{_hv(d.screenshots)}</td></tr></table><h2>Transactions, one per recipient</h2>")
    for i, p in enumerate(d.payees, 1):
        b.append(f"<h3>Recipient {i}: {_h(p.identifier)}</h3><table>"
                 f"<tr><th>Recipient {'UPI ID' if p.kind == 'upi_vpa' else 'account'}</th><td>{_h(p.identifier)} <i>(from the chat, message #{_h(', #'.join(map(str, p.msg_ids)))})</i></td></tr>"
                 f"<tr><th>Amount requested in the chat</th><td>{_h(p.amount_in_chat or 'not stated')} <i>(from the chat; not proof of payment)</i></td></tr>"
                 f"<tr><th>12-digit transaction ID (UTR)</th><td>{_hv(p.utr)}</td></tr>"
                 f"<tr><th>Transaction date</th><td>{_hv(p.paid_on)}</td></tr><tr><th>Amount paid</th><td>{_hv(p.amount_paid)}</td></tr>"
                 f"<tr><th>VERIQ finding</th><td>{_h(p.result)} (rule {_h(p.rule_id)})</td></tr></table>")
    b += _findings_html(d, False) + _timeline_html(d, False) + _files_html(d)
    b.append("<h2>What to say on the 1930 call</h2><ul>" + "".join(f"<li>{_h(x)}</li>" for x in _call_script(d)) + "</ul>")
    b.append(f"<p><b>{_h(STANDING_LINE)}</b></p>")
    return _html_wrap(f"VERIQ filing sheet {d.case_id}", b)


def summary_html(d: ReportData) -> str:
    b = [f"<h1>VERIQ summary (shareable, redacted) · case {_h(d.case_id)}</h1>", f"<p class='banner'><b>{_h(STANDING_LINE)}</b></p>",
         f"<p>Generated {_h(d.generated_at)}. Claimed firm: <b>{_h(d.claimed_firm or 'not confirmed')}</b>. Overall: <b>{_h(d.case_result or 'no payees found')}</b>.</p>",
         "<p>Account numbers and phone numbers show only their last four digits. Your personal details are left out.</p>"]
    if d.case_result == "NO_MAJOR_ISSUE":
        b.append(f"<p class='ng'>{_h(NOT_A_GUARANTEE)}</p>")
    if d.is_stub:
        b.append(f"<p class='stub'><b>v0 notice:</b> results come from {_h(d.decision_source)}. They are not a real rules-engine decision.</p>")
    b += _findings_html(d, True) + _timeline_html(d, True) + _files_html(d) + [f"<p><b>{_h(STANDING_LINE)}</b></p>"]
    return _html_wrap(f"VERIQ summary {d.case_id}", b)


INCIDENT_FORMAT = ("VERIQ incident card v1: fields to copy into the complaint form at cybercrime.gov.in or to read out "
                   "on the 1930 helpline. It is not an official NCRP format and nothing has been filed.")


def incident_json(d: ReportData) -> str:
    """Structured incident card (JSON). Full identifiers: keep it private, like the filing sheet."""
    import json

    def blank(v):
        return v if v else None  # null = only the user knows it; never invented

    card = {
        "format": INCIDENT_FORMAT,
        "standing_line": STANDING_LINE,
        "case_id": d.case_id,
        "generated_at": d.generated_at,
        "suggested_category": "Online financial fraud: investment / trading scam (choose the closest category on the portal)",
        "claimed_firm": d.claimed_firm,
        "veriq_overall_result": d.case_result,
        "decision_source": d.decision_source,
        "money_already_sent": d.money_sent,
        "complainant": {"mobile": blank(d.complainant_mobile), "debited_bank_or_wallet": blank(d.debited_bank),
                        "debited_account_or_upi": blank(d.debited_account), "screenshots": blank(d.screenshots)},
        "payees": [{
            "identifier": p.identifier, "type": p.kind, "found_in": p.found_in, "first_seen": p.first_seen,
            "message_ids": p.msg_ids, "amount_asked_in_chat": p.amount_in_chat,
            "veriq_result": p.result, "rule": p.rule_id, "reasons": p.reasons, "next_step": p.next_step,
            "qr_code": ({k: p.qr.get(k) for k in ("pa", "pn", "am", "tn", "link")} if p.qr else None),
            "mistake_review": p.review or None,
            "evidence": [{k: x.get(k) for k in ("class", "lane", "claimed", "observed", "source", "as_of", "rule",
                                                 "limitation")} for x in p.findings],
            "transaction": {"utr": blank(p.utr), "date_paid": blank(p.paid_on), "amount_paid": blank(p.amount_paid)},
        } for p in d.payees],
        "case_evidence": [{k: x.get(k) for k in ("class", "lane", "claimed", "observed", "source", "as_of", "limitation")}
                          for x in d.case_findings],
        "evidence_chain": {
            "files": [{"name": f.get("name"), "kind": f.get("kind"), "sha256": f.get("sha256")} for f in d.files],
            "events": [{"msg_id": t["msg_id"], "ts": t["ts"], "sender": t["sender"], "kind": t["kind"],
                        "text": (t["text"] or "")[:500]} for t in d.timeline],
            "pressure_cues": d.cues,
        },
        "voice_audit": d.voice,
    }
    return json.dumps(card, ensure_ascii=False, indent=1)
