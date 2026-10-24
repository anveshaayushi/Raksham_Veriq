"""Q5: the demo story (acceptance part B) and the document checks stay green, so the live demo cannot silently break."""
from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "scripts"))
import acceptance as A  # noqa: E402


def test_demo_story_and_document_checks_pass():
    A.items.clear()
    for fn in (A.a_plan, A.a_claims, A.a_slide, A.a_docs, A.b_three, A.b_tax, A.b_voice, A.b_registry, A.b_filing,
               A.b_offline, A.b_new, A.b_overturn):
        fn(True)
    bad = [(i["item"], i["detail"]) for i in A.items if i["status"] != "PASS"]
    assert not bad, bad
