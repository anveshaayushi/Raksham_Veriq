"""VERIQ v0 (pre-build) app. Run from the repo root:  streamlit run app/streamlit_app.py

Steps: 1 Consent · 2 Upload · 3 Confirm the firm · 4 Payee names (user-reported) · 5 Answer · 6 Reports
All chat-derived text is escaped before display. Nothing is written to disk by this app.
"""

from __future__ import annotations

import sys
import uuid
from datetime import date
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import streamlit as st  # noqa: E402

from app.case import UserCheck, build_case, extract, load_demo, report_data  # noqa: E402
from app.adapters.extract import amount_in, payees as payee_list  # noqa: E402
from app.contracts import SCHEMA_SOURCE, evidence_class, get  # noqa: E402
from app.evidence_input import SOURCES  # noqa: E402
from app.intake import Intake, IntakeError, add_audio, add_chat, decode_text, sha256  # noqa: E402
from app.next_steps import NOT_A_GUARANTEE, PLAIN_LABEL, STANDING_LINE, display_next_step, with_money_sent  # noqa: E402
from app.text_safety import code, md_escape  # noqa: E402
from report.build import filing_sheet_html, filing_sheet_md, summary_html, summary_md  # noqa: E402

STEPS = ["Consent", "Upload", "Confirm the firm", "Payee names", "Answer", "Reports"]
ICON = {"LINKED": "🔗", "NAME_DISCREPANCY": "⛔", "REGISTRATION_CONFLICT": "⛔", "HUMAN_REVIEW": "⚠️", "INCONCLUSIVE": "❔",
        "NO_MAJOR_ISSUE": "✅"}

st.set_page_config(page_title="VERIQ · check before you pay", page_icon="🛡️", layout="centered")
st.markdown(
    """<style>
    html, body, [class*="css"] {font-size: 18px;}
    .stButton>button, .stDownloadButton>button {width: 100%; min-height: 3rem; font-size: 1.05rem; font-weight: 600;}
    div[data-testid="stCaptionContainer"] {font-size: 0.95rem;}
    </style>""",
    unsafe_allow_html=True,  # constant CSS only; never user content
)

S = st.session_state
S.setdefault("step", 1)
S.setdefault("case_id", "case-" + uuid.uuid4().hex[:8])


def go(n: int) -> None:
    S.step = n


def reset() -> None:
    for k in list(S.keys()):
        del S[k]


# ---------------------------------------------------------------- header ----
st.title("VERIQ")
st.write("Check a suspicious money chat **before you pay**: who you were told you're paying, and who would actually receive it.")
st.progress(S.step / len(STEPS), text=f"Step {S.step} of {len(STEPS)}: {STEPS[S.step - 1]}")
with st.sidebar:
    st.subheader("Your data")
    st.write("Files stay in this app's memory for this browser session. Nothing is saved to disk by VERIQ.")
    if st.button("Delete my data and start again", key="reset"):
        reset()
        st.rerun()
    st.caption(f"Contract: {SCHEMA_SOURCE}")
    st.caption(STANDING_LINE)

# ---------------------------------------------------------------- 1 consent ----
if S.step == 1:
    st.header("1 · Before you start")
    st.markdown(
        "- You can upload a **WhatsApp chat export** (.txt, or the .zip WhatsApp makes) and **voice notes**.\n"
        "- VERIQ looks for who was claimed, where you were asked to pay, and pressure tactics.\n"
        "- VERIQ **cannot prove fraud** and **cannot confirm that a voice is real**.\n"
        "- Never type an OTP, UPI PIN, password or card number here. VERIQ never asks for them.\n"
        "- This prototype keeps your files in memory for this session only and writes nothing to disk. "
        "Use **Delete my data** (left menu) to clear them. Closing the server also clears them.")
    ok = st.checkbox("This is my own conversation (or I have permission), and I agree to have it analysed here.", key="consent")
    if st.button("Continue", key="c1", disabled=not ok):
        S.consented = True
        go(2)
        st.rerun()

