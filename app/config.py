"""Deployment settings from environment variables (Q4 item d). Every setting has a safe default for a laptop demo.

| Variable | Default | Meaning |
|---|---|---|
| VERIQ_DATA_DIR | (none) | folder for persistent data (registry database); only used when set |
| VERIQ_REGISTRY_DB | $VERIQ_DATA_DIR/registry.db if VERIQ_DATA_DIR is set | SQLite registry file; unset = demo stub registry |
| VERIQ_REGISTRY_SECRET / VERIQ_REGISTRY_SECRET_FILE | (none) | HMAC key (16+ chars) or a file holding it; never in the repo |
| VERIQ_MAX_UPLOAD_MB | 20 | largest single voice note / image accepted (chat .txt stays 2 MB) |
| VERIQ_LANG | en | en or hi: answer labels also shown in Hindi when hi |
| VERIQ_OFFLINE | 0 | 1 = block every outgoing network connection from VERIQ's own code (loopback still allowed) |
| VERIQ_VOICE_HEAD | 0 | 1 = use the in-domain trained voice head (failed cross-dataset; demo only) |
| VERIQ_AASIST_REPO | external/aasist | AASIST code + weights folder |
| VERIQ_VOICE_CALIBRATION | results/asvspoof/calibration_asvspoof_dev.json | voice threshold (fitted on ASVspoof 2019 LA DEV by Claude B); "none" = no threshold, every voice note abstains |
"""
from __future__ import annotations

import ipaddress
import os
import socket
from dataclasses import dataclass
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
# Weak review cue (Prompt 2, block B): pretrained AASIST with the threshold Claude B fitted on ASVspoof 2019 LA dev.
# On LA eval it flagged 16% of genuine clips and missed 56% of synthetic ones, so a flag only asks for human review
# and "no_signal" never clears a payee (rules/). voice/calibration.json itself is NOT written.
DEFAULT_VOICE_CALIBRATION = ROOT / "results" / "asvspoof" / "calibration_asvspoof_dev.json"


def voice_calibration_path() -> str | None:
    v = os.environ.get("VERIQ_VOICE_CALIBRATION")
    if v is not None:
        return None if v.lower() == "none" else v
    return str(DEFAULT_VOICE_CALIBRATION) if DEFAULT_VOICE_CALIBRATION.is_file() else None


@dataclass(frozen=True)
class Config:
    data_dir: Path | None
    registry_db: str | None
    max_upload_mb: int
    lang: str
    offline: bool
    voice_head: bool


def load() -> Config:
    data = os.environ.get("VERIQ_DATA_DIR")
    reg = os.environ.get("VERIQ_REGISTRY_DB") or (str(Path(data) / "registry.db") if data else None)
    try:
        mb = max(1, min(200, int(os.environ.get("VERIQ_MAX_UPLOAD_MB", "20"))))
    except ValueError:
        mb = 20
    lang = os.environ.get("VERIQ_LANG", "en").lower()
    return Config(Path(data) if data else None, reg, mb, lang if lang in ("en", "hi") else "en",
                  os.environ.get("VERIQ_OFFLINE", "0") == "1", os.environ.get("VERIQ_VOICE_HEAD", "0") == "1")


class NetworkBlocked(OSError):
    pass


_real_connect = socket.socket.connect


def _is_loopback(address) -> bool:
    host = address[0] if isinstance(address, tuple) else address
    if not isinstance(host, str):
        return True  # unix sockets etc.
    if host in ("localhost", ""):
        return True
    try:
        return ipaddress.ip_address(host.split("%")[0]).is_loopback
    except ValueError:
        return False  # a host name: would need DNS, i.e. the network


def block_network() -> None:
    """Offline mode: any connection to a non-loopback address raises NetworkBlocked (and is counted)."""
    def guarded(self, address):
        if not _is_loopback(address):
            blocked.append(str(address))
            raise NetworkBlocked(f"VERIQ_OFFLINE=1: outgoing connection to {address} blocked")
        return _real_connect(self, address)
    socket.socket.connect = guarded


def unblock_network() -> None:
    socket.socket.connect = _real_connect


blocked: list[str] = []


def apply(cfg: Config | None = None) -> Config:
    cfg = cfg or load()
    if cfg.registry_db and not os.environ.get("VERIQ_REGISTRY_DB"):
        os.environ["VERIQ_REGISTRY_DB"] = cfg.registry_db
    if cfg.offline:
        block_network()
    cal = voice_calibration_path()
    if cal and not os.environ.get("VERIQ_VOICE_CALIBRATION"):
        os.environ["VERIQ_VOICE_CALIBRATION"] = cal  # read by voice/service.py when the model first loads
    from app import intake
    intake.MAX_AUDIO_BYTES = intake.MAX_IMAGE_BYTES = cfg.max_upload_mb * 1024 * 1024
    return cfg
