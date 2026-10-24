#!/usr/bin/env python3
"""Final acceptance list (Q5): every item, its command, and PASS / FAIL / NOT RUN. Writes results/ACCEPTANCE.md.

    python scripts/acceptance.py            (make acceptance)    about 3 min in the sandbox, ~10 min on the laptop
    python scripts/acceptance.py --fast     skip the full reproduction (tests + benchmarks) and the app start

Part A checks the whole build (tests, reproduction, smoke, documents). Part B replays the 2-minute demo story with the
real engine, so the demo cannot silently break: three changing payees; name matches but "pay 18% tax" -> Inconclusive;
a voice cue never clears; a second victim -> linked; a gateway never links; the filing sheet; offline; a NEW chat;
a genuine user flagged and cleared.
"""
from __future__ import annotations

import argparse
import json
import re
import subprocess
import sys
import time
from datetime import date, datetime, timedelta, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
items: list[dict] = []


def item(part: str, name: str, command: str):
    def wrap(fn):
        def run(*a):
            try:
                ok, detail = fn(*a)
            except Exception as e:  # an item that crashes fails; the list continues
                ok, detail = False, f"{type(e).__name__}: {e}"[:200]
            status = "NOT RUN" if ok is None else ("PASS" if ok else "FAIL")
            items.append({"part": part, "item": name, "command": command, "status": status, "detail": detail})
            print(f"[{status:7s}] {name}: {detail}", flush=True)
        return run
    return wrap


# ------------------------------------------------------------------------------------------------ part A ----
@item("A", "Reproduction: data, tests, coverage, random order, benchmarks", "python scripts/reproduce.py")
def a_reproduce(fast):
    if fast:
        return None, "skipped (--fast)"
    r = subprocess.run([sys.executable, str(ROOT / "scripts" / "reproduce.py")], cwd=ROOT, capture_output=True, text=True)
    rep = json.loads((ROOT / "results" / "reproduce.json").read_text(encoding="utf-8"))
    fails = [c["check"] for c in rep["checks"] if c["status"] == "FAIL"]
    tests = next((c["detail"] for c in rep["checks"] if c["check"] == "full test suite"), "")
    return r.returncode == 0 and not fails, (tests + (f"; FAILED: {fails}" if fails else "; all reproduction checks pass"))


@item("A", "Smoke test (fresh install, offline, app health)", "python scripts/smoke.py")
def a_smoke(fast):
    r = subprocess.run([sys.executable, str(ROOT / "scripts" / "smoke.py")] + (["--no-app"] if fast else []), cwd=ROOT,
                       capture_output=True, text=True)
    last = [ln for ln in r.stdout.splitlines() if ln.startswith("SMOKE")]
    return r.returncode == 0, (last[-1] if last else r.stdout[-200:])


@item("A", "Mutation check result on file: every planted bug caught", "python scripts/mutation_check.py")
def a_mutation(_):
    p = ROOT / "results" / "mutation.json"
    if not p.is_file():
        return None, "results/mutation.json missing: run make reproduce-full"
    m = json.loads(p.read_text(encoding="utf-8"))
    return m["survived"] == 0 and m["stale"] == 0, f"killed {m['killed']}/{m['applied']}"


@item("A", "Plan versus delivered: every promise points at an existing claim", "python scripts/plan_vs_delivered.py")
def a_plan(_):
    r = subprocess.run([sys.executable, str(ROOT / "scripts" / "plan_vs_delivered.py")], cwd=ROOT, capture_output=True,
                       text=True)
    return r.returncode == 0, "PLAN_VS_DELIVERED.md regenerated" if r.returncode == 0 else r.stdout[-200:]


@item("A", "CLAIMS.md: every proof file it names exists; every 'runs' row has a command or file", "(this script)")
def a_claims(_):
    text = (ROOT / "CLAIMS.md").read_text(encoding="utf-8")
    rows = re.findall(r"^\| (C-\d+) \|(.*)$", text, re.M)
    missing = []
    for cid, rest in rows:
        for path in re.findall(r"`((?:app|bench|core|tests|registry|report|voice|results|scripts|eval|data)/[\w./-]+)", rest):
            p = path.split("::")[0]
            if not (ROOT / p).exists():
                missing.append(f"{cid}: {p}")
    return not missing, f"{len(rows)} claims checked" + (f"; missing: {missing}" if missing else "")


@item("A", "Finale slide matches CLAIMS.md line for line", "python scripts/make_slide.py")
def a_slide(_):
    import importlib.util
    spec = importlib.util.spec_from_file_location("mk", ROOT / "scripts" / "make_slide.py")
    mk = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mk)
    same = (ROOT / "FINALE_SLIDE.md").is_file() and (ROOT / "FINALE_SLIDE.md").read_text(encoding="utf-8") == mk.build()
    return same, "FINALE_SLIDE.md is up to date" if same else "regenerate: python scripts/make_slide.py"


