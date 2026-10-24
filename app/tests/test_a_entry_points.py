"""When Claude A's parse_chat/extract exist, the app calls them and merges voice transcripts first (A's CR-8)."""
import sys
import types

from app.adapters import extract as ex_adapter
from app.contracts import Message


def test_calls_claude_a_and_merges_transcripts(monkeypatch):
    seen = {}
    parsing = types.ModuleType("parsing")
    parsing.parse_chat = lambda text: [Message(msg_id=1, ts="2026-10-20T20:59", sender="R", kind="voice", text="",
                                               media_ref="PTT-1.opus")]
    extract = types.ModuleType("extract")

    def fake_extract(msgs, case_id):
        seen["text"] = msgs[0].text
        return [], []
    extract.extract = fake_extract
    monkeypatch.setitem(sys.modules, "parsing", parsing)
    monkeypatch.setitem(sys.modules, "extract", extract)
    out = ex_adapter.run("x", "c1", {"PTT-1.opus": "pay sunita.t@upi"})
    assert seen["text"] == "pay sunita.t@upi" and not out.is_stub and "extract/" in out.source
