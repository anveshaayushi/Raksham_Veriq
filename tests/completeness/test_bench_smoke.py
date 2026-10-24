"""Smoke and reproducibility tests for the benchmark and data-generation scripts (organisers' rules 1 and 2).

Plain words: these run every script that produces a reported number or a synthetic dataset, on small inputs,
and check that (a) the synthetic data generators reproduce the committed files byte for byte, (b) the benchmark
scripts run end to end and write the result fields RESULTS.md quotes, (c) the red-team defences still hold.
The full-size runs are in `python scripts/reproduce.py` (REPRODUCE.md)."""
from __future__ import annotations

import csv
import json
import shutil
import sys
import types
import wave
from pathlib import Path

import numpy as np
import pytest

ROOT = Path(__file__).resolve().parents[2]
HAS_FFMPEG = shutil.which("ffmpeg") is not None


# ------------------------------------------------------------------ synthetic chat generator ----
def test_chat_generator_reproduces_the_committed_benchmark_byte_for_byte(tmp_path, monkeypatch, capsys):
    from bench import generate
    monkeypatch.setattr(generate, "OUT", tmp_path)
    generate.main()
    assert "wrote test: 300 chats" in capsys.readouterr().out
    for split in ("dev", "test"):
        assert (tmp_path / f"{split}.json").read_bytes() == (ROOT / "bench" / "data" / f"{split}.json").read_bytes()


def test_chat_generator_is_seeded_and_labels_every_case():
    from bench.generate import generate
    a, b = generate("dev", 12, 7), generate("dev", 12, 7)
    assert a == b and generate("dev", 12, 8) != a
    kinds = {c["kind"] for c in a}
    assert {"scam_rotation", "legit_match", "no_check"} <= kinds
    assert all(len(c["expected"]) == len(c["payees"]) and isinstance(c["is_scam"], bool) for c in a)


def test_campaign_generator_reproduces_the_committed_files(tmp_path):
    from data.synthetic.generate_campaigns import generate_campaign_data
    generate_campaign_data(str(tmp_path))
    for f in ("campaign_cases.json", "registry_seed.json"):
        assert (tmp_path / f).read_bytes() == (ROOT / "data" / "synthetic" / f).read_bytes()
    seed = json.loads((tmp_path / "registry_seed.json").read_text(encoding="utf-8"))
    assert all("SYNTHETIC" in r["source"] for r in seed)


# ------------------------------------------------------------------ chat benchmark runner ----
def test_benchmark_runner_end_to_end_on_a_small_split(tmp_path, monkeypatch, capsys):
    from bench import run
    (tmp_path / "data").mkdir()
    cases = json.loads((ROOT / "bench" / "data" / "dev.json").read_text(encoding="utf-8"))[:18]
    (tmp_path / "data" / "smoke.json").write_text(json.dumps(cases), encoding="utf-8")
    monkeypatch.setattr(run, "HERE", tmp_path)
    assert run.main(["run", "smoke"]) == 0
    r = json.loads((tmp_path / "results_smoke.json").read_text(encoding="utf-8"))
    assert r["chats"] == 18 and r["payees"] == sum(len(c["payees"]) for c in cases)
    for k in ("extraction", "decision_accuracy", "false_alarms_on_legit_payees", "scam_payees_marked_no_major_issue",
              "confusion", "ms_per_chat", "failure_count"):
        assert k in r
    assert '"split": "smoke"' in capsys.readouterr().out


def test_committed_test_results_match_a_fresh_run():
    """The numbers on the results page (bench/results_test.json) are what the code produces today."""
    from bench.run import run_case
    cases = json.loads((ROOT / "bench" / "data" / "test.json").read_text(encoding="utf-8"))
    committed = json.loads((ROOT / "bench" / "results_test.json").read_text(encoding="utf-8"))
    correct = total = 0
    for c in cases:
        out = run_case(c)
        for p, exp in zip([p["value_norm"] for p in c["payees"]], c["expected"]):
            total += 1
            correct += out["results"].get(p) == exp
    assert total == committed["payees"] and round(correct / total, 4) == committed["decision_accuracy"]


# ------------------------------------------------------------------ red-team set ----
def test_red_team_defences_hold_and_known_gaps_are_reported(tmp_path, monkeypatch, capsys):
    pytest.importorskip("cv2")
    from bench import adversarial
    monkeypatch.setattr(adversarial, "HERE", tmp_path)
    assert adversarial.main(["adv"]) == 0
    r = json.loads((tmp_path / "results_adversarial.json").read_text(encoding="utf-8"))
    assert r["defended_attacks_passed"] == r["defended_attacks"]  # every defended attack still defended
    committed = json.loads((ROOT / "bench" / "results_adversarial.json").read_text(encoding="utf-8"))
    assert (r["cases"], r["known_gaps"]) == (committed["cases"], committed["known_gaps"])
    assert "| Group | Attack |" in capsys.readouterr().out


