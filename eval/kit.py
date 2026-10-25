"""Kit runner additions (Q3 item a): chats, WhatsApp zips and images inside `veriq-eval`, plus the judge report.

    ./veriq-eval --input <kit folder> [--labels labels.csv | --infer-labels-from-dirs] --out preds.csv --report report.md

What each modality returns (one CSV row per file, never a crash):
  audio / video  Claude B's voice pipeline (video: the audio track only, extracted by ffmpeg; no visual analysis).
                 The app's default has NO calibrated threshold, so most rows abstain ("cant_assess"); the raw score
                 is still written so a judge can compute AUC.
  chat (.txt, WhatsApp .zip)  VERIQ's rules engine, exactly as in the app. Answer mapped to the kit's two labels:
                 flagged  (pred "fake" = scam)    LINKED, NAME_DISCREPANCY, REGISTRATION_CONFLICT, HUMAN_REVIEW, or
                                                  INCONCLUSIVE with a hard pressure cue (fee to withdraw, OTP, ...)
                 no_signal (pred "real")          NO_MAJOR_ISSUE (which never means "safe")
                 cant_assess (no forced label)    INCONCLUSIVE without a hard cue (usually: nobody checked the payee
                                                  name in their bank app), or no payee / no dated message found
                 Optional label columns used for chats: claimed_firm, bank_app_names ("<upi>=<NAME>; ...").
  image          UPI QR codes are read and their payee reported. NO visual deepfake / manipulation claim: always
                 cant_assess with the reason.
Labels: a CSV (file,label[,dataset,codec,language,claimed_firm,bank_app_names]) or parent folders named
real/fake/bonafide/spoof/genuine/scam/legit/fraud. "scam"/"fraud" count as fake; "genuine"/"legit" as real.
"""
from __future__ import annotations

import concurrent.futures as cf
import math
from collections import Counter, defaultdict
from datetime import date
from pathlib import Path
from typing import Dict, List, Optional

ACCUSING = {"LINKED", "NAME_DISCREPANCY", "REGISTRATION_CONFLICT"}
FLAG_RESULTS = ACCUSING | {"HUMAN_REVIEW"}
MAX_KIT_FILE_BYTES = 60 * 1024 * 1024


def wilson(k: int, n: int, z: float = 1.96):
    if n == 0:
        return None
    p = k / n
    d = 1 + z * z / n
    c = (p + z * z / (2 * n)) / d
    h = z * math.sqrt(p * (1 - p) / n + z * z / (4 * n * n)) / d
    return [round(max(0.0, c - h), 3), round(min(1.0, c + h), 3)]


def _names(s: str) -> Dict[str, str]:
    out = {}
    for part in (s or "").split(";"):
        if "=" in part:
            k, v = part.split("=", 1)
            if k.strip() and v.strip():
                out[k.strip().lower().replace(" ", "")] = v.strip()
    return out


def chat_assessment(path: Path, lab_row: dict) -> dict:
    """Run one chat (.txt or WhatsApp .zip) through the app's engine. Returns state, pred_label, reasons."""
    from app.case import UserCheck, build_case
    from app.intake import Intake, IntakeError, add_chat, decode_text
    data = path.read_bytes()
    if len(data) > MAX_KIT_FILE_BYTES:
        return {"state": "cant_assess", "pred_label": "", "reasons": ["file_too_large"]}
    audio, images = {}, {}
    if path.suffix.lower() == ".zip":
        it = Intake()
        try:
            add_chat(it, path.name, data)
        except IntakeError as e:
            return {"state": "cant_assess", "pred_label": "", "reasons": [f"zip rejected: {e}"]}
        text = decode_text(it.chat.data)
        audio = {a.name: a.data for a in it.audio}
        images = {i.name: i.data for i in it.images}
    else:
        try:
            text = decode_text(data)
        except IntakeError as e:
            return {"state": "cant_assess", "pred_label": "", "reasons": [str(e)]}
    checks = {k: UserCheck(v, "Bank app (beneficiary name)", date.today()) for k, v in
              _names(lab_row.get("bank_app_names", "")).items()}
    c = build_case(case_id=path.stem[:40] or "kit", chat_text=text, claimed_firm=(lab_row.get("claimed_firm") or "").strip(),
                   checks=checks, audio=audio, images=images)
    res = c.case_result()
    hard = sorted({x.type for x in c.extraction.cues if x.severity == "hard"})
    payees = [p.value_norm for p in c.payees]
    reasons = [f"VERIQ answer: {res or 'none'}", f"payees: {', '.join(payees) or 'none found'}"]
    if hard:
        reasons.append("hard cues: " + ", ".join(hard))
    reasons += [w for w in c.extraction.warnings[:2]]
    if res is None:
        links = c.payment_links()
        if links:
            return {"state": "cant_assess", "pred_label": "", "reasons": reasons + [
                "asked to pay through a link (" + ", ".join(links[:2]) + "): VERIQ can't see who receives it; the app "
                "answers 'check before you pay'"]}
        return {"state": "cant_assess", "pred_label": "", "reasons": reasons + ["no payee or no dated message"]}
    if res in FLAG_RESULTS or (res == "INCONCLUSIVE" and hard):
        return {"state": "flagged", "pred_label": "fake", "reasons": reasons, "result": res}
    if res == "NO_MAJOR_ISSUE":
        return {"state": "no_signal", "pred_label": "real", "reasons": reasons + ["this is not a guarantee"], "result": res}
    return {"state": "cant_assess", "pred_label": "", "result": res,
            "reasons": reasons + ["inconclusive: no hard cue and no bank-app name check (the app would ask the user to check)"]}