@item("A", "Required documents present", "(this script)")
def a_docs(_):
    need = ["SUBMISSION.md", "REPRODUCE.md", "TESTPLAN.md", "RESULTS.md", "CLAIMS.md", "STATUS.md", "DISCLOSURE.md",
            "FINALE_LOG.md", "HANDOFF.md", "DEPLOY.md", "DEPLOYABILITY.md", "PLAN_VS_DELIVERED.md", "PREBUILT.md",
            "FINALE_SLIDE.md", "QA_SHEET.md", "DEMO_12MIN.md", "docs/DEMO_SCRIPT.md", "README.md", "RUBRIC_MAP.md",
            "ENGINEERING_WALKTHROUGH.md", "PROBLEM_USER.md", "EVASION_LAB.md", "Dockerfile", "docker-compose.yml",
            "requirements.txt", "requirements-dev.txt", "requirements-voice.txt"]
    miss = [n for n in need if not (ROOT / n).is_file()]
    return not miss, f"{len(need) - len(miss)}/{len(need)} present" + (f"; missing {miss}" if miss else "")


@item("A", "Open-data and blind results recorded (or honestly 'not run')", "python -m bench.sms.run; python -m bench.blind.run")
def a_open(_):
    sms, blind = ROOT / "results" / "q2" / "sms.json", ROOT / "results" / "q2" / "blind.json"
    got = [n for n, p in (("SMS Spam", sms), ("blind chats", blind)) if p.is_file()]
    return (True if len(got) == 2 else None), ("run: " + ", ".join(got) if got else "not run yet") + \
        ("" if len(got) == 2 else " (allowed: RESULTS.md says 'not run')")


# ------------------------------------------------------------------------------------------------ part B ----
def _case(chat, firm, names=None, audio=None, transcripts=None):
    from app.case import UserCheck, build_case
    checks = {k: UserCheck(v, "Bank app (beneficiary name)", date(2026, 10, 25)) for k, v in (names or {}).items()}
    return build_case(case_id="acc", chat_text=chat, claimed_firm=firm, checks=checks, audio=audio, transcripts=transcripts)


@item("B", "1. Three changing payees are found and checked separately (scenario A)", "demo: scenario A")
def b_three(_):
    from app.case import UserCheck, build_case, demo_inputs, load_demo
    fx = load_demo("A")
    di = demo_inputs(fx)
    c = build_case(case_id=di["case_id"], chat_text=di["chat_text"], claimed_firm=di["claimed_firm"],
                   checks={k: UserCheck(v["name"], v["source"], v["date"]) for k, v in di["checks"].items()},
                   transcripts=di["transcripts"], fixture=fx)
    return len(c.payees) == 3 and c.case_result() == "NAME_DISCREPANCY", \
        f"{[p.value_norm for p in c.payees]} -> {c.case_result()}"


@item("B", "2. Name matches but 'pay 18% tax to withdraw' -> Inconclusive", "demo: paste chat")
def b_tax(_):
    c = _case("13/10/2026, 6:02 pm - Desk: To withdraw your profit pay 18% tax first to navyug.brk@validhdfc\n",
              "Navyug Broking Pvt Ltd", {"navyug.brk@validhdfc": "NAVYUG BROKING PVT LTD"})
    return c.case_result() == "INCONCLUSIVE", f"answer {c.case_result()}"


@item("B", "3. A voice cue never clears: flagged voice + matching name -> review, never 'no major issue'", "demo: voice")
def b_voice(_):
    from voice import service
    from voice.calibration import Calibration
    from voice.stub import stub_result  # noqa: F401  (contract module present)

    class AlwaysFake:
        name, model_version, chunk_samples, native_polarity = "test", "acceptance-fake", 16000, "higher_is_fake"

        def score_chunks(self, chunks):
            return [0.99] * len(chunks)

    service.set_backend(AlwaysFake(), Calibration(0.5, "higher_is_fake", "calibrated", "acceptance-fake", "test"))
    try:
        audio = {"PTT-1.wav": (ROOT / "app" / "demo_media" / "demo_voice_real_human.wav").read_bytes()}
        c = _case("13/10/2026, 6:02 pm - Desk: Add funds to navyug.brk@validhdfc\n"
                  "13/10/2026, 6:03 pm - Desk: PTT-1.wav (file attached)\n", "Navyug Broking Pvt Ltd",
                  {"navyug.brk@validhdfc": "NAVYUG BROKING PVT LTD"}, audio=audio)
    finally:
        service.reset_backend()
    states = [v.state for v in c.voice]
    return c.case_result() == "HUMAN_REVIEW" and states == ["flagged"], f"voice {states} -> {c.case_result()}"


