"""Threshold/calibration file handling.

Plain words: a detector outputs a raw number. A *threshold* turns it into
"flag / don't flag". A threshold only makes sense for the exact model it was
fitted for, so the file records the model_version and we REFUSE to apply it to a
different model. Without a valid file, the system abstains (cant_assess) and
keeps the raw score for inspection. We never ship a made-up threshold.

File format (JSON):
{
  "threshold": -1.23,                 # float, fitted on a DEV set, never on test data
  "polarity": "higher_is_real",       # or "higher_is_fake"
  "score_kind": "raw",                # "raw" (logit) or "calibrated" (Platt/isotonic output)
  "model_version": "aasist-...",      # must equal detector.model_version
  "calibrated_on": "free text: which dev sets, codecs, date",
  "target_false_alarm": 0.05
}
"""
from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Optional

POLARITIES = ("higher_is_real", "higher_is_fake")
SCORE_KINDS = ("raw", "calibrated")


class CalibrationError(Exception):
    pass


@dataclass(frozen=True)
class Calibration:
    threshold: float
    polarity: str
    score_kind: str
    model_version: str
    calibrated_on: str = ""
    target_false_alarm: Optional[float] = None

    def is_fake_side(self, score: float) -> bool:
        """True if the score falls on the 'possible manipulation' side of the threshold."""
        if self.polarity == "higher_is_real":
            return score < self.threshold
        return score >= self.threshold


def load_calibration(path: str | Path) -> Calibration:
    try:
        d = json.loads(Path(path).read_text(encoding="utf-8"))
        cal = Calibration(
            threshold=float(d["threshold"]),
            polarity=str(d["polarity"]),
            score_kind=str(d.get("score_kind", "raw")),
            model_version=str(d["model_version"]),
            calibrated_on=str(d.get("calibrated_on", "")),
            target_false_alarm=(None if d.get("target_false_alarm") is None else float(d["target_false_alarm"])),
        )
    except (OSError, ValueError, KeyError, TypeError) as e:
        raise CalibrationError(f"cannot read calibration file {path}: {type(e).__name__}: {e}")
    if cal.polarity not in POLARITIES:
        raise CalibrationError(f"polarity must be one of {POLARITIES}")
    if cal.score_kind not in SCORE_KINDS:
        raise CalibrationError(f"score_kind must be one of {SCORE_KINDS}")
    if not cal.model_version:
        raise CalibrationError("model_version is required")
    return cal


def save_calibration(cal: Calibration, path: str | Path) -> None:
    Path(path).write_text(
        json.dumps(
            {
                "threshold": cal.threshold,
                "polarity": cal.polarity,
                "score_kind": cal.score_kind,
                "model_version": cal.model_version,
                "calibrated_on": cal.calibrated_on,
                "target_false_alarm": cal.target_false_alarm,
            },
            indent=2,
        ),
        encoding="utf-8",
    )