def image_assessment(path: Path) -> dict:
    from parsing.qr import decode_qr, parse_upi
    data = path.read_bytes()
    found = [u for u in (parse_upi(p) for p in decode_qr(data)) if u]
    why = ["no visual deepfake or manipulation detection (not claimed)"]
    if found:
        why.insert(0, "UPI QR payee: " + "; ".join(f"{u['pa']} ({u['pn'] or 'no name'})" for u in found))
    else:
        why.insert(0, "no UPI QR code found")
    return {"state": "cant_assess", "pred_label": "", "reasons": why}


def with_timeout(fn, timeout_s: float, *args) -> dict:
    """Per-file time limit. A file that runs too long becomes cant_assess; the kit run continues."""
    ex = cf.ThreadPoolExecutor(max_workers=1)
    fut = ex.submit(fn, *args)
    try:
        return fut.result(timeout=timeout_s)
    except cf.TimeoutError:
        return {"state": "cant_assess", "pred_label": "", "reasons": [f"timeout: more than {timeout_s:.0f} s"]}
    except Exception as e:  # never crash the kit run
        return {"state": "cant_assess", "pred_label": "", "reasons": [f"internal_error:{type(e).__name__}"]}
    finally:
        ex.shutdown(wait=False, cancel_futures=True)


# ------------------------------------------------------------------------------------------------ report ----
def _metrics(rows: List[dict]) -> dict:
    lab = [r for r in rows if r["label"] in ("real", "fake")]
    decided = [r for r in lab if r["pred_label"] in ("real", "fake") and r["state"] != "cant_assess"]
    tp = sum(r["label"] == "fake" and r["pred_label"] == "fake" for r in decided)
    fp = sum(r["label"] == "real" and r["pred_label"] == "fake" for r in decided)
    tn = sum(r["label"] == "real" and r["pred_label"] == "real" for r in decided)
    fn = sum(r["label"] == "fake" and r["pred_label"] == "real" for r in decided)
    ab_real = sum(r["label"] == "real" for r in lab) - (fp + tn)
    ab_fake = sum(r["label"] == "fake" for r in lab) - (tp + fn)
    n_real, n_fake = fp + tn, tp + fn
    m = {"labelled": len(lab), "decided": len(decided), "abstained": len(lab) - len(decided),
         "abstention_rate": round((len(lab) - len(decided)) / len(lab), 3) if lab else None,
         "abstention_wilson95": wilson(len(lab) - len(decided), len(lab)),
         "confusion": {"real->real": tn, "real->fake": fp, "real->abstain": ab_real,
                       "fake->fake": tp, "fake->real": fn, "fake->abstain": ab_fake},
         "accuracy_on_decided": round((tp + tn) / len(decided), 3) if decided else None,
         "accuracy_wilson95": wilson(tp + tn, len(decided)),
         "precision_fake": round(tp / (tp + fp), 3) if tp + fp else None, "precision_wilson95": wilson(tp, tp + fp),
         "recall_fake": round(tp / n_fake, 3) if n_fake else None, "recall_wilson95": wilson(tp, n_fake),
         "false_positive_rate": round(fp / n_real, 3) if n_real else None, "fpr_wilson95": wilson(fp, n_real)}
    scored = [r for r in lab if r.get("score") not in ("", None) and r.get("polarity")]
    if scored and len({r["label"] for r in scored}) == 2:
        from eval import metrics as M
        sign = -1.0 if scored[0]["polarity"] == "higher_is_real" else 1.0
        fk = [sign * float(r["score"]) for r in scored if r["label"] == "fake"]
        rl = [sign * float(r["score"]) for r in scored if r["label"] == "real"]
        m["auc_raw_score"] = round(M.auc(fk, rl), 3) if fk and rl else None
        m["eer_raw_score"] = round(M.eer(fk, rl), 3) if fk and rl else None
    return m


def _clean(md: str) -> str:
    """Never print a bare 'None': say why a metric has no value."""
    md = md.replace("None (n=0)", "n/a (0 files decided)")
    md = md.replace("| **None** |", "| **n/a** (no genuine file decided) |").replace("| None |", "| n/a |")
    return md.replace("| None |", "| n/a |")


