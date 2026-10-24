"""Scenario player (Q3 item b): a phone-style chat that plays message by message, recomputing VERIQ's answer live.

The jury can edit any line (for example change a payee's UPI ID), choose what the bank app shows for each payee,
add a voice note, and replay. Panels: attack (the message just received and the pressure it applies), alert (VERIQ's
answer on the chat SO FAR), user action (the next step), review (a genuine user flagged by mistake asks for review;
a reviewer overturns it, with the time to decision), report (download). Every answer is computed by the same
engine as the main app; nothing is pre-written. All names, IDs and firms are fictional.
"""
from __future__ import annotations

import html
import re
import time
from datetime import date
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
_START = re.compile(r"^\s*\[?\d{1,2}[/.-]\d{1,2}[/.-]\d{2,4},?\s+\d{1,2}[:.]\d{2}")

# Scenario D: a LEGITIMATE broker whose bank account is registered under a short trading name. The user's bank app
# shows "SSL CAPITAL SERVICES", which shares no word with "Sahyadri Securities Ltd", so VERIQ says
# NAME_DISCREPANCY: a false alarm. The user asks for a review; the reviewer checks SEBI and overturns it.
SCENARIO_D = {
    "title": "D · Legitimate broker flagged by mistake, then cleared",
    "claimed_firm": "Sahyadri Securities Ltd",
    "chat": ("20/10/2026, 10:02 am - Kavya (Sahyadri Securities): Good morning Mr Joshi, your trading account is active.\n"
             "20/10/2026, 10:04 am - Kavya (Sahyadri Securities): To add funds for the IPO you applied for, use UPI ID "
             "sslcap.sec@validicici (our client funds account).\n"
             "20/10/2026, 10:05 am - Mr Joshi: Ok, will pay ₹15,000 today.\n"
             "20/10/2026, 10:06 am - Kavya (Sahyadri Securities): Thank you. You can also verify us on SEBI Check.\n"),
    "names": {"sslcap.sec@validicici": "SSL CAPITAL SERVICES"},
    "transcripts": {},
}


def scenarios() -> dict:
    from app.case import demo_inputs, demo_title, load_demo
    out = {}
    for sid in ("A", "B", "C"):
        fx = load_demo(sid)
        di = demo_inputs(fx)
        out[sid] = {"title": demo_title(fx) if callable(demo_title) else sid, "claimed_firm": di["claimed_firm"],
                    "chat": di["chat_text"], "names": {k: v["name"] for k, v in di["checks"].items()},
                    "transcripts": di["transcripts"] or {}, "fixture": fx}
    out["D"] = SCENARIO_D
    return out


def split_messages(chat: str) -> list[str]:
    """Group raw lines into messages (a message may continue on following lines)."""
    msgs: list[str] = []
    for ln in chat.splitlines():
        if _START.match(ln) or not msgs:
            msgs.append(ln)
        else:
            msgs[-1] += "\n" + ln
    return [m for m in msgs if m.strip()]


def compute(chat_so_far: str, firm: str, names: dict, choice: dict, transcripts: dict, audio: dict, fixture=None):
    """VERIQ's answer on the chat so far. choice[payee] in {'scenario', 'firm', 'unchecked', 'custom:<NAME>'}."""
    from app.case import UserCheck, build_case
    checks = {}
    for k, how in choice.items():
        if how == "firm":
            checks[k] = UserCheck(firm.upper(), "Bank app (beneficiary name)", date(2026, 10, 25))
        elif how == "scenario" and names.get(k):
            checks[k] = UserCheck(names[k], "Bank app (beneficiary name)", date(2026, 10, 25))
        elif how.startswith("custom:") and how[7:].strip():
            checks[k] = UserCheck(how[7:].strip(), "Bank app (beneficiary name)", date(2026, 10, 25))
    t0 = time.perf_counter()
    c = build_case(case_id="player", chat_text=chat_so_far, claimed_firm=firm, checks=checks,
                   transcripts=transcripts or None, audio=audio or None, fixture=fixture)
    return c, (time.perf_counter() - t0) * 1000