# ------------------------------------------------------------------ voice benchmark helpers ----
def test_voice_metric_helpers():
    pytest.importorskip("sklearn", reason="voice extras not installed")
    from bench.voice import train_eval as T
    y = np.array([0, 0, 0, 0, 1, 1, 1, 1])
    s = np.array([0.1, 0.2, 0.3, 0.4, 0.6, 0.7, 0.8, 0.9])
    assert T.roc_auc(y, s) == 1.0 and T.eer(y, s) == 0.0
    thr = T.thr_at_far(s[y == 0], far=0.0)
    assert thr >= 0.4 and T.rates(y, s, thr) == (0.0, 1.0)
    gf, fc = T.boot(y, s, thr, n=50)
    assert gf == [0.0, 0.0] and fc == [1.0, 1.0]


def _write_wav(p: Path, x: np.ndarray, sr=16000):
    with wave.open(str(p), "wb") as w:
        w.setnchannels(1)
        w.setsampwidth(2)
        w.setframerate(sr)
        w.writeframes((np.clip(x, -1, 1) * 32767).astype("<i2").tobytes())


def _speechlike(seconds, seed, amp):
    rng = np.random.default_rng(seed)
    n = int(seconds * 16000)
    t = np.arange(n) / 16000
    x = rng.standard_normal(n) * 0.001
    on = (t % 0.4) < 0.25
    x[on] = rng.standard_normal(on.sum()) * amp
    return x.astype(np.float32)


@pytest.mark.skipif(not HAS_FFMPEG, reason="ffmpeg not installed")
def test_voice_train_eval_end_to_end_with_a_stand_in_model(tmp_path, monkeypatch, capsys):
    """Runs the full training/evaluation script on 36 noise clips with a tiny stand-in model (not AASIST): proves
    the script, the dev-threshold rule and the head export run. Says nothing about accuracy."""
    torch = pytest.importorskip("torch", reason="voice extras not installed")
    pytest.importorskip("sklearn")
    pytest.importorskip("soundfile")
    from bench.voice import train_eval as T

    data = tmp_path / "set"
    rows = []
    for split in ("train", "dev", "test"):
        (data / split).mkdir(parents=True)
        for i in range(6):
            for label, amp in (("real", 0.1), ("fake", 0.4)):  # both pass the quality gate (0.6 would clip)
                name = f"{split}/{label}_{i}.wav"
                _write_wav(data / name, _speechlike(3.0, 10 * i + len(split) + len(label), amp))
                rows.append([name, label, f"{label}{i % 3}", split, "en", 3.0])
    rows.append(["test/hi_0.wav", "fake", "hf_x", "test", "hi", 3.0])
    _write_wav(data / "test" / "hi_0.wav", _speechlike(3.0, 99, 0.4))
    with open(data / "labels.csv", "w", newline="", encoding="utf-8") as f:
        csv.writer(f).writerows([["file", "label", "source", "split", "lang", "seconds"], *rows])

    class Stand:
        model_version = "standin@000000000000"
        chunk_samples = 16000
        _torch = torch
        _device = "cpu"

        @staticmethod
        def _model(t):
            f = torch.stack([t.std(1), t.abs().amax(1)], 1)
            return f.repeat(1, 80), torch.stack([-t.std(1), t.std(1)], 1)

    monkeypatch.setattr(T, "load_detector", lambda repo: Stand())
    out = tmp_path / "out" / "results.json"
    out.parent.mkdir()
    monkeypatch.setattr(sys, "argv", ["train_eval", "--data", str(data), "--aasist", "unused", "--out", str(out)])
    T.main()
    r = json.loads(out.read_text())
    assert r["n"] == {"train": 12, "dev": 12, "test_en": 12, "test_hindi_fake_only": 1}
    for d in ("pretrained", "trained_head"):
        assert 0.0 <= r["detectors"][d]["test_auc"] <= 1.0 and len(r["detectors"][d]["test_genuine_flagged_95ci"]) == 2
    head = json.loads((out.parent / "head.json").read_text())
    cal = json.loads((out.parent / "head_calibration.json").read_text())
    assert len(head["coef"]) == 160 and cal["model_version"].startswith("standin@000000000000+head@")