def build_report(rows: List[dict], command: str, polarity: Optional[str]) -> str:
    return _clean(_build_report(rows, command, polarity))


def _build_report(rows: List[dict], command: str, polarity: Optional[str]) -> str:
    for r in rows:
        r["polarity"] = polarity or ""
    by_mod: Dict[str, List[dict]] = defaultdict(list)
    for r in rows:
        by_mod[r["modality"]].append(r)
    L = ["# VERIQ kit report", "", f"Command: `{command}`", "",
         f"Files: {len(rows)} ({', '.join(f'{k}: {len(v)}' for k, v in sorted(by_mod.items()))}). "
         f"Labelled: {sum(r['label'] in ('real', 'fake') for r in rows)}.", "",
         "Each file gets one of three states: **flagged** (counted as 'fake'/'scam'), **no_signal** (counted as "
         "'real'; for chats this is VERIQ's 'No major issue', which never means safe), or **cant_assess** "
         "(VERIQ abstains). Accuracy, precision, recall and false-positive rate are on the files VERIQ decided; "
         "abstentions are reported separately and never hidden.", ""]
    for mod, rs in sorted(by_mod.items()):
        m = _metrics(rs)
        L += [f"## {mod} ({len(rs)} files, {m['labelled']} labelled)", ""]
        if not m["labelled"]:
            L += ["No labels for this modality: states only.", "",
                  "| State | Files |", "|---|---|"] + [f"| {k} | {v} |" for k, v in Counter(r['state'] for r in rs).most_common()] + [""]
            continue
        c = m["confusion"]
        L += ["| Metric | Value | 95% Wilson interval |", "|---|---|---|",
              f"| Test-set size (labelled) | {m['labelled']} | |",
              f"| Abstained (cant_assess) | {m['abstained']} ({m['abstention_rate']}) | {m['abstention_wilson95']} |",
              f"| Accuracy on decided files | {m['accuracy_on_decided']} (n={m['decided']}) | {m['accuracy_wilson95']} |",
              f"| Precision (fake/scam) | {m['precision_fake']} | {m['precision_wilson95']} |",
              f"| Recall (fake/scam) | {m['recall_fake']} | {m['recall_wilson95']} |",
              f"| **False-positive rate** (real called fake) | **{m['false_positive_rate']}** | {m['fpr_wilson95']} |"]
        if "auc_raw_score" in m:
            L.append(f"| AUC / EER of the raw score (all labelled, abstentions included) | {m['auc_raw_score']} / {m['eer_raw_score']} | |")
        L += ["", "Confusion matrix (rows: true label; columns: VERIQ):", "",
              "| true \\ VERIQ | fake/scam | real | abstain |", "|---|---|---|---|",
              f"| fake/scam | {c['fake->fake']} | {c['fake->real']} | {c['fake->abstain']} |",
              f"| real | {c['real->fake']} | {c['real->real']} | {c['real->abstain']} |", ""]
        for col in ("dataset", "codec", "language"):
            vals = sorted({r.get(col, "") for r in rs if r.get(col)})
            if len(vals) > 1:
                L += [f"By {col}:", "", "| " + col + " | labelled | abstained | accuracy (decided) | FPR | recall |",
                      "|---|---|---|---|---|---|"]
                for v in vals:
                    mm = _metrics([r for r in rs if r.get(col) == v])
                    L.append(f"| {v} | {mm['labelled']} | {mm['abstained']} | {mm['accuracy_on_decided']} | "
                             f"{mm['false_positive_rate']} | {mm['recall_fake']} |")
                L.append("")
        fails = [r for r in rs if r["label"] in ("real", "fake") and r["pred_label"] in ("real", "fake")
                 and r["state"] != "cant_assess" and r["pred_label"] != r["label"]]
        L += ["### Failure cases", ""]
        if fails:
            L += ["| File | True | VERIQ | Why (VERIQ's own reasons) |", "|---|---|---|---|"]
            for r in fails[:20]:
                L.append(f"| {r['file_id']} | {r['label']} | {r['pred_label']} ({r['state']}) | "
                         f"{str(r['reasons'])[:160].replace('|', '/')} |")
            if len(fails) > 20:
                L.append(f"| ... {len(fails) - 20} more in the CSV | | | |")
        else:
            L.append("None among the decided files.")
        L.append("")
    L += ["## Known limits", "",
          "Voice: pretrained AASIST with a threshold fitted on ASVspoof 2019 LA dev is a WEAK cue (on LA eval it "
          "flagged 16% of genuine clips and missed 56% of synthetic ones; In-the-Wild not run); in the app a voice "
          "result never clears or accuses a payee. Video: audio track only. Images: "
          "QR payees only, no visual deepfake detection. Chats: rules written by the team; without a bank-app name "
          "check most chats are 'Inconclusive' (abstain here). Small sets have wide intervals.", ""]
    return "\n".join(L)
