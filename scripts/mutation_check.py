#!/usr/bin/env python3
"""Mutation check: do the tests notice when the safety logic is broken? (Q1 item g, organisers' rule 4)

Plain words: we copy the project to a temporary folder, plant ONE deliberate bug at a time (a "mutant"), and run the
test suite. If at least one test fails, the mutant is "killed": the tests guard that behaviour. If every test still
passes, the mutant "survived": that behaviour is not protected, and we must add a test. The real project folder is
never modified.

    python scripts/mutation_check.py                 # all mutants, writes results/mutation.json
    python scripts/mutation_check.py --only M03,M07  # a few
    python scripts/mutation_check.py --list          # show the mutants

Each mutant is an exact text replacement; if its text is no longer in the file (the code moved), it is reported as
"stale" rather than silently skipped, so this list cannot rot unnoticed.
"""
from __future__ import annotations

import argparse
import json
import shutil
import subprocess
import sys
import tempfile
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent

# (id, file, old text, new text, what the bug means in plain words)
MUTANTS = [
    ("M01", "rules/__init__.py", 'if rstatus == "linked" and registry_ev is not None:',
     'if False and rstatus == "linked" and registry_ev is not None:',
     "LINKED never fires: a payee reported by 2+ victims is not called out"),
    ("M02", "core/schemas.py", '"LINKED": 1, "NAME_DISCREPANCY": 2,', '"LINKED": 2, "NAME_DISCREPANCY": 1,',
     "rule rank flipped: the case shows a milder payee's result instead of the worst one"),
    ("M03", "rules/__init__.py", "if not matched or cant or hard:", "if not matched or cant:",
     "hard-cue block removed: 'pay 18% tax to withdraw' with a matching name says 'no major issue'"),
    ("M04", "rules/__init__.py", 'matched = [e for e, v, _ in verdicts if v == "match"]',
     'matched = [e for e, v, _ in verdicts if v == "match"] or [e for e in voice_ev if _voice_state(e.observed) == "no_signal"]',
     "a voice result clears a payee (no_signal treated like a name match)"),
    ("M05", "rules/__init__.py", 'flagged = [e for e in voice_ev if _voice_state(e.observed) == "flagged"]',
     "flagged = []", "a flagged voice note is ignored"),
    ("M06", "registry/interface.py", "return indicator_type == \"upi_vpa\" and v.endswith(NON_ATTRIBUTABLE_SUFFIXES)",
     "return False", "payment-gateway handles are stored and can be linked (innocent merchants accused)"),
    ("M07", "registry/interface.py", "LINK_MIN_INDEPENDENT_REPORTERS = 2", "LINK_MIN_INDEPENDENT_REPORTERS = 1",
     "registry link threshold weakened: one reporter is enough to brand a payee"),
    ("M08", "registry/sqlite_registry.py", "BURST_WINDOW_S = 10 * 60", "BURST_WINDOW_S = 0",
     "burst protection off: a scripted flood of new 'reporters' counts as independent"),
    ("M09", "app/text_safety.py", 'lambda m: "hxxp" + m.group(2)[3:] + m.group(3)', "lambda m: m.group(0)",
     "defanging broken in the app: links from the scammer's chat become clickable"),
    ("M10", "report/build.py", 'lambda m: "hxxp" + m.group(2)[3:] + m.group(3)', "lambda m: m.group(0)",
     "defanging broken in the reports"),
    ("M11", "rules/templates.py", 'f"Checks run found no major issue. {NOT_A_GUARANTEE} Before paying',
     'f"Checks run found no major issue. Before paying',
     "'This is not a guarantee.' dropped from the mildest answer"),
    ("M12", "app/next_steps.py", "    if not money_sent:\n        return decision",
     "    if not money_sent:\n        return decision\n    if isinstance(decision, dict):\n        decision = {**decision, \"result\": \"LINKED\"}",
     "the 'money already sent' toggle changes the result, not just the next step"),
    ("M13", "app/intake.py", "MAX_ZIP_RATIO = 100", "MAX_ZIP_RATIO = 10 ** 9", "zip-bomb ratio check disabled"),
    ("M14", "registry/sqlite_registry.py",
     'return RegistryResult(payee_id, "unavailable", 0, False, SOURCE, f"registry unavailable ({e})")\n        try:',
     'return RegistryResult(payee_id, "clean", 0, False, SOURCE, "")\n        try:',
     "a broken registry reports 'clean' instead of 'unavailable'"),
    ("M15", "rules/__init__.py", 'names = [e for e in own if e.lane == "payee_name" and e.class_ == "A"]',
     'names = [e for e in own if e.lane == "payee_name" and e.class_ in ("A", "D")]',
     "the sender-typed QR name (class D) is trusted like the user's own app check (class A)"),
    ("M16", "rules/__init__.py", 'reg_conflict = reg_state == "not_listed" or (', 'reg_conflict = False and (',
     "a SEBI number missing from the dated list is ignored"),
    ("M17", "registry/sqlite_registry.py", "return hmac_indicator(self.secret, indicator_type, value_norm)",
     "return f\"{indicator_type}:{value_norm}\"", "raw UPI IDs / account numbers stored in the registry file"),
]