# ---------------------------------------------------------------- 2 upload ----
elif S.step == 2:
    st.header("2 · Upload the chat")
    tab_up, tab_demo = st.tabs(["Upload my chat", "Try a synthetic demo"])
    with tab_up:
        chat = st.file_uploader("WhatsApp chat export (.txt or .zip, up to 2 MB of text)", type=["txt", "zip"], key="chatfile")
        voices = st.file_uploader("Voice notes (optional): .opus .ogg .m4a .mp3 .wav", type=["opus", "ogg", "m4a", "mp3", "wav", "aac"],
                                  accept_multiple_files=True, key="voicefiles")
        if st.button("Check files", key="check_files", disabled=chat is None):
            intake = Intake()
            try:
                add_chat(intake, chat.name, chat.getvalue())
                for v in voices or []:
                    add_audio(intake, v.name, v.getvalue())
                text = decode_text(intake.chat.data)
            except IntakeError as e:
                st.error(str(e))
            else:
                S.demo = None
                S.chat_text = text
                S.audio = {a.name: a.data for a in intake.audio}
                S.files = [{"name": intake.chat.name, "kind": "chat", "sha256": intake.chat.sha256}] + [
                    {"name": a.name, "kind": "audio", "sha256": a.sha256} for a in intake.audio]
                S.intake_warnings = intake.warnings
                S.transcripts = {}
    with tab_demo:
        st.write("Fictional chats for trying VERIQ. Their results are **hand-written stub values** until the rules engine is connected.")
        sid = st.radio("Scenario", ["A", "B", "C"], format_func=lambda x: load_demo(x)["title"], key="demo_pick")
        if st.button("Load this demo", key="load_demo"):
            fx = load_demo(sid)
            S.demo = sid
            S.chat_text = fx["chat"]
            S.audio = {}
            S.transcripts = fx["transcripts"]
            S.files = [{"name": f"demo_scenario_{sid}.txt", "kind": "chat", "sha256": sha256(fx["chat"].encode())}]
            S.intake_warnings = []
            S.claimed_firm = fx["claimed_firm"]
            S.checks = {k: {"name": v[0], "source": v[1], "date": date.fromisoformat(fx["as_of"])} for k, v in fx["checks"].items()}
    if S.get("chat_text"):
        ex = extract(S.case_id, S.chat_text, S.get("transcripts"))
        S.payee_values = [p.value_norm for p in payee_list(ex.indicators)]
        st.success(f"Read {len(ex.messages)} messages · found {len(S.payee_values)} payment destination(s).")
        for f in S.files:
            st.caption(f"✓ {f['name']} ({f['kind']}) · SHA-256 {f['sha256'][:16]}…")
        for w in S.get("intake_warnings", []) + ex.warnings:
            st.warning(w)
        if ex.is_stub:
            st.info(f"Extraction: {ex.source}.")
        if S.get("demo"):
            st.info(f"Demo {S.demo} loaded. All names and IDs are fictional.")
        if st.button("Continue", key="c2", disabled=not ex.messages):
            go(3)
            st.rerun()

# ---------------------------------------------------------------- 3 confirm ----
elif S.step == 3:
    st.header("3 · Who do you believe you are dealing with?")
    ex = extract(S.case_id, S.chat_text, S.get("transcripts"))
    firms = [i.value_raw for i in ex.indicators if i.type == "firm_name"]
    if firms:
        st.caption("Firm names mentioned in the chat: " + ", ".join(md_escape(f) for f in dict.fromkeys(firms)))
    S.claimed_firm = st.text_input("Name of the firm the sender claimed to be", value=S.get("claimed_firm", ""), key="firm_input",
                                   max_chars=120, help="Type the firm's name as you understood it, e.g. 'Navyug Wealth Research Pvt Ltd'.")
    st.subheader("Where you were asked to pay")
    st.caption("Each destination is checked separately. They are never merged.")
    msgs = {m.msg_id: m for m in ex.messages}
    for n, p in enumerate(payee_list(ex.indicators), 1):
        m = msgs.get(p.msg_id)
        with st.container(border=True):
            kind = "UPI ID" if p.type == "upi_vpa" else "Bank account"
            st.markdown(f"**{n}. {kind}: {md_escape(p.value_raw)}**")
            amt = amount_in(m.text if m else "")
            src = "a voice-note transcript (check it against what you heard)" if p.source == "voice" else "the message text"
            st.caption(f"Message #{p.msg_id} · {m.ts if m else ''} · {amt or 'amount not stated'} · found in {src} · confidence {p.confidence}")
    if not payee_list(ex.indicators):
        st.warning("No UPI ID or account number was found, so there is nothing to check yet.")
    c1, c2 = st.columns(2)
    if c1.button("Back", key="b3"):
        go(2)
        st.rerun()
    if c2.button("Continue", key="c3"):
        if not S.claimed_firm.strip():
            st.warning("No firm entered: every payee will stay unverified.")
        go(4)
        st.rerun()

