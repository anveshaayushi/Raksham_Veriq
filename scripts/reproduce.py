#!/usr/bin/env python3
"""One command from a clean checkout to every reported number (Q1, organisers' rules 1-4). See REPRODUCE.md.

    python scripts/reproduce.py                    # data + tests + coverage + random order + chat benchmark + red team
    python scripts/reproduce.py --mutation         # also the mutation check (slow: one suite run per planted bug)
    python scripts/reproduce.py --voice-data <voiceset dir> --aasist <aasist repo>   # also retrain/re-test the voice head
    python scripts/reproduce.py --quick            # skip the two random-order runs

Writes results/ (described in REPRODUCE.md, section 6) and compares against the committed results:
  * synthetic data: regenerated files must be byte-identical to bench/data/*.json and data/synthetic/*.json
  * chat benchmark: every field identical to bench/results_{dev,test}.json except time per chat (machine-dependent)
  * red-team set: identical to bench/results_adversarial.json
  * tests: 0 failed (skips allowed, each with its printed reason); product coverage >= 85%
  * voice: head.json matches its calibration file; if retrained, AUC / rates within +-0.02 of bench/voice/results.json
Exit code 0 only if every check passes. Nothing here uses the network.
"""
from __future__ import annotations

import argparse
import hashlib
import importlib.metadata as md
import json
import os
import platform
import re
import shutil
import subprocess
import sys
import time
import xml.etree.ElementTree as ET
from datetime import datetime, timedelta, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
RES = ROOT / "results"
IST = timezone(timedelta(hours=5, minutes=30))
PRODUCT = ["app", "core", "extract", "match", "parsing", "registry", "report", "rules", "voice", "eval"]
SUPPORT = ["bench", "scripts", "data"]
COVERAGE_TARGET = 85.0
RANDOM_SEEDS = (20261024, 424242)
VOICE_TOL = 0.02

checks: list[dict] = []


def check(name: str, ok: bool | None, detail: str, warn_only: bool = False) -> None:
    """ok=None means 'not run'; warn_only turns a failure into 'warn'. Neither counts as a failed check."""
    status = "pass" if ok else ("not run" if ok is None else ("warn" if warn_only else "FAIL"))
    checks.append({"check": name, "status": status, "detail": detail})
    print(f"[{checks[-1]['status']:7s}] {name}: {detail}", flush=True)


def sha256(p: Path) -> str:
    return hashlib.sha256(p.read_bytes()).hexdigest()


def dump(name: str, obj) -> None:
    with open(RES / name, "w", encoding="utf-8", newline="\n") as f:
        f.write(json.dumps(obj, indent=1, ensure_ascii=False))


def have(mod: str) -> bool:
    try:
        __import__(mod)
        return True
    except Exception:
        return False


# ---------------------------------------------------------------------------------------------- 1. environment ----
def environment() -> dict:
    pkgs = {}
    for line in (ROOT / "requirements.txt").read_text(encoding="utf-8").splitlines():
        m = re.match(r"^([A-Za-z0-9_.-]+)==(\S+)", line)
        if m:
            try:
                got = md.version(m.group(1))
            except md.PackageNotFoundError:
                got = None
            pkgs[m.group(1)] = {"pinned": m.group(2), "installed": got}
    extras = {}
    for name in ("torch", "torchaudio", "soundfile", "scikit-learn", "coverage", "pytest-cov", "pytest-randomly"):
        try:
            extras[name] = md.version(name)
        except md.PackageNotFoundError:
            extras[name] = None
    ff = shutil.which("ffmpeg")
    ffv = None
    if ff:
        try:
            ffv = subprocess.run([ff, "-version"], capture_output=True, text=True, timeout=20).stdout.splitlines()[0]
        except Exception as e:  # noqa: BLE001
            ffv = f"error: {e}"
    aasist = os.environ.get("VERIQ_AASIST_REPO") or str(ROOT / "external" / "aasist")
    commit = None
    try:
        commit = subprocess.run(["git", "rev-parse", "--short", "HEAD"], cwd=ROOT, capture_output=True, text=True,
                                timeout=10).stdout.strip() or None
        dirty = subprocess.run(["git", "status", "--porcelain"], cwd=ROOT, capture_output=True, text=True,
                               timeout=20).stdout.strip()
        commit = f"{commit}{' + uncommitted changes' if dirty else ''}" if commit else None
    except Exception:  # noqa: BLE001
        pass
    env = {"run_at_ist": datetime.now(IST).strftime("%Y-%m-%d %H:%M IST"), "commit": commit,
           "python": sys.version.split()[0], "platform": platform.platform(), "machine": platform.machine(),
           "processor": platform.processor() or None, "cpu_count": os.cpu_count(), "ffmpeg": ffv,
           "aasist_repo_present": Path(aasist).is_dir(), "pinned_packages": pkgs, "extras": extras}
    off = {k: v for k, v in pkgs.items() if v["installed"] != v["pinned"]}
    check("environment matches requirements.txt pins", not off,
          "all pins installed" if not off else f"{len(off)} differ (results may still match; use a clean venv from "
          "requirements-dev.txt for an exact reproduction): " + ", ".join(
              f"{k} pinned {v['pinned']} got {v['installed']}" for k, v in list(off.items())[:6]), warn_only=True)
    dump("environment.json", env)
    return env


