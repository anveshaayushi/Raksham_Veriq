"""VERIQ app. Run from the repo root:  streamlit run app/streamlit_app.py

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

from registry.sqlite_registry import WORDING as REGISTRY_WORDING  # noqa: E402
from app.case import FIXTURES, UserCheck, build_case, demo_inputs, demo_title, extract, load_demo, report_data  # noqa: E402
from app.adapters.extract import amount_in, payees as payee_list  # noqa: E402
from app.adapters.voice import observed_for_display, score_display as voice_score_display  # noqa: E402
from app.contracts import SCHEMA_SOURCE, evidence_class, get  # noqa: E402
from app.evidence_input import SOURCES  # noqa: E402
from app.intake import Intake, IntakeError, add_audio, add_chat, add_image, decode_text, sha256  # noqa: E402
from app.overturn import REASONS as OVERTURN_REASONS, Ledger, is_valid_handle  # noqa: E402
from rules import HIGH_PRESSURE  # noqa: E402
from app.next_steps import NOT_A_GUARANTEE, PLAIN_LABEL, STANDING_LINE, display_next_step, with_money_sent  # noqa: E402
from app.text_safety import code, md_escape  # noqa: E402
from report.build import filing_sheet_html, filing_sheet_md, incident_json, summary_html, summary_md  # noqa: E402

DEMO_QR = ROOT / "app" / "demo_media" / "demo_qr_synthetic.png"
DEMO_VOICE = {"fake": ROOT / "app" / "demo_media" / "demo_voice_synthetic_tts.wav",
              "real": ROOT / "app" / "demo_media" / "demo_voice_real_human.wav"}

STEPS = ["Start", "Chat", "Firm", "Bank name", "Answer", "Report"]
ICON = {"LINKED": "🔗", "NAME_DISCREPANCY": "⛔", "REGISTRATION_CONFLICT": "⛔", "HUMAN_REVIEW": "⚠️", "INCONCLUSIVE": "❔",
        "NO_MAJOR_ISSUE": "✅"}
# One-line, plain headline per result (the full rule, evidence and limitation stay one click away under "Details").
SEVERITY = {"LINKED": "error", "NAME_DISCREPANCY": "error", "REGISTRATION_CONFLICT": "error",
            "HUMAN_REVIEW": "warning", "INCONCLUSIVE": "warning", "NO_MAJOR_ISSUE": "success"}
HEADLINE = {"LINKED": "Don't pay. Other people have reported this payee.",
            "NAME_DISCREPANCY": "Don't pay yet. The money would go to someone else.",
            "REGISTRATION_CONFLICT": "Don't pay yet. The registration they quoted doesn't check out.",
            "HUMAN_REVIEW": "Hold on. Get a second opinion before you pay.",
            "INCONCLUSIVE": "Not sure yet. Check the payee's name in your bank app first.",
            "NO_MAJOR_ISSUE": "No major issue found."}

st.set_page_config(page_title="VERIQ · check before you pay", page_icon="🛡️", layout="centered")
st.markdown(
    """<style>
    html, body, [class*="css"] {font-size: 18px;}
    .block-container {max-width: 780px; padding-top: 2.2rem;}
    h1 {letter-spacing: -0.02em; margin-bottom: 0;}
    div[data-testid="stButton"] button, div[data-testid="stDownloadButton"] button, .stButton>button, .stDownloadButton>button {width: 100%; min-height: 3rem; font-size: 1.02rem; font-weight: 600;
        border-radius: 12px;}
    div[data-testid="stCaptionContainer"] {font-size: 0.92rem;}
    div[data-testid="stVerticalBlockBorderWrapper"] {border-radius: 14px;}
    div[data-testid="stAlert"] {border-radius: 12px;}
    div[data-testid="stExpander"] details {border-radius: 12px;}
    [data-testid="stAppDeployButton"], footer {display: none;}
    button[kind="primary"] {background: #2563eb; border-color: #2563eb; color: #fff;}
    button[kind="primary"]:hover {background: #1d4ed8; border-color: #1d4ed8; color: #fff;}
    .vq-steps {display: flex; flex-wrap: wrap; gap: 6px; margin: 0.4rem 0 1.2rem 0;}
    .vq-step {padding: 4px 12px; border-radius: 999px; font-size: 0.82rem; border: 1px solid rgba(128,128,128,0.35);
        opacity: 0.6;}
    .vq-step.done {opacity: 0.85;}
    .vq-step.cur {opacity: 1; background: #2563eb; border-color: #2563eb; color: #fff; font-weight: 600;}
    </style>""",
    unsafe_allow_html=True,  # constant CSS only; never user content
)

from app.config import apply as apply_config  # noqa: E402

CFG = apply_config()  # environment settings (Q4): data dir, registry, upload limit, language, offline mode
S = st.session_state
S.setdefault("step", 1)
S.setdefault("case_id", "case-" + uuid.uuid4().hex[:8])
S.setdefault("ledger", Ledger())


def go(n: int) -> None:
    S.step = n


def show_evidence(e, rule_id, cited: bool) -> None:
    """One finding: claimed, observed, source, date, rule, limitation (brief 3.3). Chat-derived text is escaped."""
    lane = get(e, "lane")
    st.markdown(
        f"**Evidence {code(get(e, 'evidence_id'))}** (class {md_escape(evidence_class(e))}, {md_escape(lane)})"
        f"{' · used for this result' if cited else ' · shown for context, not used for this result'}  \n"
        f"Claimed: {md_escape(get(e, 'claimed'))}  \nObserved: **{md_escape(observed_for_display(lane, get(e, 'observed')))}**  \n"
        f"Source: {md_escape(get(e, 'source'))} · Date: {md_escape(get(e, 'as_of'))}"
        f"{' · Rule: ' + md_escape(rule_id) if (rule_id and cited) else ''}  \n"
        f"Limitation: _{md_escape(get(e, 'limitation'))}_")


def reset() -> None:
    for k in list(S.keys()):
        del S[k]


def stepper(cur: int) -> None:
    """Step pills. Built from the constant STEPS list only (never user content)."""
    pills = "".join(f'<span class="vq-step {"cur" if i == cur else "done" if i < cur else ""}">{i} · {name}</span>'
                    for i, name in enumerate(STEPS, 1))
    st.markdown(f'<div class="vq-steps">{pills}</div>', unsafe_allow_html=True)


def observed_name(p) -> str:
    return str((S.get("checks", {}).get(p.value_norm) or {}).get("name", "")).strip()


def plain_why(res: str, p, d) -> str:
    """One plain sentence for a payee's result. Falls back to the engine's first reason. Chat/user text is escaped."""
    obs, firm = observed_name(p), str(S.get("claimed_firm", "")).strip()
    if res == "NAME_DISCREPANCY" and obs:
        return f"Your bank app shows **{md_escape(obs)}**, but the chat said **{md_escape(firm or 'a different firm')}**."
    if res == "REGISTRATION_CONFLICT":
        return "The SEBI registration number quoted in the chat is not on the dated list for that firm."
    if res == "LINKED":
        return "Other people have reported losing money to this payee."
    if res == "INCONCLUSIVE" and not obs:
        return "You haven't checked which name your bank app shows for this payee."
    if res == "NO_MAJOR_ISSUE" and obs:
        return f"Your bank app shows **{md_escape(obs)}**, which matches the firm."
    reasons = [str(r).replace(HIGH_PRESSURE, "").strip() for r in (get(d, "reasons") or [])]
    return md_escape(reasons[0]) if reasons else PLAIN_LABEL.get(res, res)


# ---------------------------------------------------------------- header ----
st.title("🛡️ VERIQ")
st.write("Check who you're **really** paying, before you pay.")
if S.get("page", "Check a chat") == "Check a chat" and not S.get("show_results"):
    stepper(S.step)
with st.sidebar:
    st.subheader("Your data")
    st.write("Stays in this session only. Nothing is saved to disk.")
    if st.button("Delete my data and start again", key="reset"):
        reset()
        st.rerun()
    st.caption(STANDING_LINE)
    PAGES = ["Check a chat", "Scenario player", "Kit runner (judges)", "Plan vs delivered", "Privacy proof"]
    _judge_open = S.get("page", PAGES[0]) != PAGES[0] or S.get("show_results", False) or S.get("reviewer_mode", False)
    with st.expander("For judges and reviewers", expanded=_judge_open):
        S.show_results = st.toggle("How accurate is VERIQ? (measured results)", value=S.get("show_results", False),
                                   key="results_toggle")
        S.reviewer_mode = st.toggle("Reviewer view (fraud desk / second person)", value=S.get("reviewer_mode", False),
                                    key="rev_toggle", help="Shows review requests and lets a reviewer uphold or overturn them.")
        S.page = st.radio("Pages", PAGES, index=PAGES.index(S.get("page", PAGES[0])), key="page_radio")
        st.caption(f"Contract: {SCHEMA_SOURCE}")

# ---------------------------------------------------------------- other pages (Q3) ----
if S.get("page", "Check a chat") != "Check a chat" and not S.get("show_results"):
    from app.views import kit as _kit, plan as _plan, player as _player, privacy as _privacy
    {"Scenario player": _player, "Kit runner (judges)": _kit, "Plan vs delivered": _plan,
     "Privacy proof": _privacy}[S.page].render(st)
    st.stop()

# ---------------------------------------------------------------- results page ----
if S.get("show_results"):
    from app.results_page import render as render_results
    render_results(st, md_escape)
    st.stop()

# ---------------------------------------------------------------- 1 consent ----
if S.step == 1:
    st.header("Before you start")
    st.markdown("Add the chat where someone asked you for money. VERIQ checks **who would actually receive it**.")
    st.markdown("🔒 Never type an OTP, UPI PIN or password here. VERIQ never asks for them.")
    with st.expander("What VERIQ can and can't do"):
        st.markdown(
            "- You can upload a **WhatsApp chat export** (.txt, or the .zip WhatsApp makes) and **voice notes**.\n"
            "- VERIQ looks for who was claimed, where you were asked to pay, and pressure tactics.\n"
            "- VERIQ **cannot prove fraud** and **cannot confirm that a voice is real**.\n"
            "- This prototype keeps your files in memory for this session only and writes nothing to disk. "
            "Use **Delete my data** (left menu) to clear them. Closing the server also clears them.")
    ok = st.checkbox("This is my own conversation (or I have permission), and I agree to have it analysed here.", key="consent")
    if st.button("Continue", key="c1", type="primary", disabled=not ok):
        S.consented = True
        go(2)
        st.rerun()

# ---------------------------------------------------------------- 2 upload ----
elif S.step == 2:
    st.header("Add the chat")
    tab_up, tab_demo = st.tabs(["Upload my chat", "Try a synthetic demo"])
    with tab_up:
        chat = st.file_uploader("WhatsApp chat export (.txt or .zip)", type=["txt", "zip"], key="chatfile",
                                help="In WhatsApp: open the chat → ⋮ → More → Export chat → Without media. Up to 2 MB of text.")
        pasted = st.text_area("…or paste the chat here", key="pasted", height=140, max_chars=200_000,
                              placeholder="20/10/2026, 8:59 pm - Name: message")
        with st.expander("Add voice notes or screenshots (optional)"):
            voices = st.file_uploader("Voice notes: .opus .ogg .m4a .mp3 .wav", type=["opus", "ogg", "m4a", "mp3", "wav", "aac"],
                                      accept_multiple_files=True, key="voicefiles")
            imgs = st.file_uploader("Screenshots or QR images: .jpg .png .webp (UPI QR codes in them are read)",
                                    type=["jpg", "jpeg", "png", "webp"], accept_multiple_files=True, key="imagefiles")
        if st.button("Check files", key="check_files", type="primary", disabled=chat is None and not pasted.strip()):
            intake = Intake()
            try:
                if chat is not None:
                    add_chat(intake, chat.name, chat.getvalue())
                else:
                    add_chat(intake, "pasted_chat.txt", pasted.encode("utf-8"))
                for v in voices or []:
                    add_audio(intake, v.name, v.getvalue())
                for im in imgs or []:
                    add_image(intake, im.name, im.getvalue())
                text = decode_text(intake.chat.data)
            except IntakeError as e:
                st.error(str(e))
            else:
                S.demo = None
                S.chat_text = text
                S.audio = {a.name: a.data for a in intake.audio}
                S.images = {i.name: i.data for i in intake.images}
                S.files = [{"name": intake.chat.name, "kind": "chat", "sha256": intake.chat.sha256}] + [
                    {"name": a.name, "kind": "audio", "sha256": a.sha256} for a in intake.audio] + [
                    {"name": i.name, "kind": "image", "sha256": i.sha256} for i in intake.images]
                S.intake_warnings = intake.warnings
                S.transcripts = {}
    with tab_demo:
        st.caption("Fictional chats (all names and IDs invented). Answers come from the same engine as an upload.")
        sid = st.radio("Scenario", list(FIXTURES), format_func=lambda x: demo_title(load_demo(x)), key="demo_pick")
        add_qr = st.checkbox("Also attach a QR screenshot (synthetic)", key="demo_qr")
        add_voice = st.checkbox("Attach audio for the voice note", key="demo_voice",
                                help="A held-out test clip: synthetic TTS for A and C, a real human recording for B.")
        if st.button("Load this demo", key="load_demo", type="primary"):
            fx = load_demo(sid)
            di = demo_inputs(fx)
            S.demo = sid
            S.case_id = di["case_id"]
            S.chat_text = di["chat_text"]
            S.audio = {}
            if add_voice:
                refs = [v["file_id"] for v in fx["expected"]["voice_results"]]
                clip = DEMO_VOICE["real" if sid == "B" else "fake"]
                S.audio = {r: clip.read_bytes() for r in refs}
            S.images = {DEMO_QR.name: DEMO_QR.read_bytes()} if add_qr else {}
            S.transcripts = di["transcripts"]
            demo_audio_files = [{"name": f"{r} (held-out test clip)", "kind": "audio", "sha256": sha256(b)} for r, b in S.audio.items()]
            S.files = [{"name": f"{fx['fixture_id']}.txt (synthetic demo chat)", "kind": "chat", "sha256": sha256(di["chat_text"].encode())}] + (
                [{"name": DEMO_QR.name, "kind": "image", "sha256": sha256(S.images[DEMO_QR.name])}] if add_qr else []) + demo_audio_files
            S.intake_warnings = []
            S.claimed_firm = di["claimed_firm"]
            S.checks = di["checks"]
    if S.get("chat_text"):
        ex = extract(S.case_id, S.chat_text, S.get("transcripts"), load_demo(S.demo) if S.get("demo") else None, S.get("images"))
        S.payee_values = [p.value_norm for p in payee_list(ex.indicators)]
        st.success(f"Read {len(ex.messages)} messages · found {len(S.payee_values)} place(s) you were asked to pay."
                   + (f" Demo {S.demo}: all names and IDs are fictional." if S.get("demo") else ""))
        for w in S.get("intake_warnings", []) + ex.warnings:
            st.warning(w)
        if ex.is_stub:
            st.info(f"Extraction: {ex.source}.")
        with st.expander(f"Files received ({len(S.files)})"):
            for f in S.files:
                st.caption(f"✓ {f['name']} ({f['kind']}) · SHA-256 {f['sha256'][:16]}…")
        if st.button("Continue", key="c2", type="primary", disabled=not ex.messages):
            go(3)
            st.rerun()

# ---------------------------------------------------------------- 3 confirm ----
elif S.step == 3:
    st.header("Who did they say they were?")
    ex = extract(S.case_id, S.chat_text, S.get("transcripts"), load_demo(S.demo) if S.get("demo") else None, S.get("images"))
    firms = [i.value_raw for i in ex.indicators if i.type == "firm_name"]
    S.claimed_firm = st.text_input("Firm or person they claimed to be", value=S.get("claimed_firm", ""), key="firm_input",
                                   max_chars=120, placeholder="e.g. Navyug Wealth Research Pvt Ltd")
    if firms:
        st.caption("Mentioned in the chat: " + ", ".join(md_escape(f) for f in dict.fromkeys(firms)))
    st.subheader("Where you were asked to pay")
    msgs = {m.msg_id: m for m in ex.messages}
    found = payee_list(ex.indicators)
    with st.container(border=True):
        for n, p in enumerate(found, 1):
            m = msgs.get(p.msg_id)
            kind = "UPI ID" if p.type == "upi_vpa" else "Bank account"
            amt = amount_in(m.text if m else "")
            st.markdown(f"**{n}.** {kind} **{md_escape(p.value_raw)}**" + (f" · {md_escape(amt)}" if amt else ""))
        if not found:
            st.caption("Nothing found yet.")
    if found:
        with st.expander("Where each one was found"):
            st.caption("Each destination is checked separately. They are never merged.")
            for n, p in enumerate(found, 1):
                m = msgs.get(p.msg_id)
                amt = amount_in(m.text if m else "")
                src = {"voice": "a voice-note transcript (check it against what you heard)",
                       "image": f"a QR code in {md_escape(m.media_ref if m else 'an image')}"}.get(p.source, "the message text")
                st.caption(f"{n}. Message #{p.msg_id} · {m.ts if m else ''} · {amt or 'amount not stated'} · found in {src} · "
                           f"confidence {p.confidence}")
    if not found:
        st.warning("No UPI ID or account number was found, so there is nothing to check yet.")
    c1, c2 = st.columns(2)
    if c1.button("Back", key="b3"):
        go(2)
        st.rerun()
    if c2.button("Continue", key="c3", type="primary"):
        if not S.claimed_firm.strip():
            st.warning("No firm entered: every payee will stay unverified.")
        go(4)
        st.rerun()

# ---------------------------------------------------------------- 4 payee names ----
elif S.step == 4:
    st.header("What name does your bank app show?")
    st.info("In **your own** bank or UPI app, start a payment to each ID below, **read the name it shows, then cancel**. "
            "Never enter your PIN.")
    with st.expander("Why this matters"):
        st.caption("Scammers use real-sounding firm names in chat, but the bank shows who actually owns the account. "
                   "What you type is recorded as **user-reported**: VERIQ cannot see your app and does not contact any "
                   "bank, UPI provider or SEBI.")
    S.setdefault("checks", {})
    ex = extract(S.case_id, S.chat_text, S.get("transcripts"), load_demo(S.demo) if S.get("demo") else None, S.get("images"))
    for n, p in enumerate(payee_list(ex.indicators), 1):
        prev = S.checks.get(p.value_norm, {"name": "", "source": SOURCES[1 if p.type == "upi_vpa" else 0], "date": date.today()})
        with st.container(border=True):
            st.markdown(f"**{n}. {md_escape(p.value_raw)}**")
            if p.source == "image":
                st.caption("From a QR code: type the name **your app** shows, not the one inside the QR.")
            if is_valid_handle(p.value_norm):
                st.caption("'@valid' format alone proves nothing: confirm the firm on SEBI Check.")
            name = st.text_input("Name shown (leave blank if you couldn't check)", value=prev["name"], key=f"nm_{p.value_norm}",
                                 max_chars=120)
            with st.expander("Where and when you checked"):
                src = st.selectbox("Where you saw it", SOURCES, index=SOURCES.index(prev["source"]), key=f"src_{p.value_norm}")
                when = st.date_input("Date you checked", value=prev["date"], max_value=date.today(), key=f"dt_{p.value_norm}")
            st.caption("✓ User-reported" if name.strip() else "Not checked: this payee will stay unverified.")
            S.checks[p.value_norm] = {"name": name, "source": src, "date": when}
    c1, c2 = st.columns(2)
    if c1.button("Back", key="b4"):
        go(3)
        st.rerun()
    if c2.button("Get the answer", key="c4", type="primary"):
        go(5)
        st.rerun()

# ---------------------------------------------------------------- 5 answer ----
elif S.step == 5:
    fx = load_demo(S.demo) if S.get("demo") else None
    case = build_case(case_id=S.case_id, chat_text=S.chat_text, claimed_firm=S.get("claimed_firm", ""),
                      checks={k: UserCheck(v["name"], v["source"], v["date"]) for k, v in S.get("checks", {}).items()},
                      audio=S.get("audio"), files=S.get("files"), transcripts=S.get("transcripts"), fixture=fx,
                      images=S.get("images"))
    S.case = case
    ledger: Ledger = S.ledger
    st.header("The answer")
    if S.get("reviewer_mode"):
        with st.container(border=True):
            st.subheader("Reviewer view")
            pending = [r for r in ledger.requests.values() if r.status == "review requested"]
            if not pending:
                st.caption("No review requests waiting.")
            for r in pending:
                st.markdown(f"**{md_escape(r.payee_label)}** · original result {code(r.original_result)} · {r.elapsed()}  \n"
                            f"User's reason: {md_escape(r.reason)}  \nNote: {md_escape(r.note or '(none)')}  \n"
                            f"Reference given: {md_escape(r.reference or '(none)')}")
                if is_valid_handle(r.reference):
                    st.caption("The reference is in SEBI's @valid format. Confirm it on SEBI Check before overturning.")
                rv = st.text_input("Reviewer name", key=f"rvn_{r.payee_id}")
                rr_ = st.text_input("Reason for your decision", key=f"rvr_{r.payee_id}")
                b1, b2 = st.columns(2)
                for btn, action in ((b1, "overturned"), (b2, "upheld")):
                    if btn.button("Overturn" if action == "overturned" else "Uphold", key=f"rv_{action}_{r.payee_id}",
                                  disabled=not (rv.strip() and rr_.strip())):
                        from registry.sqlite_registry import from_env as _reg
                        ledger.decide(r.payee_id, action, rv, rr_, registry=_reg())
                        st.rerun()
    if case.bundle.is_stub:
        st.warning(f"**v0 stub:** results come from {case.bundle.source}. They are not a real rules-engine decision.")
        for n in case.bundle.notes:
            st.caption(n)
    overall = case.case_result()
    if overall:
        getattr(st, SEVERITY.get(overall, "info"))(f"### {ICON.get(overall, '')} {HEADLINE.get(overall, PLAIN_LABEL[overall])}")
        if CFG.lang == "hi":
            from rules.templates import LABEL as _LABEL
            st.markdown(f"**{_LABEL[overall]['hi']}**")
        if overall == "NO_MAJOR_ISSUE":
            st.markdown(f"**{NOT_A_GUARANTEE}**")
        deciding = next(p for p in case.payees if case.result_for(p.id).result == overall)
        lead = "Why" if overall == "NO_MAJOR_ISSUE" else "Why this alert fired"
        st.markdown(f"**{lead}:** " + plain_why(overall, deciding, case.result_for(deciding.id))
                    + (f" (payee {md_escape(deciding.value_raw)})" if len(case.payees) > 1 else ""))
        with st.container(border=True):
            st.markdown("**What you can do now**")
            a1, a2 = st.columns(2)
            if a1.button("🛑 I will not pay for now", key="act_nopay"):
                S.user_action = "decided not to pay for now"
            if a2.button("🔎 Check the payee name in my bank app", key="act_verify"):
                go(4)
                st.rerun()
            a3, a4 = st.columns(2)
            if a3.button("✅ This is genuine: ask a person to review", key="act_genuine"):
                S.user_action = ("asked for a review: open 'This looks wrong?' under the payee below, choose a reason "
                                 "and submit; the original answer is kept until a reviewer decides")
            from app.case import report_data as _rd
            from report.build import filing_sheet_md as _fs, summary_md as _sm
            _d = _rd(case, money_sent=S.get("money_sent", False))
            a4.download_button("📄 Report pack (text) to file yourself", _sm(_d) + "\n\n" + _fs(_d),
                               "veriq_report_pack.txt", "text/plain", key="act_pack")
            if S.get("user_action"):
                st.success(f"You {S.user_action}.")
            st.caption("VERIQ blocks nothing and contacts no one. You decide.")
    elif case.payment_links():
        st.warning("### ❔ Check before you pay. You were asked to pay through a link.")
        st.markdown("**Why:** VERIQ can't see who receives money paid through a link: "
                    + ", ".join(code(u) for u in case.payment_links()[:3])
                    + ". Don't pay through a link sent in a chat. Open the firm's official app or website yourself, "
                      "or pay a UPI ID whose name you can check in your own bank app.")
    else:
        st.subheader("No payment destination found, so nothing could be checked.")
    S.money_sent = st.toggle("I have already sent money", value=S.get("money_sent", False), key="money_toggle",
                             help="Changes only the next step (to the 1930 reporting path). It does not change any result.")
    if case.voice_is_stub or any("stub" in str(get(v, "model_version", "")).lower() for v in case.voice):
        st.caption("Voice notes were not analysed here (no audio attached), so they count for nothing either way.")
    msgs = {m.msg_id: m for m in case.extraction.messages}
    if len(case.payees) > 1:
        st.subheader(f"Each place you were asked to pay ({len(case.payees)})")
    for n, p in enumerate(case.payees, 1):
        d = with_money_sent(case.result_for(p.id), S.money_sent)
        res = get(d, "result")
        req = ledger.requests.get(p.id)
        with st.container(border=True):
            st.markdown(f"#### {ICON.get(res, '')} {md_escape(p.value_raw)}")
            st.markdown(f"**{PLAIN_LABEL.get(res, res)}.** {plain_why(res, p, d)}")
            if any(str(r).startswith(HIGH_PRESSURE) for r in get(d, "reasons") or []):
                st.error("High pressure: the voice note couldn't be checked, but the chat pushes you to pay fast to an "
                         "unverified recipient.")
            if req is not None and req.status == "overturned":
                st.success(f"Reviewed: explained. Overturned by {md_escape(req.reviewer)}: {md_escape(req.reviewer_reason)} "
                           f"({req.elapsed()}). Original result {res} stays on record. {NOT_A_GUARANTEE}")
            elif req is not None and req.status == "upheld":
                st.warning(f"Reviewed: upheld by {md_escape(req.reviewer)}: {md_escape(req.reviewer_reason)} ({req.elapsed()}).")
            elif req is not None:
                st.info(f"Review requested ({req.elapsed()}). A reviewer will uphold or overturn this result.")
            st.info(f"**Next step:** {display_next_step(d)}")
            with st.expander("Details: rule, evidence, sources"):
                st.markdown(f"Result {code(res)} · rule {code(get(d, 'rule_id'))}")
                for r in get(d, "reasons") or []:
                    st.markdown(f"- {md_escape(str(r).replace(HIGH_PRESSURE, '').strip())}")
                evs = case.evidence_for(p.id)
                if evs:
                    for e in evs:
                        show_evidence(e, get(d, "rule_id"), cited=get(e, "evidence_id") in (get(d, "evidence_ids") or []))
                else:
                    st.caption("Evidence: none entered for this payee. Missing evidence is not a match.")
                m = msgs.get(p.msg_id)
                if m is not None and m.kind == "voice":
                    v = next((v for v in case.voice if get(v, "file_id") == m.media_ref), None)
                    if v is not None:
                        st.caption(f"Found in a voice note. Voice check: {get(v, 'state')} · {md_escape('; '.join(get(v, 'reasons') or []))} "
                                   f"· {voice_score_display(v)} · model: {md_escape(get(v, 'model_version'))}. "
                                   "Weak review cue (pretrained AASIST, threshold from ASVspoof 2019 LA dev; on LA eval it "
                                   "flagged 16% of genuine clips and missed 56% of synthetic ones). Only 'flagged' can raise "
                                   "concern; a voice result never clears a payee.")
                rr = next((r for r in case.registry if get(r, "payee_id") == p.id), None)
                if rr is not None:
                    note = f" · {md_escape(get(rr, 'note'))}" if get(rr, "note") else ""
                    st.caption(f"Cross-victim registry: {md_escape(get(rr, 'status'))}{note} · "
                               f"source: {md_escape(get(rr, 'source'))}. {REGISTRY_WORDING}")
            rr = next((r for r in case.registry if get(r, "payee_id") == p.id), None)
            if rr is not None:
                from registry.sqlite_registry import from_env as _reg_env, new_reporter_token
                _r = _reg_env()
                if _r is not None and p.type in ("upi_vpa", "bank_account"):
                    if st.button("I lost money to this payee: report it (stored as a keyed hash)", key=f"rep_{p.id}"):
                        tok = S.setdefault("reporter_token", new_reporter_token())  # one token per browser session
                        out = _r.report(p.type, p.value_norm, tok)
                        S[f"rep_out_{p.id}"] = out.status + (': ' + out.note if out.note else '')
                        st.rerun()
                    if S.get(f"rep_out_{p.id}"):
                        st.caption(f"Your report: {md_escape(S[f'rep_out_{p.id}'])}. A payee is linked only after "
                                   "2 independent reporters or a reviewer.")
            if res in ("NAME_DISCREPANCY", "HUMAN_REVIEW", "REGISTRATION_CONFLICT", "LINKED") and req is None:
                with st.expander("This looks wrong? Explain and ask for a review"):
                    st.caption("You can't clear a warning yourself (a scammer could talk you into it). A reviewer "
                               "looks at your explanation; the original result stays on record.")
                    why = st.selectbox("What happened?", OVERTURN_REASONS, key=f"ow_{p.id}")
                    if why == OVERTURN_REASONS[0]:
                        st.caption("Go back to step 4 and type the name exactly as your app shows it.")
                        if st.button("Fix the name", key=f"ofix_{p.id}"):
                            go(4)
                            st.rerun()
                    else:
                        note = st.text_area("Explain in a sentence", key=f"on_{p.id}", max_chars=300)
                        ref = st.text_input("Reference (the firm's @valid UPI ID, its SEBI registration no., or a bank "
                                            "reference)", key=f"orf_{p.id}", max_chars=120)
                        if st.button("Ask for a review", key=f"oreq_{p.id}"):
                            ledger.request(p.id, p.value_norm, res, why, note, ref)
                            st.rerun()
    st.caption("More detail")
    shifts = [p for p in case.payees]
    if len(shifts) > 1:
        with st.expander(f"The payment destination changed {len(shifts) - 1} time(s)"):
            msgs_ = {m.msg_id: m for m in case.extraction.messages}
            for k, p in enumerate(shifts, 1):
                m = msgs_.get(p.msg_id)
                where = {"voice": "in a voice note", "image": "in a QR code"}.get(p.source, "in a message")
                st.markdown(f"{k}. {md_escape(m.ts if m else '')} · {code(p.value_raw)} · {where} (#{p.msg_id})")
            st.caption("Scammers often rotate payees so no single account collects many reports.")
    if case.case_level_evidence():
        with st.expander("Evidence about the whole case (registration, voice)"):
            for e in case.case_level_evidence():
                show_evidence(e, None, cited=any(get(e, "evidence_id") in (get(d, "evidence_ids") or []) for d in case.decisions))
    with st.expander("Safeguards running in this session"):
        nbytes = len(S.get("chat_text", "").encode()) + sum(len(b) for b in (S.get("audio") or {}).values()) + sum(
            len(b) for b in (S.get("images") or {}).values())
        st.markdown(
            f"- **Your files stay in memory**: {len(S.get('files', []))} file(s), {nbytes:,} bytes, this browser session "
            "only. Voice notes are written to a private temp folder for decoding and deleted at once. *Delete my data* "
            "(left menu) clears everything.\n"
            "- **Runs on this laptop**: no bank, UPI, SEBI or police system is contacted; nothing is filed or blocked.\n"
            "- **Every alert says why**: each result shows its rule, evidence, source, date and limitation.\n"
            "- **Weak signals can't decide**: a voice flag or a QR name only asks for review; the payee name from your "
            "own app decides.\n"
            "- **Mistakes can be fixed**: *This looks wrong?* sends a result to a reviewer; the original stays on record.\n"
            f"- **Cross-victim registry**: {REGISTRY_WORDING}")
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
    if c2.button("Make the reports", key="c5", type="primary"):
        go(6)
        st.rerun()

# ---------------------------------------------------------------- 6 reports ----
elif S.step == 6:
    case = S.case
    st.header("Reports (optional)")
    st.write("Download a report to keep or to share. **Nothing is sent anywhere.**")
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
    reviews = {pid: f"{r.status}" + (f" by {r.reviewer}: {r.reviewer_reason}" if r.reviewer else "") + f" (original {r.original_result})"
               for pid, r in S.ledger.requests.items()}
    data = report_data(case, money_sent=S.get("money_sent", False), user=user, per_payee=per, reviews=reviews)
    c1, c3 = st.columns(2)
    c1.download_button("📄 Filing sheet for 1930", filing_sheet_html(data), file_name=f"veriq_filing_sheet_{case.case_id}.html",
                       mime="text/html", key="dl1", help="Full details, for 1930 / cybercrime.gov.in. Keep it private.")
    c3.download_button("🔗 Summary to share", summary_html(data), file_name=f"veriq_summary_{case.case_id}.html",
                       mime="text/html", key="dl3", help="Account numbers cut to the last four digits.")
    with st.expander("Other formats"):
        c2, c4 = st.columns(2)
        c2.download_button("Filing sheet (Markdown)", filing_sheet_md(data), file_name=f"veriq_filing_sheet_{case.case_id}.md", mime="text/markdown", key="dl2")
        c4.download_button("Shareable summary (Markdown)", summary_md(data), file_name=f"veriq_summary_{case.case_id}.md", mime="text/markdown", key="dl4")
        c5, c6 = st.columns(2)
        c5.download_button("Incident card for 1930 / NCRP (JSON)", incident_json(data),
                           file_name=f"veriq_incident_{case.case_id}.json", mime="application/json", key="dl5")
        c6.download_button("Review audit trail (JSON)", S.ledger.audit_json(), file_name=f"veriq_audit_{case.case_id}.json",
                           mime="application/json", key="dl6")
        st.caption("The incident card lists the fields the 1930 / cybercrime.gov.in complaint asks for. It is not an "
                   "official format and is not sent anywhere. It contains full identifiers: keep it private.")
    with st.expander("Preview the shareable summary"):
        st.markdown(summary_md(data))
    st.caption(STANDING_LINE)
    if st.button("Back", key="b6"):
        go(5)
        st.rerun()
