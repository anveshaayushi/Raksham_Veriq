"""Privacy proof (Q3 item c): what VERIQ holds about you, deleted in front of you; the registry holds only keyed hashes.

1. "Delete my data": lists what this browser session holds (chat, voice notes, images, case) and VERIQ's temporary
   folders on this computer (names starting with veriq_), deletes them, and shows the same lists again (empty).
2. Registry view: what a cross-victim registry file actually stores, row by row. Identifiers are HMAC-SHA256 hashes
   keyed with a secret that is not in the file; the page searches the raw bytes of the file for the identifiers and
   shows that none are found. Keyed hashes are pseudonymisation, not anonymity: whoever holds the key can test a guess.
tests/completeness/test_privacy_proof.py proves the same things automatically.
"""
from __future__ import annotations

import shutil
import sqlite3
import tempfile
import time
from pathlib import Path

SESSION_DATA_KEYS = ("intake", "case", "chat_text", "checks", "audio", "images", "kit_out", "pl_chat", "ledger",
                     "pl_ledger", "paste_text")


TEMP_PREFIXES = ("veriq_voice_", "veriq_kit_", "veriq_privacy_")  # folders this app creates (never other programs')


def veriq_temp_folders() -> list[str]:
    root = Path(tempfile.gettempdir())
    return sorted(p.name for p in root.iterdir() if p.name.startswith(TEMP_PREFIXES) and p.exists())


def session_holdings(S) -> list[str]:
    out = []
    for k in SESSION_DATA_KEYS:
        if k in S and S[k] not in (None, "", {}, []):
            v = S[k]
            size = len(v) if hasattr(v, "__len__") else 1
            out.append(f"{k} ({type(v).__name__}, {size} item(s) or characters)")
    return out


def delete_everything(S) -> dict:
    before = {"session": session_holdings(S), "temp_folders": veriq_temp_folders()}
    for k in list(S.keys()):
        del S[k]
    for name in before["temp_folders"]:
        shutil.rmtree(Path(tempfile.gettempdir()) / name, ignore_errors=True)
    after = {"session": session_holdings(S), "temp_folders": veriq_temp_folders()}
    return {"before": before, "after": after, "at": time.strftime("%H:%M:%S")}


def demo_registry_rows(identifiers=("ramesh.k@upi", "sunita.t@upi", "30112233445021")) -> dict:
    """Builds a throwaway registry with synthetic reports, reads back every row and scans the raw file bytes."""
    from registry.sqlite_registry import BURST_WINDOW_S, SQLiteRegistry, create_db, new_reporter_token
    td = Path(tempfile.mkdtemp(prefix="veriq_privacy_"))
    try:
        db = td / "registry_demo.db"
        create_db(db)
        t = [1_800_000_000.0]
        reg = SQLiteRegistry(db, secret=b"privacy-demo-secret-" + str(time.time()).encode(), clock=lambda: t[0])
        for i, v in enumerate(identifiers):
            for _ in range(2 if i < 2 else 1):
                reg.report("upi_vpa" if "@" in v else "bank_account", v, new_reporter_token())
                t[0] += BURST_WINDOW_S + 1
        con = sqlite3.connect(db)
        rows = [dict(zip([d[0] for d in cur.description], r)) for cur in [con.execute("SELECT * FROM reports")]
                for r in cur.fetchall()]
        con.close()
        raw = db.read_bytes()
        found = {v: (v.encode() in raw) for v in identifiers}
        return {"rows": rows, "raw_identifier_found_in_file": found, "file_bytes": len(raw)}
    finally:
        shutil.rmtree(td, ignore_errors=True)


def render(st) -> None:
    S = st.session_state
    st.header("Privacy proof")
    st.write("VERIQ keeps your files only in this browser session's memory. Voice notes are written to a private "
             "temporary folder for a moment while ffmpeg reads them and deleted before the answer is shown.")
    st.subheader("1 · What VERIQ holds about you right now")
    st.write({"this session": session_holdings(S) or ["nothing"], "temporary folders (veriq_voice_ / veriq_kit_ / veriq_privacy_)": veriq_temp_folders() or ["none"]})
    if st.button("Delete my data now and show me", key="priv_delete"):
        S["_priv_last"] = delete_everything(S)
    last = S.get("_priv_last")
    if last:
        st.success(f"Deleted at {last['at']}.")
        st.write({"before": last["before"], "after": last["after"]})
    st.subheader("2 · What the cross-victim registry stores")
    st.write("A throwaway registry is created with three synthetic reports, read back row by row, scanned for the raw "
             "UPI IDs and account number, and deleted.")
    if st.button("Build, inspect and delete a demo registry", key="priv_reg"):
        S["_priv_reg"] = demo_registry_rows()
    reg = S.get("_priv_reg")
    if reg:
        st.dataframe([{k: (str(v)[:24] + "…" if isinstance(v, str) and len(str(v)) > 24 else v) for k, v in r.items()}
                      for r in reg["rows"]], hide_index=True)
        st.write({f"'{k}' in the file?": ("FOUND" if v else "not found") for k, v in reg["raw_identifier_found_in_file"].items()})
        st.caption("Keyed hashes are pseudonymisation, not anonymity: whoever holds the secret key can test a guessed "
                   "identifier. The key is never stored in the registry file.")