# ---------------------------------------------------------------------------------------------- 2. synthetic data ----
def regenerate_data() -> None:
    from bench import generate
    from data.synthetic.generate_campaigns import generate_campaign_data
    out = RES / "regenerated"
    (out / "bench").mkdir(parents=True, exist_ok=True)
    (out / "campaigns").mkdir(parents=True, exist_ok=True)
    old = generate.OUT
    generate.OUT = out / "bench"
    try:
        generate.main()
    finally:
        generate.OUT = old
    generate_campaign_data(str(out / "campaigns"))
    rows = []
    for new, ref in [(out / "bench" / "dev.json", ROOT / "bench" / "data" / "dev.json"),
                     (out / "bench" / "test.json", ROOT / "bench" / "data" / "test.json"),
                     (out / "campaigns" / "campaign_cases.json", ROOT / "data" / "synthetic" / "campaign_cases.json"),
                     (out / "campaigns" / "registry_seed.json", ROOT / "data" / "synthetic" / "registry_seed.json")]:
        rows.append({"file": str(ref.relative_to(ROOT)).replace("\\", "/"), "sha256": sha256(new),
                     "committed_sha256": sha256(ref), "identical": sha256(new) == sha256(ref)})
    dump("data_checksums.json", rows)
    bad = [r["file"] for r in rows if not r["identical"]]
    check("synthetic data regenerates byte-identical (seeded)", not bad,
          f"{len(rows) - len(bad)}/{len(rows)} files identical" + (f"; differ: {bad}" if bad else ""))


# ---------------------------------------------------------------------------------------------- 3. tests ----
def _junit_counts(path: Path) -> dict:
    root = ET.parse(path).getroot()
    suites = [root] if root.tag == "testsuite" else list(root)
    tot = {k: sum(int(s.get(k, 0)) for s in suites) for k in ("tests", "failures", "errors", "skipped")}
    tot["passed"] = tot["tests"] - tot["failures"] - tot["errors"] - tot["skipped"]
    return tot


def run_tests() -> dict:
    cov = have("pytest_cov")
    cmd = [sys.executable, "-m", "pytest", "-p", "no:randomly", "-p", "no:cacheprovider", "-q", "-rs",
           f"--junitxml={RES / 'junit.xml'}"]
    if cov:
        cmd += ["--cov", "--cov-report=term", f"--cov-report=json:{RES / 'coverage.json'}"]
    t0 = time.perf_counter()
    r = subprocess.run(cmd, cwd=ROOT, capture_output=True, text=True)
    secs = round(time.perf_counter() - t0, 1)
    (RES / "pytest_output.txt").write_text(r.stdout[-200000:] + "\n" + r.stderr[-20000:], encoding="utf-8")
    counts = _junit_counts(RES / "junit.xml")
    skips = sorted({ln.split(":", 2)[-1].strip() for ln in r.stdout.splitlines() if ln.startswith("SKIPPED")})
    out = {"command": " ".join(cmd[1:]).replace(str(RES), "results"), "seconds": secs, **counts, "skip_reasons": skips}
    check("full test suite", counts["failures"] == 0 and counts["errors"] == 0,
          f"{counts['passed']} passed, {counts['failures']} failed, {counts['errors']} errors, {counts['skipped']} skipped "
          f"in {secs} s")
    if cov:
        data = json.loads((RES / "coverage.json").read_text(encoding="utf-8"))
        per = {}
        for f, v in data["files"].items():
            top = f.replace("\\", "/").split("/")[0]
            group = "product" if top in PRODUCT else "support"
            s = per.setdefault(group, [0, 0])
            s[0] += v["summary"]["num_statements"]
            s[1] += v["summary"]["covered_lines"]
        cover = {g: round(100 * c / n, 1) for g, (n, c) in per.items() if n}
        low = sorted(((f, round(v["summary"]["percent_covered"], 1)) for f, v in data["files"].items()
                      if f.replace("\\", "/").split("/")[0] in PRODUCT and v["summary"]["percent_covered"] < 85),
                     key=lambda x: x[1])
        out["coverage"] = {"product_percent": cover.get("product"), "support_scripts_percent": cover.get("support"),
                           "product_packages": PRODUCT, "support_packages": SUPPORT, "target": COVERAGE_TARGET,
                           "product_files_below_85": low}
        term = r.stdout[r.stdout.find("coverage:"):] if "coverage:" in r.stdout else ""
        (RES / "coverage.txt").write_text(term.split("\n=")[0] if term else "", encoding="utf-8")
        check("statement coverage of product code", (cover.get("product") or 0) >= COVERAGE_TARGET,
              f"product {cover.get('product')}% (target {COVERAGE_TARGET}%), bench/scripts {cover.get('support')}%")
    else:
        check("statement coverage of product code", None, "pytest-cov not installed: pip install -r requirements-dev.txt")
    dump("tests.json", out)
    return out