def _copy_repo(dst: Path) -> None:
    ignore = shutil.ignore_patterns(".git", "__pycache__", ".pytest_cache", ".venv", "results", "external", "data/raw",
                                    "*.db", "out", "dev")
    shutil.copytree(ROOT, dst, ignore=ignore)


def run(only: list[str] | None, pytest_args: list[str]) -> dict:
    rows = []
    with tempfile.TemporaryDirectory(prefix="veriq_mut_") as td:
        work = Path(td) / "veriq"
        _copy_repo(work)
        cmd = [sys.executable, "-m", "pytest", "-x", "-q", "-rfE", "-p", "no:randomly", "-p", "no:cacheprovider",
               *pytest_args]
        base = subprocess.run(cmd, cwd=work, capture_output=True, text=True)
        if base.returncode != 0:
            raise SystemExit("the UNMUTATED suite fails in the temp copy; fix that first:\n" + base.stdout[-2000:])
        for mid, rel, old, new, meaning in MUTANTS:
            if only and mid not in only:
                continue
            f = work / rel
            src = f.read_text(encoding="utf-8")
            if src.count(old) != 1:
                rows.append({"id": mid, "file": rel, "meaning": meaning, "status": "stale",
                             "detail": f"text found {src.count(old)} times (expected exactly 1)"})
                continue
            f.write_text(src.replace(old, new), encoding="utf-8")
            t0 = time.perf_counter()
            try:
                r = subprocess.run(cmd, cwd=work, capture_output=True, text=True, timeout=1800)
                failed = [ln.split(" ")[1] for ln in r.stdout.splitlines() if ln.startswith(("FAILED ", "ERROR ")) and " " in ln]
                status = "killed" if r.returncode != 0 else "SURVIVED"
                detail = (failed[0] if failed else r.stdout.strip().splitlines()[-1][:160]) if r.stdout.strip() else ""
            except subprocess.TimeoutExpired:
                status, detail = "killed", "suite timed out (counts as detected)"
            finally:
                f.write_text(src, encoding="utf-8")
            rows.append({"id": mid, "file": rel, "meaning": meaning, "status": status, "first_failing_test": detail,
                         "seconds": round(time.perf_counter() - t0, 1)})
            print(f"{mid} {status:8s} {meaning}  [{detail}]", flush=True)
    live = [r for r in rows if r["status"] != "stale"]
    killed = sum(r["status"] == "killed" for r in live)
    return {"mutants": len(rows), "applied": len(live), "killed": killed, "survived": len(live) - killed,
            "stale": len(rows) - len(live), "kill_rate": round(killed / len(live), 3) if live else None, "rows": rows}


def main(argv=None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--only", default="")
    ap.add_argument("--list", action="store_true")
    ap.add_argument("--out", default=str(ROOT / "results" / "mutation.json"))
    ap.add_argument("pytest_args", nargs="*", help="extra pytest arguments, e.g. a test folder")
    a = ap.parse_args(argv)
    if a.list:
        for mid, rel, *_, meaning in MUTANTS:
            print(f"{mid} {rel:30s} {meaning}")
        return 0
    res = run([x for x in a.only.split(",") if x] or None, a.pytest_args)
    out = Path(a.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(res, indent=1), encoding="utf-8")
    print(f"kill rate: {res['killed']}/{res['applied']} ({res['kill_rate']}); survived: {res['survived']}; "
          f"stale: {res['stale']}  -> {out}")
    return 0 if res["survived"] == 0 and res["stale"] == 0 else 1


if __name__ == "__main__":
    raise SystemExit(main())
