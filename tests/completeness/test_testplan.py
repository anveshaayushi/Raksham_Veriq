"""TESTPLAN.md cannot go stale: every test it names exists, and every CLAIMS.md row has a line in it."""
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
PLAN = (ROOT / "TESTPLAN.md").read_text(encoding="utf-8")


def test_every_test_named_in_the_plan_exists():
    refs = re.findall(r"`([\w/]+\.py)::(test_\w+)`", PLAN)
    assert len(refs) >= 60
    missing = [f"{f}::{t}" for f, t in refs
               if not (ROOT / f).is_file() or not re.search(rf"^def {t}\(", (ROOT / f).read_text(encoding="utf-8"), re.M)]
    assert not missing, missing


def test_every_claim_row_is_in_the_plan():
    claims = re.findall(r"^\| (C-\d+) \|", (ROOT / "CLAIMS.md").read_text(encoding="utf-8"), re.M)
    assert claims and not [c for c in claims if not re.search(rf"^\| {c} ", PLAN, re.M)]


def test_every_named_test_file_exists():
    files = set(re.findall(r"`((?:tests|app|registry|report|voice)/[\w/]+\.py)`", PLAN))
    assert files and all((ROOT / f).is_file() for f in files)