# ---------------------------------------------------------------- 4 payee names ----
elif S.step == 4:
    st.header("4 · What name does your bank app show?")
    st.info("For each payee: start a payment in **your own** bank or UPI app, stop at the screen that shows the payee's name, "
            "read it, then **cancel**. Never enter your PIN. What you type here is recorded as **user-reported**: VERIQ "
            "cannot see your app and does not contact any bank, UPI provider or SEBI.")
    S.setdefault("checks", {})
    ex = extract(S.case_id, S.chat_text, S.get("transcripts"))
    for n, p in enumerate(payee_list(ex.indicators), 1):
        prev = S.checks.get(p.value_norm, {"name": "", "source": SOURCES[1 if p.type == "upi_vpa" else 0], "date": date.today()})
        with st.container(border=True):
            st.markdown(f"**{n}. {md_escape(p.value_raw)}**")
            name = st.text_input("Exact name shown (leave blank if you couldn't check)", value=prev["name"], key=f"nm_{p.value_norm}", max_chars=120)
            src = st.selectbox("Where you saw it", SOURCES, index=SOURCES.index(prev["source"]), key=f"src_{p.value_norm}")
            when = st.date_input("Date you checked", value=prev["date"], max_value=date.today(), key=f"dt_{p.value_norm}")
            st.caption("User-reported" if name.strip() else "Missing: this payee will stay unverified.")
            S.checks[p.value_norm] = {"name": name, "source": src, "date": when}
    c1, c2 = st.columns(2)
    if c1.button("Back", key="b4"):
        go(3)
        st.rerun()
    if c2.button("Get the answer", key="c4"):
        go(5)
        st.rerun()

# ---------------------------------------------------------------- 5 answer ----
elif S.step == 5:
    fx = load_demo(S.demo) if S.get("demo") else None
    case = build_case(case_id=S.case_id, chat_text=S.chat_text, claimed_firm=S.get("claimed_firm", ""),
                      checks={k: UserCheck(v["name"], v["source"], v["date"]) for k, v in S.get("checks", {}).items()},
                      audio=S.get("audio"), files=S.get("files"), transcripts=S.get("transcripts"), fixture=fx)
    S.case = case
    st.header("5 · The answer")
    if case.bundle.is_stub:
        st.warning(f"**v0 stub:** results come from {case.bundle.source}. They are not a real rules-engine decision.")
        for n in case.bundle.notes:
            st.caption(n)
    overall = case.case_result()
    if overall:
        st.subheader(f"{ICON.get(overall, '')} Overall: {PLAIN_LABEL[overall]} ({overall})")
        if overall == "NO_MAJOR_ISSUE":
            st.markdown(f"**{NOT_A_GUARANTEE}**")
    else:
        st.subheader("No payment destination found, so nothing could be checked.")
    S.money_sent = st.toggle("I have already sent money", value=S.get("money_sent", False), key="money_toggle",
                             help="Changes only the next step (to the 1930 reporting path). It does not change any result.")
    if case.voice_is_stub or any(get(v, "model_version", "").startswith("stub") for v in case.voice):
        st.caption("Voice results shown here are stub values: no voice detector is connected in this v0 build.")
    ev_by_id = {get(e, "evidence_id"): e for e in case.evidence}
    msgs = {m.msg_id: m for m in case.extraction.messages}
    for n, p in enumerate(case.payees, 1):
        d = with_money_sent(case.result_for(p.id), S.money_sent)
        res = get(d, "result")
        with st.container(border=True):
            st.markdown(f"### {ICON.get(res, '')} {n}. {md_escape(p.value_raw)}")
            st.markdown(f"**{PLAIN_LABEL.get(res, res)}** · {code(res)} · rule {code(get(d, 'rule_id'))}")
            for r in get(d, "reasons") or []:
                st.markdown(f"- {md_escape(r)}")
            ids = list(get(d, "evidence_ids") or [])
            if ids:
                for eid in ids:
                    e = ev_by_id.get(eid)
                    if e is None:
                        continue
                    st.markdown(
                        f"**Evidence {code(eid)}** (class {md_escape(evidence_class(e))}, {md_escape(get(e, 'lane'))})  \n"
                        f"Claimed: {md_escape(get(e, 'claimed'))}  \nObserved: **{md_escape(get(e, 'observed'))}**  \n"
                        f"Source: {md_escape(get(e, 'source'))} · Date: {md_escape(get(e, 'as_of'))} · Rule: {md_escape(get(d, 'rule_id'))}  \n"
                        f"Limitation: _{md_escape(get(e, 'limitation'))}_")
            else:
                st.caption("Evidence: none entered for this payee. Missing evidence is not a match.")
            m = msgs.get(p.msg_id)
            if m is not None and m.kind == "voice":
                v = next((v for v in case.voice if get(v, "file_id") == m.media_ref), None)
                if v is not None:
                    st.caption(f"Found in a voice note. Voice check: {get(v, 'state')} · {'; '.join(get(v, 'reasons') or [])} "
                               f"· model: {get(v, 'model_version')}. A voice result can raise concern but never clears a payee.")
            st.info(f"**Next step:** {display_next_step(d)}")
    with st.expander("Timeline: what was said (not whether it is true)"):
        for m in case.extraction.messages:
            st.markdown(f"`#{m.msg_id}` {md_escape(m.ts or '')} · **{md_escape(m.sender)}** ({m.kind}): {md_escape(m.text or '(no text)')}")
        if case.extraction.cues:
            st.markdown("**Pressure cues (review only, not proof):** " + "; ".join(
                f"#{c.msg_id} {c.type} ({c.severity})" for c in case.extraction.cues))
    st.caption(STANDING_LINE)
    c1, c2 = st.columns(2)
    if c1.button("Back", key="b5"):
        go(4)
        st.rerun()
    if c2.button("Make the reports", key="c5"):
        go(6)
        st.rerun()