def random_order() -> None:
    if not have("pytest_randomly"):
        check("random test order (2 runs)", None, "pytest-randomly not installed: pip install -r requirements-dev.txt")
        return
    runs = []
    for seed in RANDOM_SEEDS:
        x = RES / f"junit_random_{seed}.xml"
        r = subprocess.run([sys.executable, "-m", "pytest", "-o", "addopts=", "-q", "-rfE", "-p", "randomly",
                            f"--randomly-seed={seed}", "-p", "no:cacheprovider", f"--junitxml={x}"],
                           cwd=ROOT, capture_output=True, text=True)
        c = _junit_counts(x)
        x.unlink()
        fails = [ln for ln in r.stdout.splitlines() if ln.startswith(("FAILED", "ERROR"))]
        runs.append({"seed": seed, **c, "failing": fails[:20]})
    dump("random_order.json", {"runs": runs, "plugin": "pytest-randomly (shuffles test order; reseeds random)"})
    bad = [r for r in runs if r["failures"] or r["errors"]]
    check("random test order (2 runs, seeds " + ", ".join(map(str, RANDOM_SEEDS)) + ")", not bad,
          "; ".join(f"seed {r['seed']}: {r['passed']} passed, {r['failures'] + r['errors']} failed" for r in runs)
          + (" -> flaky or order-dependent tests" if bad else " -> no flaky tests seen"))


# ---------------------------------------------------------------------------------------------- 4. benchmarks ----
def _strip_time(d: dict) -> dict:
    return {k: v for k, v in d.items() if k != "ms_per_chat"}


def chat_benchmark() -> None:
    from bench.run import evaluate
    for split in ("dev", "test"):
        new = evaluate(split, out_dir=RES)
        ref = json.loads((ROOT / "bench" / f"results_{split}.json").read_text(encoding="utf-8"))
        same = _strip_time(new) == _strip_time(ref)
        fa = new["false_alarms_on_legit_payees"]
        check(f"chat benchmark ({split}, synthetic)", same,
              f"{new['chats']} chats, {new['payees']} payees, accuracy {new['decision_accuracy']}, payees found "
              f"{new['extraction']['tp']}/{new['payees']}, false alarms {fa['count']}/{fa['of']}, median "
              f"{new['ms_per_chat']['median']} ms/chat" + ("" if same else " -> DIFFERS from committed"))


def red_team() -> None:
    if not have("cv2"):
        check("red-team set", None, "opencv not installed")
        return
    from bench import adversarial
    s = adversarial.summarize(adversarial.run())
    adversarial.write(s, RES)
    ref = json.loads((ROOT / "bench" / "results_adversarial.json").read_text(encoding="utf-8"))
    check("red-team set (synthetic, written by us)", s == ref,
          f"defended {s['defended_attacks_passed']}/{s['defended_attacks']}, known gaps still open "
          f"{s['known_gaps_still_failing']}/{s['known_gaps']}" + ("" if s == ref else " -> DIFFERS from committed"))


