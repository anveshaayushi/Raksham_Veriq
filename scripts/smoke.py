#!/usr/bin/env python3
"""Smoke test for a fresh install or a deployed container (Q4 item b). Exit code 0 only if every step passes.

    python scripts/smoke.py            (make smoke)
    python scripts/smoke.py --no-app   (skip starting the web app, e.g. inside a build step)

Steps: parse a sample chat · run the rules engine · analyse a voice clip (ffmpeg + gate; model if installed) · query
a registry · build a report · start the app and check its health endpoint · confirm VERIQ's own code made no
outgoing network connection while doing all of that (sockets to non-loopback addresses are blocked and counted).
"""
from __future__ import annotations

import argparse
import os
import shutil
import socket
import subprocess
import sys
import tempfile
import time
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
results: list[tuple[str, bool, str]] = []


def step(name):
    def wrap(fn):
        def run(*a):
            t0 = time.perf_counter()
            try:
                detail = fn(*a) or ""
                ok = True
            except Exception as e:  # report and continue
                ok, detail = False, f"{type(e).__name__}: {e}"[:200]
            results.append((name, ok, f"{detail} ({(time.perf_counter() - t0) * 1000:.0f} ms)"))
            print(f"[{'PASS' if ok else 'FAIL'}] {name}: {detail}", flush=True)
        return run
    return wrap


@step("parse a sample chat")
def s_parse():
    from app.case import demo_inputs, load_demo
    from parsing import parse_chat
    msgs = parse_chat(demo_inputs(load_demo("A"))["chat_text"])
    assert len(msgs) >= 5, len(msgs)
    return f"{len(msgs)} messages"


@step("rules engine on scenario A")
def s_engine():
    from app.case import UserCheck, build_case, demo_inputs, load_demo
    fx = load_demo("A")
    di = demo_inputs(fx)
    checks = {k: UserCheck(v["name"], v["source"], v["date"]) for k, v in di["checks"].items()}
    c = build_case(case_id=di["case_id"], chat_text=di["chat_text"], claimed_firm=di["claimed_firm"], checks=checks,
                   transcripts=di["transcripts"], fixture=fx)
    assert c.case_result() == "NAME_DISCREPANCY", c.case_result()
    return f"{len(c.payees)} payees, answer {c.case_result()}"


@step("analyse a voice clip")
def s_voice():
    from voice import analyse
    data = (ROOT / "app" / "demo_media" / "demo_voice_real_human.wav").read_bytes()
    vr = analyse("smoke.wav", data, "smoke.wav")
    assert vr.state in ("flagged", "no_signal", "cant_assess") and vr.file_id == "smoke.wav"
    if shutil.which("ffmpeg") is None:
        raise RuntimeError("ffmpeg not on PATH (voice notes would all be 'can't assess')")
    return f"state {vr.state}, {vr.speech_seconds} s speech, model {vr.model_version}"


@step("registry: report twice, then look up")
def s_registry():
    from registry.sqlite_registry import BURST_WINDOW_S, SQLiteRegistry, create_db, new_reporter_token
    with tempfile.TemporaryDirectory(prefix="veriq_smoke_") as td:
        db = Path(td) / "r.db"
        create_db(db)
        t = [1_800_000_000.0]
        reg = SQLiteRegistry(db, secret=b"smoke-test-secret-0123", clock=lambda: t[0])
        for _ in range(2):
            reg.report("upi_vpa", "smoke.mule@upi", new_reporter_token())
            t[0] += BURST_WINDOW_S + 1
        st = reg.lookup("p", "upi_vpa", "smoke.mule@upi").status
        assert st == "linked" and b"smoke.mule@upi" not in db.read_bytes()
    return "linked after 2 independent reporters; no raw identifier in the file"


@step("build the reports")
def s_report():
    from app.case import UserCheck, build_case, demo_inputs, load_demo, report_data
    from report.build import filing_sheet_md, incident_json, summary_md
    fx = load_demo("A")
    di = demo_inputs(fx)
    c = build_case(case_id=di["case_id"], chat_text=di["chat_text"], claimed_firm=di["claimed_firm"],
                   checks={k: UserCheck(v["name"], v["source"], v["date"]) for k, v in di["checks"].items()},
                   transcripts=di["transcripts"], fixture=fx)
    d = report_data(c, money_sent=True)
    out = summary_md(d) + filing_sheet_md(d) + incident_json(d)
    assert "1930" in out
    return f"{len(out)} characters"


@step("start the app and check /_stcore/health")
def s_app():
    with socket.socket() as s:
        s.bind(("127.0.0.1", 0))
        port = s.getsockname()[1]
    env = {**os.environ, "VERIQ_OFFLINE": "1"}
    p = subprocess.Popen([sys.executable, "-m", "streamlit", "run", str(ROOT / "app" / "streamlit_app.py"),
                          "--server.headless", "true", "--server.port", str(port), "--server.address", "127.0.0.1",
                          "--browser.gatherUsageStats", "false"], cwd=ROOT, env=env,
                         stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    try:
        for _ in range(120):
            try:
                body = urllib.request.urlopen(f"http://127.0.0.1:{port}/_stcore/health", timeout=2).read().decode()
                if body.strip() == "ok":
                    return f"health ok on port {port}"
            except OSError:
                time.sleep(0.5)
        raise RuntimeError("no health response within 60 s")
    finally:
        p.terminate()
        try:
            p.wait(10)
        except subprocess.TimeoutExpired:
            p.kill()


def main(argv=None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--no-app", action="store_true")
    a = ap.parse_args(argv)
    from app import config
    config.blocked.clear()
    config.block_network()  # everything below must work with the network blocked
    try:
        s_parse()
        s_engine()
        s_voice()
        s_registry()
        s_report()
        if not a.no_app:
            s_app()
    finally:
        config.unblock_network()
    egress = list(config.blocked)
    results.append(("no outgoing network connection", not egress, f"{len(egress)} attempt(s) blocked {egress[:3]}"))
    print(f"[{'PASS' if not egress else 'FAIL'}] no outgoing network connection: {len(egress)} attempt(s) blocked")
    bad = [r for r in results if not r[1]]
    print(f"\nSMOKE: {'PASS' if not bad else 'FAIL'} ({len(results) - len(bad)}/{len(results)} steps)")
    return 1 if bad else 0


if __name__ == "__main__":
    raise SystemExit(main())