# ---------------------------------------------------------------- 6 reports ----
elif S.step == 6:
    case = S.case
    st.header("6 · Reports")
    st.write("Two drafts: a **filing sheet** for you (full details, for 1930 / cybercrime.gov.in) and a **shareable summary** "
             "with account numbers cut to the last four digits. Neither is filed anywhere.")
    with st.expander("Add details only you know (optional; left blank otherwise)", expanded=S.get("money_sent", False)):
        user = {"mobile": st.text_input("Your mobile number", key="u_mobile"),
                "bank": st.text_input("Bank, wallet or merchant the money left from", key="u_bank"),
                "account": st.text_input("Your account or UPI ID that was debited", key="u_account"),
                "screenshots": st.text_input("Screenshots you have (file names)", key="u_shots")}
        per = {}
        for p in case.payees:
            st.markdown(f"**Payment to {md_escape(p.value_raw)}**")
            per[p.id] = {"utr": st.text_input("12-digit transaction ID (UTR)", key=f"utr_{p.id}", max_chars=22),
                         "paid_on": st.text_input("Date paid", key=f"pd_{p.id}"),
                         "amount_paid": st.text_input("Amount paid", key=f"ap_{p.id}")}
    data = report_data(case, money_sent=S.get("money_sent", False), user=user, per_payee=per)
    c1, c2 = st.columns(2)
    c1.download_button("Filing sheet (HTML)", filing_sheet_html(data), file_name=f"veriq_filing_sheet_{case.case_id}.html", mime="text/html", key="dl1")
    c2.download_button("Filing sheet (Markdown)", filing_sheet_md(data), file_name=f"veriq_filing_sheet_{case.case_id}.md", mime="text/markdown", key="dl2")
    c3, c4 = st.columns(2)
    c3.download_button("Shareable summary (HTML)", summary_html(data), file_name=f"veriq_summary_{case.case_id}.html", mime="text/html", key="dl3")
    c4.download_button("Shareable summary (Markdown)", summary_md(data), file_name=f"veriq_summary_{case.case_id}.md", mime="text/markdown", key="dl4")
    with st.expander("Preview the shareable summary"):
        st.markdown(summary_md(data))
    st.caption(STANDING_LINE)
    if st.button("Back", key="b6"):
        go(5)
        st.rerun()
