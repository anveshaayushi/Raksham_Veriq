"""The reproducibility and test-quality tools themselves (scripts/reproduce.py, scripts/mutation_check.py) are tested
too, on small inputs: a reviewer should not have to trust an untested checker."""
from __future__ import annotations

import json
import runpy
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "scripts"))
import mutation_check as MC  # noqa: E402
import reproduce as R  # noqa: E402

pytestmark = pytest.mark.filterwarnings("ignore:.*found in sys.modules:RuntimeWarning")


@pytest.fixture()
def res(tmp_path, monkeypatch):
    monkeypatch.setattr(R, "RES", tmp_path)
    monkeypatch.setattr(R, "checks", [])
    return tmp_path


def test_every_mutant_still_applies_to_exactly_one_place():
    for mid, rel, old, new, meaning in MC.MUTANTS:
        src = (ROOT / rel).read_text(encoding="utf-8")
        assert src.count(old) == 1, f"{mid} is stale: its text is in {rel} {src.count(old)} times"
        assert old != new and meaning
    assert len(MC.MUTANTS) >= 15 and len({m[0] for m in MC.MUTANTS}) == len(MC.MUTANTS)


def test_mutation_check_kills_a_mutant_on_a_small_suite(tmp_path, capsys):
    out = tmp_path / "m.json"
    assert MC.main(["--only", "M11", "--out", str(out), "tests/golden"]) == 0
    r = json.loads(out.read_text())
    assert r["killed"] == 1 and r["kill_rate"] == 1.0 and r["rows"][0]["first_failing_test"].startswith("tests/golden")
    assert MC.main(["--list"]) == 0 and "M17" in capsys.readouterr().out


def test_mutation_check_reports_survivors_and_stale_mutants(tmp_path, monkeypatch):
    monkeypatch.setattr(MC, "MUTANTS", [
        ("X1", "rules/templates.py", "LABEL = {", "LABEL = {  # harmless", "a change no test can see"),
        ("X2", "rules/templates.py", "text that is not there", "x", "stale on purpose")])
    out = tmp_path / "m.json"
    assert MC.main(["--out", str(out), "tests/golden/test_fixtures.py"]) == 1
    r = json.loads(out.read_text())
    assert [x["status"] for x in r["rows"]] == ["SURVIVED", "stale"] and r["survived"] == 1 and r["stale"] == 1


def test_reproduce_environment_data_and_voice_checks(res):
    env = R.environment()
    assert env["python"] and "pinned_packages" in env and (res / "environment.json").is_file()
    R.regenerate_data()
    rows = json.loads((res / "data_checksums.json").read_text())
    assert len(rows) == 4 and all(r["identical"] for r in rows)
    R.voice(None, None)
    st = {c["check"]: c["status"] for c in R.checks}
    assert st["synthetic data regenerates byte-identical (seeded)"] == "pass"
    assert st["voice head file matches its calibration"] == "pass"
    assert st["voice benchmark retrain (FSDD + Kokoro, synthetic/public)"] == "not run"
    assert st["environment matches requirements.txt pins"] in ("pass", "warn")


def test_reproduce_benchmarks_and_report(res):
    pytest.importorskip("cv2")
    R.chat_benchmark()
    R.red_team()
    assert all(c["status"] == "pass" for c in R.checks), R.checks
    assert (res / "results_test.json").is_file() and (res / "results_adversarial.json").is_file()
    env = {"run_at_ist": "now", "platform": "p", "machine": "m", "cpu_count": 1, "python": "3", "commit": "c",
           "ffmpeg": None}
    assert R.report(env, 0.0) == 0 and "ALL CHECKS PASSED" in (res / "REPRODUCE_REPORT.md").read_text()
    R.check("planted failure", False, "x")
    assert R.report(env, 0.0) == 1


def test_reproduce_detects_a_changed_benchmark_result(res, monkeypatch):
    import bench.run as BR
    real = BR.evaluate

    def tampered(split, out_dir=None, data_dir=None):
        r = real(split, out_dir=out_dir, data_dir=data_dir)
        r["decision_accuracy"] = 0.5
        return r

    monkeypatch.setattr(BR, "evaluate", tampered)
    R.chat_benchmark()
    assert {c["status"] for c in R.checks} == {"FAIL"}


def test_junit_counts_and_time_stripping(tmp_path):
    x = tmp_path / "j.xml"
    x.write_text('<testsuites><testsuite tests="5" failures="1" errors="0" skipped="2"/></testsuites>')
    assert R._junit_counts(x) == {"tests": 5, "failures": 1, "errors": 0, "skipped": 2, "passed": 2}
    assert R._strip_time({"a": 1, "ms_per_chat": 2}) == {"a": 1}


def test_eval_module_entry_point(monkeypatch, capsys):
    monkeypatch.setattr(sys, "argv", ["eval", "--help"])
    with pytest.raises(SystemExit) as e:
        runpy.run_module("eval", run_name="__main__")
    assert e.value.code == 0 and "usage" in capsys.readouterr().out.lower()