def voice(voice_data: str | None, aasist: str | None) -> None:
    head = ROOT / "bench" / "voice" / "head.json"
    cal = json.loads((ROOT / "bench" / "voice" / "head_calibration.json").read_text(encoding="utf-8"))
    sha12 = sha256(head)[:12]
    check("voice head file matches its calibration", cal["model_version"].endswith("+head@" + sha12),
          f"head.json sha256[:12]={sha12}; calibration for {cal['model_version']}")
    ref = json.loads((ROOT / "bench" / "voice" / "results.json").read_text(encoding="utf-8"))
    if not (voice_data and aasist):
        h = ref["detectors"]["trained_head"]
        check("voice benchmark retrain (FSDD + Kokoro, synthetic/public)", None,
              f"not re-run (needs --voice-data and --aasist, see REPRODUCE.md); committed: AUC {h['test_auc']}, "
              f"genuine flagged {h['test_genuine_flagged']}, synthetic caught {h['test_synthetic_caught']}")
        return
    out = RES / "voice" / "results.json"
    out.parent.mkdir(parents=True, exist_ok=True)
    r = subprocess.run([sys.executable, "-m", "bench.voice.train_eval", "--data", voice_data, "--aasist", aasist,
                        "--out", str(out)], cwd=ROOT, capture_output=True, text=True)
    if r.returncode != 0:
        check("voice benchmark retrain", False, "train_eval failed: " + (r.stderr.strip().splitlines() or [""])[-1][:200])
        return
    new = json.loads(out.read_text(encoding="utf-8"))
    diffs = []
    for det in ("pretrained", "trained_head"):
        for k in ("test_auc", "test_eer", "test_genuine_flagged", "test_synthetic_caught"):
            a, b = new["detectors"][det][k], ref["detectors"][det][k]
            if abs(a - b) > VOICE_TOL:
                diffs.append(f"{det}.{k} {a} vs {b}")
    h = new["detectors"]["trained_head"]
    check("voice benchmark retrain (FSDD + Kokoro, synthetic/public)", not diffs,
          f"AUC {h['test_auc']}, genuine flagged {h['test_genuine_flagged']}, synthetic caught "
          f"{h['test_synthetic_caught']} (tolerance +-{VOICE_TOL})" + (f"; differ: {diffs}" if diffs else ""))


def mutation() -> None:
    r = subprocess.run([sys.executable, str(ROOT / "scripts" / "mutation_check.py"), "--out",
                        str(RES / "mutation.json")], cwd=ROOT, capture_output=True, text=True)
    try:
        m = json.loads((RES / "mutation.json").read_text(encoding="utf-8"))
    except (OSError, ValueError):
        check("mutation check", False, (r.stdout + r.stderr).strip()[-300:])
        return
    surv = [x["id"] for x in m["rows"] if x["status"] == "SURVIVED"]
    check("mutation check (planted bugs caught by the tests)", not surv and not m["stale"],
          f"killed {m['killed']}/{m['applied']} (kill rate {m['kill_rate']}); survived {surv or 'none'}; "
          f"stale {m['stale']}")


# ---------------------------------------------------------------------------------------------- report ----
def report(env: dict, t0: float) -> int:
    fails = [c for c in checks if c["status"] == "FAIL"]
    lines = ["# Reproduction report", "",
             f"Run at {env['run_at_ist']} on {env['platform']} ({env['machine']}, {env['cpu_count']} CPUs), "
             f"Python {env['python']}, commit {env['commit'] or 'unknown'}; ffmpeg: {env['ffmpeg'] or 'not found'}; "
             f"total {round(time.perf_counter() - t0)} s.", "",
             "| Check | Result | Detail |", "|---|---|---|"]
    lines += [f"| {c['check']} | {c['status']} | {c['detail'].replace('|', '/')} |" for c in checks]
    lines += ["", f"**{'ALL CHECKS PASSED' if not fails else str(len(fails)) + ' CHECK(S) FAILED'}** "
                  "('not run' items are listed, not hidden). Data is synthetic (generated by us) or public; "
                  "see REPRODUCE.md for what each number means and its limits.", ""]
    (RES / "REPRODUCE_REPORT.md").write_text("\n".join(lines), encoding="utf-8")
    dump("reproduce.json", {"environment": {k: env[k] for k in ("run_at_ist", "commit", "python", "platform")},
                            "checks": checks})
    print("\n".join(lines))
    return 1 if fails else 0


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--quick", action="store_true", help="skip the two random-order runs")
    ap.add_argument("--mutation", action="store_true", help="also run scripts/mutation_check.py (slow)")
    ap.add_argument("--voice-data", help="voice set folder from bench/voice/make_set.py")
    ap.add_argument("--aasist", help="AASIST repo folder (code + weights)")
    a = ap.parse_args(argv)
    t0 = time.perf_counter()
    RES.mkdir(exist_ok=True)
    env = environment()
    regenerate_data()
    run_tests()
    if not a.quick:
        random_order()
    chat_benchmark()
    red_team()
    voice(a.voice_data, a.aasist)
    if a.mutation:
        mutation()
    return report(env, t0)


if __name__ == "__main__":
    raise SystemExit(main())
