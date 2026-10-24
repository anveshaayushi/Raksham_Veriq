"""Plan versus delivered page (Q3 item d): same data as PLAN_VS_DELIVERED.md (scripts/plan_vs_delivered.py)."""
from __future__ import annotations

import importlib.util
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]


def load():
    spec = importlib.util.spec_from_file_location("pvd", ROOT / "scripts" / "plan_vs_delivered.py")
    m = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(m)
    return m.build()


def render(st) -> None:
    d = load()
    st.header("Plan versus delivered")
    c = d["counts"]
    st.write(f"Every promise in our Round 1 deck, checked against what runs today. Built **{c['built']}**, partial "
             f"**{c['partial']}**, cut deliberately **{c['cut deliberately']}**, not built **{c['not built']}**. "
             "Each 'built' row names the CLAIMS.md line with its proof command.")
    st.dataframe([{"Deck": r["deck"], "Promise": r["promise"], "Status": r["status"],
                   "Proof": ", ".join(r["claims"]) or "-", "Note": r["note"]} for r in d["promises"]], hide_index=True)
    st.subheader("The deck's four finale targets")
    st.dataframe(d["targets"], hide_index=True)
