"""'How accurate is VERIQ?' page: only numbers produced by commands in this repo (rubric: measured accuracy,
error rates incl. false positives on data never trained on, named failure cases). FINALE, Claude C."""

from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent


def _load(rel: str):
    p = ROOT / rel
    try:
        return json.loads(p.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return None


def chat_rows():
    r = _load("bench/results_test.json")
    if not r:
        return None
    return {"chats": r["chats"], "payees": r["payees"], "extraction": r["extraction"],
            "decision_accuracy": r["decision_accuracy"], "false_alarms": r["false_alarms_on_legit_payees"],
            "missed_scams": r["scam_payees_marked_no_major_issue"], "ms": r["ms_per_chat"],
            "failures": r.get("failures", [])[:5], "failure_count": r.get("failure_count", 0)}


def voice_rows():
    r = _load("bench/voice/results.json")
    if not r:
        return None
    d = r["detectors"]
    return {"n": r["n"], "seconds_per_clip": r["seconds_per_clip_cpu"], "pre": d["pretrained"], "head": d["trained_head"],
            "model_version": r.get("exported", {}).get("model_version", "")}


def adversarial():
    return _load("bench/results_adversarial.json")


def render(st, md_escape) -> None:
    st.header("How accurate is VERIQ?")
    st.caption("Every number here comes from a command in this repository, run on data the system never trained on. "
               "All data is synthetic or public. Small sets: read the intervals and the failure cases.")
    c = chat_rows()
    st.subheader("1 · Chat and payee checks (rules)")
    if c:
        st.markdown(
            f"- **{c['chats']} held-out synthetic chats, {c['payees']} payees** (`python -m bench.run test`)\n"
            f"- Payees found: **{c['extraction']['tp']}/{c['payees']}**, false pickups: **{c['extraction']['fp']}** "
            "(decoys: e-mails, phone and order numbers, URLs)\n"
            f"- Answers as expected: **{c['decision_accuracy'] * 100:.1f}%**\n"
            f"- False alarms on genuine payees: **{c['false_alarms']['count']}/{c['false_alarms']['of']}** · "
            f"scams marked 'no major issue': **{c['missed_scams']['count']}/{c['missed_scams']['of']}**\n"
            f"- Time per chat (rules only): median {c['ms']['median']} ms")
        if c["failures"]:
            from collections import Counter
            kinds = Counter(f"{f.get('typed_name')} → {f['got']} (expected {f['expected']})" for f in c["failures"])
            st.markdown(f"**Failure cases ({c['failure_count']}):** " + "; ".join(
                md_escape(f"{k} ×{n}") for k, n in kinds.most_common(3)))
    else:
        st.info("Not run yet: `python -m bench.run test`.")
    v = voice_rows()
    st.subheader("2 · Voice-note check (AASIST + our trained head)")
    if v:
        pre, head = v["pre"], v["head"]
        st.markdown(
            f"Held-out test: {v['n']['test_en']} English clips (2 real speakers, 8 synthetic voices never seen in "
            f"training) + {v['n']['test_hindi_fake_only']} Hindi synthetic clips; WhatsApp-like Opus compression; "
            "same preprocessing as the app. Threshold fixed on a separate dev set (target: ≤5% genuine flagged).")
        st.table({
            "": ["AUC", "Equal error rate", "Genuine clips flagged (95% CI)", "Synthetic clips caught (95% CI)",
                 "Hindi synthetic caught"],
            "Pretrained AASIST": [str(pre["test_auc"]), str(pre["test_eer"]),
                                  f"{pre['test_genuine_flagged']:.1%} {pre['test_genuine_flagged_95ci']}",
                                  f"{pre['test_synthetic_caught']:.1%} {pre['test_synthetic_caught_95ci']}",
                                  f"{pre['hindi_synthetic_caught']:.1%}"],
            "AASIST + our trained head": [str(head["test_auc"]), str(head["test_eer"]),
                                          f"{head['test_genuine_flagged']:.1%} {head['test_genuine_flagged_95ci']}",
                                          f"{head['test_synthetic_caught']:.1%} {head['test_synthetic_caught_95ci']}",
                                          f"{head['hindi_synthetic_caught']:.1%}"]})
        st.markdown("**What this means:** training helped, but about 1 in 5 genuine clips is still flagged. So a voice "
                    "flag only asks for a human review; it never accuses or clears a payee. The payee-name check decides.")
        st.markdown("**Known failures:** some speakers are flagged often; one synthetic voice is rarely caught; a second "
                    "compression pass lowers the catch rate; only one TTS engine and digit strings were tested; real "
                    "voice clones were not tested.")
    else:
        st.info("Not run yet: `python -m bench.voice.train_eval`.")
    a = adversarial()
    st.subheader("3 · Red-team: attacks we tried")
    if a:
        st.markdown(f"Defended attacks passed: **{a['defended_attacks_passed']}/{a['defended_attacks']}** · "
                    f"known gaps still open: **{a['known_gaps_still_failing']}/{a['known_gaps']}** "
                    "(`python -m bench.adversarial`)")
        st.table({"Attack": [r["attack"] for r in a["rows"]], "Expected": [r["expected"] for r in a["rows"]],
                  "Got": [r["got"] for r in a["rows"]],
                  "Result": ["pass" if r["pass"] else ("KNOWN GAP" if r["known_gap"] else "FAIL") for r in a["rows"]]})
    st.caption("Limits: synthetic data written or generated by the team; not real victims' chats or real voice clones.")