@pytest.mark.skipif(not HAS_FFMPEG, reason="ffmpeg not installed")
def test_voice_set_builder_end_to_end_with_stand_in_inputs(tmp_path, monkeypatch, capsys):
    """make_set.py with 6 fake 'FSDD' speakers (noise, not speech) and a stand-in TTS: checks the speaker-disjoint
    split rule, the Opus round trip and labels.csv. The real set needs FSDD + Kokoro (REPRODUCE.md)."""
    pytest.importorskip("torchaudio", reason="voice extras not installed")
    sf = pytest.importorskip("soundfile")
    from bench.voice import make_set as M
    fsdd = tmp_path / "fsdd"
    fsdd.mkdir()
    for s in M.SPK:
        for d in range(10):
            sf.write(fsdd / f"{d}_{s}_0.wav", _speechlike(0.3, d, 0.3), 8000)

    class FakeKokoro:
        def __init__(self, model, voices):
            pass

        def create(self, text, voice, speed, lang):
            return _speechlike(1.0, len(text), 0.3), 24000

    monkeypatch.setitem(sys.modules, "kokoro_onnx", types.SimpleNamespace(Kokoro=FakeKokoro))
    out = tmp_path / "set"
    monkeypatch.setattr(sys, "argv", ["make_set", "--fsdd", str(fsdd), "--kokoro", "k.onnx", "--voices", "v.bin",
                                      "--out", str(out), "--per-speaker", "1", "--per-voice", "1"])
    M.main()
    rows = list(csv.DictReader(open(out / "labels.csv", encoding="utf-8")))
    assert len(rows) == len(M.SPK) + len(M.EN_VOICES) + len(M.HI_VOICES)
    by_split = {}
    for r in rows:
        by_split.setdefault(r["split"], set()).add(r["source"])
        assert (out / r["file"]).is_file()
    assert not (by_split["train"] & by_split["test"]) and not (by_split["dev"] & by_split["test"])  # disjoint
    assert {r["lang"] for r in rows if r["split"] == "test"} == {"en", "hi"}


# ------------------------------------------------------------------ dataset bookkeeping scripts ----
def test_dataset_registry_script(tmp_path, monkeypatch, capsys):
    sys.path.insert(0, str(ROOT / "scripts"))
    import datasets as DS
    monkeypatch.setattr(DS, "RAW", tmp_path)
    for argv in (["list"], ["status"], ["disclosure"]):
        monkeypatch.setattr(sys, "argv", ["datasets.py", *argv])
        DS.main()
    out = capsys.readouterr().out
    assert "licence=UNVERIFIED" in out and "NO - do not use yet" in out and "not cleared for use" in out
    monkeypatch.setattr(sys, "argv", ["datasets.py", "record", "asvspoof2019_la", "--source-url", "https://example",
                                      "--licence", "ODC-By 1.0", "--allowed", "dev,test", "--checked-by", "team"])
    DS.main()
    monkeypatch.setattr(sys, "argv", ["datasets.py", "disclosure"])
    DS.main()
    assert "| asvspoof2019_la | train/dev | https://example | ODC-By 1.0 | dev, test |" in capsys.readouterr().out
    monkeypatch.setattr(sys, "argv", ["datasets.py", "record", "nope", "--source-url", "u", "--licence", "l",
                                      "--allowed", "dev", "--checked-by", "t"])
    with pytest.raises(SystemExit):
        DS.main()


def test_asvspoof_subset_script_on_a_mock_layout(tmp_path, capsys):
    """Mock of the ASVspoof 2019 LA folder layout (not the real data): protocol parsing, seeded sampling, labels."""
    sys.path.insert(0, str(ROOT / "scripts"))
    import make_asvspoof_subset as MS
    root = tmp_path / "LA"
    proto = root / "ASVspoof2019_LA_cm_protocols"
    audio = root / "ASVspoof2019_LA_dev" / "flac"
    proto.mkdir(parents=True)
    audio.mkdir(parents=True)
    (proto / "ASVspoof2019.LA.cm.dev.trl.txt").write_text(
        "\n".join([f"LA_0001 LA_D_{i} - - bonafide" for i in range(4)] + [f"LA_0002 LA_D_{9 + i} - A01 spoof" for i in range(4)]
                  + ["short line"]))
    with pytest.raises(SystemExit, match="no protocol file"):
        MS.main(["--root", str(root), "--split", "eval", "--out", str(tmp_path / "o")])
    # no audio files present: every pick is skipped, exit code 1, labels.csv still written (empty)
    assert MS.main(["--root", str(root), "--split", "dev", "--n-real", "2", "--n-fake", "2", "--out", str(tmp_path / "o")]) == 1
    assert "skipped 4" in capsys.readouterr().out
    if not HAS_FFMPEG:
        return
    sf = pytest.importorskip("soundfile")
    for i in list(range(4)) + [9 + i for i in range(4)]:
        sf.write(audio / f"LA_D_{i}.flac", _speechlike(0.5, i, 0.3), 16000)
    assert MS.main(["--root", str(root), "--split", "dev", "--n-real", "2", "--n-fake", "2", "--seed", "1",
                    "--codecs", "nosuch", "--out", str(tmp_path / "o2")]) == 0
    rows = list(csv.DictReader(open(tmp_path / "o2" / "labels.csv", encoding="utf-8")))
    assert sorted(r["label"] for r in rows) == ["fake", "fake", "real", "real"]
    assert "encoders not in this ffmpeg build" in capsys.readouterr().out