@item("B", "4. A second victim's report links the payee; 5. a payment gateway never links", "demo: registry")
def b_registry(_):
    import tempfile
    from registry.sqlite_registry import BURST_WINDOW_S, SQLiteRegistry, create_db, new_reporter_token
    with tempfile.TemporaryDirectory(prefix="veriq_acc_") as td:
        db = Path(td) / "r.db"
        create_db(db)
        t = [1_800_000_000.0]
        reg = SQLiteRegistry(db, secret=b"acceptance-secret-0123", clock=lambda: t[0])
        reg.report("upi_vpa", "ramesh.k@upi", new_reporter_token())
        one = reg.lookup("p", "upi_vpa", "ramesh.k@upi").status
        t[0] += BURST_WINDOW_S + 1
        reg.report("upi_vpa", "ramesh.k@upi", new_reporter_token())
        two = reg.lookup("p", "upi_vpa", "ramesh.k@upi").status
        gw = [reg.report("upi_vpa", "navyug@razorpay", new_reporter_token()).status for _ in range(3)]
        gws = reg.lookup("p", "upi_vpa", "navyug@razorpay").status
    return (one, two) == ("clean", "linked") and gws != "linked" and set(gw) == {"excluded"}, \
        f"1 report: {one}; 2 victims: {two}; gateway reports: {gw[0]}, lookup: {gws}"


@item("B", "6. Filing sheet for 1930 / cybercrime.gov.in with full identifiers", "demo: reports")
def b_filing(_):
    from app.case import report_data
    from report.build import filing_sheet_md
    c = _case("13/10/2026, 6:02 pm - X: pay ₹20,000 to ramesh.k@upi\n", "Navyug", {"ramesh.k@upi": "SHREE GANESH TRADERS"})
    md = filing_sheet_md(report_data(c, money_sent=True))
    return "1930" in md and "ramesh.k@upi" in md.replace("\\", ""), f"{len(md)} characters"


@item("B", "7. Works offline: no outgoing connection during a full check", "demo: offline")
def b_offline(_):
    from app import config
    config.blocked.clear()
    config.block_network()
    try:
        _case("13/10/2026, 6:02 pm - X: pay to ramesh.k@upi\n", "Navyug", {"ramesh.k@upi": "SHREE GANESH TRADERS"})
    finally:
        config.unblock_network()
    return not config.blocked, f"{len(config.blocked)} blocked attempts"


@item("B", "8. A NEW chat typed live gets a computed answer in under a second", "demo: paste box")
def b_new(_):
    t0 = time.perf_counter()
    c = _case("25/10/2026, 8:00 am - Judge: Sir urgent, send ₹9,999 to judge.test@okicici in 5 mins, guaranteed double\n",
              "Any Firm Ltd")
    ms = (time.perf_counter() - t0) * 1000
    return c.case_result() is not None and ms < 1000, f"{c.case_result()} in {ms:.0f} ms"


@item("B", "9. A genuine user flagged by mistake is cleared by a reviewer, with time to decision", "demo: scenario D")
def b_overturn(_):
    from app.overturn import Ledger
    from app.views.player import SCENARIO_D
    c = _case(SCENARIO_D["chat"], SCENARIO_D["claimed_firm"], SCENARIO_D["names"])
    p = c.payees[0]
    first = c.result_for(p.id).result
    led = Ledger()
    led.request(p.id, p.value_norm, first, "The firm uses a different legal or trading name", "", p.value_norm)
    r = led.decide(p.id, "overturned", "Reviewer", "SEBI Check shows the @valid handle")
    return first == "NAME_DISCREPANCY" and r.status == "overturned", f"{first} -> {r.status}, {r.elapsed()}"


def main(argv=None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--fast", action="store_true")
    a = ap.parse_args(argv)
    for fn in (a_reproduce, a_smoke, a_mutation, a_plan, a_claims, a_slide, a_docs, a_open, b_three, b_tax, b_voice, b_registry,
               b_filing, b_offline, b_new, b_overturn):
        fn(a.fast)
    fails = [i for i in items if i["status"] == "FAIL"]
    when = datetime.now(timezone(timedelta(hours=5, minutes=30))).strftime("%Y-%m-%d %H:%M IST")
    commit = subprocess.run(["git", "rev-parse", "--short", "HEAD"], cwd=ROOT, capture_output=True, text=True).stdout.strip()
    L = ["# Acceptance list", "", f"Run {when}, commit {commit or 'unknown'}"
         f"{' (fast mode)' if a.fast else ''}. Command: `python scripts/acceptance.py`.", "",
         "| Part | Item | Command | Result | Detail |", "|---|---|---|---|---|"]
    L += [f"| {i['part']} | {i['item']} | `{i['command']}` | **{i['status']}** | {i['detail'].replace('|', '/')} |" for i in items]
    L += ["", f"**{'ACCEPTED' if not fails else str(len(fails)) + ' ITEM(S) FAILED'}** "
              "('NOT RUN' items are listed, never hidden).", ""]
    (ROOT / "results").mkdir(exist_ok=True)
    (ROOT / "results" / "ACCEPTANCE.md").write_text("\n".join(L), encoding="utf-8")
    print("\n".join(L))
    return 1 if fails else 0


if __name__ == "__main__":
    raise SystemExit(main())
