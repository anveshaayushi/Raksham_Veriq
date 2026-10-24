"""Q4: environment configuration, offline mode, smoke test, and static checks of the container files."""
from __future__ import annotations

import socket
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]


def test_config_defaults_and_overrides(monkeypatch, tmp_path):
    from app import config
    for k in ("VERIQ_DATA_DIR", "VERIQ_REGISTRY_DB", "VERIQ_MAX_UPLOAD_MB", "VERIQ_LANG", "VERIQ_OFFLINE"):
        monkeypatch.delenv(k, raising=False)
    c = config.load()
    assert (c.data_dir, c.registry_db, c.max_upload_mb, c.lang, c.offline) == (None, None, 20, "en", False)
    monkeypatch.setenv("VERIQ_DATA_DIR", str(tmp_path))
    monkeypatch.setenv("VERIQ_MAX_UPLOAD_MB", "5")
    monkeypatch.setenv("VERIQ_LANG", "HI")
    c = config.load()
    assert c.registry_db == str(tmp_path / "registry.db") and c.max_upload_mb == 5 and c.lang == "hi"
    monkeypatch.setenv("VERIQ_MAX_UPLOAD_MB", "lots")
    monkeypatch.setenv("VERIQ_LANG", "fr")
    assert config.load().max_upload_mb == 20 and config.load().lang == "en"
    from app import intake
    old = intake.MAX_AUDIO_BYTES
    monkeypatch.setenv("VERIQ_REGISTRY_DB", "placeholder")  # recorded by monkeypatch, so apply()'s change is undone
    monkeypatch.delenv("VERIQ_REGISTRY_DB")
    try:
        monkeypatch.setenv("VERIQ_MAX_UPLOAD_MB", "3")
        config.apply()
        assert intake.MAX_AUDIO_BYTES == 3 * 1024 * 1024
        assert config.load().registry_db == str(tmp_path / "registry.db")
    finally:
        intake.MAX_AUDIO_BYTES = intake.MAX_IMAGE_BYTES = old


def test_offline_mode_blocks_outgoing_but_not_loopback():
    from app import config
    config.blocked.clear()
    config.block_network()
    try:
        with socket.socket() as s:
            with pytest.raises(config.NetworkBlocked):
                s.connect(("8.8.8.8", 53))
        srv = socket.socket()
        srv.bind(("127.0.0.1", 0))
        srv.listen(1)
        with socket.socket() as c:
            c.connect(srv.getsockname())  # loopback is allowed
        srv.close()
        with socket.socket() as s:
            with pytest.raises(config.NetworkBlocked):
                s.connect(("example.com", 80))  # a host name would need DNS: blocked
    finally:
        config.unblock_network()
    assert config.blocked[:2] == ["('8.8.8.8', 53)", "('example.com', 80)"]


def test_smoke_without_the_web_app(capsys):
    sys.path.insert(0, str(ROOT / "scripts"))
    import smoke
    smoke.results.clear()
    rc = smoke.main(["--no-app"])
    out = capsys.readouterr().out
    assert "no outgoing network connection: 0 attempt(s)" in out
    assert rc == 0 or "ffmpeg not on PATH" in out


def test_container_files_follow_the_rules():
    d = (ROOT / "Dockerfile").read_text()
    c = (ROOT / "docker-compose.yml").read_text()
    assert "USER veriq" in d and "HEALTHCHECK" in d and "FROM python:3.11.9-slim-bookworm" in d
    assert "VERIQ_REGISTRY_SECRET_FILE: /run/secrets/registry_secret" in c and "read_only: true" in c
    assert "VERIQ_REGISTRY_SECRET:" not in c  # the key is never written into the compose file
    assert "secrets/" in (ROOT / ".gitignore").read_text() and "secrets" in (ROOT / ".dockerignore").read_text()