def bubble(msg: str, mine: bool) -> str:
    """Phone-style bubble. The text is escaped: chat content can never inject HTML."""
    m = re.match(r"^(.*?) - ([^:]{1,60}): (.*)$", msg, re.S)
    when, who, body = (m.group(1), m.group(2), m.group(3)) if m else ("", "", msg)
    side = "flex-end" if mine else "flex-start"
    bg = "#dcf8c6" if mine else "#ffffff"
    return (f"<div style='display:flex;justify-content:{side};margin:4px 0'><div style='background:{bg};"
            f"color:#111;border-radius:10px;padding:6px 10px;max-width:85%;box-shadow:0 1px 1px rgba(0,0,0,.15)'>"
            f"<div style='font-size:.75rem;color:#555'>{html.escape(who)} · {html.escape(when)}</div>"
            f"<div style='white-space:pre-wrap'>{html.escape(body)}</div></div></div>")


def render(st) -> None:
    from app.next_steps import PLAIN_LABEL
    from rules import HIGH_PRESSURE
    S = st.session_state
    sc = scenarios()
    st.header("Scenario player")
    st.write("Watch a scam (or a genuine chat) arrive message by message. VERIQ re-checks the chat **after every "
             "message**. Change anything and replay: the answer is recomputed, never pre-written.")
    sid = st.radio("Scenario", list(sc), format_func=lambda k: sc[k]["title"], key="pl_sid", horizontal=False)
    if S.get("pl_loaded") != sid:
        S.pl_loaded, S.pl_idx, S.pl_chat = sid, 1, sc[sid]["chat"]
        S.pl_firm, S.pl_voice, S.pl_review = sc[sid]["claimed_firm"], False, None
    s = sc[sid]
    with st.expander("Edit the chat or the firm (for example, change a payee's UPI ID)", expanded=False):
        S.pl_chat = st.text_area("Chat (WhatsApp export lines)", S.pl_chat, height=200, key=f"pl_chat_edit_{sid}")
        S.pl_firm = st.text_input("Firm the chat claims to be", S.pl_firm, key=f"pl_firm_edit_{sid}")
        S.pl_voice = st.checkbox("Add a voice note from the 'advisor' at the end (synthetic TTS demo clip)",
                                 S.pl_voice, key=f"pl_voice_{sid}")
    chat = S.pl_chat
    audio = {}
    if S.pl_voice:
        clip = ROOT / "app" / "demo_media" / "demo_voice_synthetic_tts.wav"
        last = split_messages(chat)[-1] if split_messages(chat) else "20/10/2026, 10:10 am - Advisor: x"
        stamp = last.split(" - ")[0]
        chat = chat.rstrip("\n") + f"\n{stamp} - Advisor: PTT-99-player.wav (file attached)\n"
        audio = {"PTT-99-player.wav": clip.read_bytes()}
    msgs = split_messages(chat)
    S.pl_idx = max(1, min(S.pl_idx, len(msgs)))
    c1, c2, c3 = st.columns(3)
    if c1.button("▶ Next message", key="pl_next", disabled=S.pl_idx >= len(msgs)):
        S.pl_idx += 1
    if c2.button("⏩ Show all", key="pl_all"):
        S.pl_idx = len(msgs)
    if c3.button("⟲ Replay", key="pl_replay"):
        S.pl_idx, S.pl_review = 1, None
    shown = msgs[:S.pl_idx]
    first_sender = re.match(r"^.*? - ([^:]+):", msgs[0]).group(1) if msgs and re.match(r"^.*? - ([^:]+):", msgs[0]) else ""
    st.markdown("<div style='background:#ece5dd;border-radius:14px;padding:10px;max-width:420px'>"
                + "".join(bubble(m, mine=bool(first_sender) and not m.split(" - ", 1)[-1].startswith(first_sender))
                          for m in shown) + "</div>", unsafe_allow_html=True)  # bubbles escape all chat text
    st.caption(f"Message {S.pl_idx} of {len(msgs)}")

    from app.case import extract
    ex = extract("player", "\n".join(shown) + "\n", s["transcripts"] or None, None, None)
    from app.adapters.extract import payees as payee_list
    found = [p.value_norm for p in payee_list(ex.indicators)]
    choice = {}
    if found:
        st.subheader("What does the bank app show for each payee?")
        for p in found:
            opts = ["scenario", "firm", "unchecked", "custom"]
            lab = {"scenario": f"As in this scenario: {s['names'].get(p) or 'not checked'}",
                   "firm": f"The firm's own name ({S.pl_firm.upper()})", "unchecked": "Not checked yet",
                   "custom": "Type a name"}
            how = st.radio(f"`{p}`", opts, format_func=lambda o, _lab=lab: _lab[o], key=f"pl_nm_{sid}_{p}", horizontal=False)
            if how == "custom":
                how = "custom:" + st.text_input("Name shown", key=f"pl_nmc_{sid}_{p}")
            choice[p] = how
    case, ms = compute("\n".join(shown) + "\n", S.pl_firm, s["names"], choice, s["transcripts"], audio, s.get("fixture"))
    res = case.case_result()

    st.subheader("1 · Attack: the message just received")
    last = shown[-1]
    cues = [x for x in case.extraction.cues if x.msg_id == len(shown)]
    st.write(", ".join(f"**{x.type.replace('_', ' ')}** ({x.severity})" for x in cues) or "No pressure cue in this message.")
    st.subheader("2 · Alert: VERIQ's answer on the chat so far")
    if res is None:
        st.info("No payment destination yet: nothing to check.")
    else:
        st.markdown(f"**{PLAIN_LABEL[res]}** ({res}) · computed in {ms:.0f} ms")
        for p in case.payees:
            d = case.result_for(p.id)
            hp = " · high pressure" if d.reasons and d.reasons[0].startswith(HIGH_PRESSURE) else ""
            from app.text_safety import md_escape
            why = md_escape(str((d.reasons or [""])[0])[:180])
            st.markdown(f"- `{p.value_norm}`: **{d.result}**{hp} · why: {why}")
    st.subheader("3 · What the user should do")
    if res:
        st.write(case.result_for(case.payees[0].id).next_step if len(case.payees) == 1 else
                 next(case.result_for(p.id).next_step for p in case.payees if case.result_for(p.id).result == res))
    st.subheader("4 · Review: a genuine user flagged by mistake")
    acc = [p for p in case.payees if case.result_for(p.id).result in ("NAME_DISCREPANCY", "LINKED", "REGISTRATION_CONFLICT")]
    if not acc:
        st.caption("Nothing to review: no payee has an accusing answer right now.")
    else:
        p = acc[0]
        from app.overturn import Ledger
        led = S.setdefault("pl_ledger", Ledger())
        if S.pl_review is None and st.button(f"This is my real broker: ask a person to review `{p.value_norm}`",
                                             key="pl_req"):
            led.requests.pop(p.id, None)
            led.request(p.id, p.value_norm, case.result_for(p.id).result,
                        "The firm uses a different legal or trading name", "player", "SEBI Check reference (typed by the user)")
            S.pl_review = "requested"
        if S.pl_review == "requested":
            st.info("Review requested. The original answer is kept until a reviewer decides.")
            if st.button("Reviewer: SEBI Check confirms the @valid handle belongs to the firm: overturn", key="pl_over"):
                r = led.decide(p.id, "overturned", "Reviewer (demo)", "SEBI Check shows the @valid handle")
                S.pl_review = f"overturned · {r.elapsed()}"
        if S.pl_review and S.pl_review.startswith("overturned"):
            st.success(f"Overturned by the reviewer ({S.pl_review.split(' · ', 1)[1]}). Audit trail kept, "
                       "with no raw payee identifier.")
    st.subheader("5 · Report")
    if res:
        from app.case import report_data
        from report.build import summary_md
        st.download_button("Download the shareable summary (Markdown)", summary_md(report_data(case, money_sent=False)),
                           f"veriq_player_{sid}.md", "text/markdown", key="pl_dl")
