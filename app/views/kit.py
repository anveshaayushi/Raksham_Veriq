"""Kit tab (Q3 item a): a judge uploads a .zip of a test folder and gets VERIQ's per-file answers and the report.

Same code as the command line (`veriq-eval ... --report report.md`). Labels: a labels.csv inside the zip
(file,label[,dataset,codec,language,claimed_firm,bank_app_names]) or folders named real/fake/scam/genuine/...
The zip is unpacked with the same safety checks as chat uploads into a private temp folder that is deleted at once.
"""
from __future__ import annotations

import csv
import io
import shutil
import tempfile
import zipfile
from pathlib import Path

MAX_KIT_ZIP = 300 * 1024 * 1024
MAX_KIT_MEMBERS = 3000
MAX_KIT_UNCOMPRESSED = 1024 * 1024 * 1024
MAX_RATIO = 200


class KitError(ValueError):
    pass


def unpack(data: bytes, dest: Path) -> int:
    if len(data) > MAX_KIT_ZIP:
        raise KitError("The kit .zip is larger than 300 MB; use the command line (veriq-eval) instead.")
    try:
        zf = zipfile.ZipFile(io.BytesIO(data))
    except zipfile.BadZipFile as e:
        raise KitError("Not a valid .zip file.") from e
    infos = [i for i in zf.infolist() if not i.is_dir()]
    if len(infos) > MAX_KIT_MEMBERS:
        raise KitError(f"More than {MAX_KIT_MEMBERS} files.")
    total = 0
    for i in infos:
        n = i.filename.replace("\\", "/")
        if n.startswith("/") or ".." in n.split("/") or ":" in n:
            raise KitError("Unsafe file path in the zip.")
        if i.flag_bits & 0x1:
            raise KitError("Encrypted zips are not supported.")
        total += i.file_size
        if total > MAX_KIT_UNCOMPRESSED or (i.compress_size and i.file_size / i.compress_size > MAX_RATIO):
            raise KitError("The zip expands to too much data (possible zip bomb).")
    for i in infos:
        out = dest / i.filename.replace("\\", "/")
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_bytes(zf.read(i))
    return len(infos)


def run_kit(data: bytes, timeout_s: float = 30.0) -> dict:
    """Unpack, evaluate, build the report, delete everything. Returns csv text, report text, row count."""
    from eval.cli import FIELDS, _read_labels, build_detector, evaluate_folder
    from eval.kit import build_report

    class Args:
        detector, aasist_repo, aasist_weights, calibration = "aasist", None, None, None

    td = Path(tempfile.mkdtemp(prefix="veriq_kit_"))
    try:
        unpack(data, td)
        roots = [p for p in td.iterdir() if p.is_dir()]
        root = roots[0] if len(roots) == 1 and not any(p.is_file() for p in td.iterdir()) else td
        lab = next(iter(sorted(root.rglob("labels.csv"))), None)
        labels = _read_labels(lab) if lab else {}
        det, err = build_detector(Args)
        cal = None
        from app.config import voice_calibration_path
        from voice.calibration import CalibrationError, load_calibration
        if det is not None and voice_calibration_path():
            try:
                cal = load_calibration(voice_calibration_path())
            except CalibrationError:
                cal = None
        rows = evaluate_folder(root, det, err, cal, labels, infer_dirs=not labels, timeout_s=timeout_s)
        for r in rows:
            r["path"] = ""  # never show server paths
        buf = io.StringIO()
        w = csv.DictWriter(buf, fieldnames=FIELDS)
        w.writeheader()
        w.writerows(rows)
        polarity = cal.polarity if cal else getattr(det, "native_polarity", None)
        rep = build_report(rows, "VERIQ app, Kit tab (same code as veriq-eval)", polarity)
        return {"csv": buf.getvalue(), "report": rep, "n": len(rows), "labels": "labels.csv" if lab else "folder names"}
    finally:
        shutil.rmtree(td, ignore_errors=True)


def render(st) -> None:
    st.header("Kit runner (for judges)")
    st.write("Upload a **.zip of a test folder**: voice notes (.opus .wav .mp3 .m4a ...), videos (audio track only), "
             "images (UPI QR codes only) and WhatsApp chats (.txt or the WhatsApp .zip). Labels come from a `labels.csv` "
             "in the zip or from folder names (real / fake / scam / genuine). You get one answer per file and a report "
             "with accuracy, precision, recall, **false-positive rate**, abstentions and 95% intervals.")
    st.caption("Same code as the command line: `veriq-eval --input <folder> --out preds.csv --report report.md`. "
               "Files are unpacked to a private temp folder and deleted as soon as the report is built.")
    up = st.file_uploader("Kit (.zip)", type=["zip"], key="kit_zip")
    if up is not None and st.button("Run the kit", key="kit_run"):
        with st.spinner("Scoring every file (voice notes take about half a second each)..."):
            try:
                S = st.session_state
                S.kit_out = run_kit(up.getvalue())
            except KitError as e:
                st.error(str(e))
    out = st.session_state.get("kit_out")
    if out:
        st.success(f"{out['n']} files scored (labels from {out['labels']}).")
        st.download_button("Download predictions (CSV)", out["csv"], "veriq_kit_predictions.csv", "text/csv", key="kit_dl_csv")
        st.download_button("Download report (Markdown)", out["report"], "veriq_kit_report.md", "text/markdown", key="kit_dl_md")
        st.markdown(out["report"])
