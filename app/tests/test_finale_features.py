"""FINALE features: QR codes in images, look-alike payee names, obfuscated pressure phrases, the high-pressure
variant for unassessable audio, mistake recovery (review / overturn), the 1930 incident card, image intake."""
import json
from datetime import date

import pytest

cv2 = pytest.importorskip("cv2")

from app.case import UserCheck, build_case, demo_inputs, load_demo, report_data  # noqa: E402
from app.intake import Intake, IntakeError, add_image  # noqa: E402
from app.overturn import Ledger, is_valid_handle, payee_hash  # noqa: E402
from extract import CUE_RX, deobfuscate  # noqa: E402
from parsing.qr import decode_qr, parse_upi  # noqa: E402
from report.build import incident_json  # noqa: E402

FIRM = "Navyug Wealth Research Pvt Ltd"


def qr_png(text: str) -> bytes:
    img = cv2.QRCodeEncoder.create().encode(text)
    img = cv2.resize(img, (300, 300), interpolation=cv2.INTER_NEAREST)
    img = cv2.copyMakeBorder(img, 30, 30, 30, 30, cv2.BORDER_CONSTANT, value=255)
    return cv2.imencode(".png", img)[1].tobytes()


CHAT = ("13/10/2026, 6:02 pm - Rahul: I am Rahul from Navyug Wealth. Pay the onboarding fee to ramesh.k@upi\n"
        "14/10/2026, 10:11 am - Rahul: IMG-20261014-WA0001.jpg (file attached)\n"
        "14/10/2026, 10:12 am - Rahul: Scan the QR, today only\n")
QR = "upi://pay?pa=sunita.t@upi&pn=SUNITA%20TRADERS&am=25000"


# ---------------------------------------------------------------- QR ----
def test_parse_upi_fields_and_rejects():
    u = parse_upi("upi://pay?pa=Sunita.T@UPI&pn=SUNITA%20TRADERS&am=25000.00&tn=fee")
    assert (u["pa"], u["pn"], u["am"], u["tn"]) == ("sunita.t@upi", "SUNITA TRADERS", 25000, "fee")
    assert parse_upi("https://example.in/pay") is None and parse_upi("upi://pay?pn=NO%20ADDRESS") is None
    assert parse_upi("upi://pay?pa=not-a-vpa&pn=X") is None


def test_decode_qr_from_image_and_garbage():
    assert decode_qr(qr_png(QR)) == [QR]
    assert decode_qr(b"not an image") == []


def test_qr_payee_is_extracted_as_image_source_and_compared():
    checks = {"ramesh.k@upi": UserCheck("SHREE GANESH TRADERS", "UPI app (payee name before paying)", date(2026, 10, 24))}
    c = build_case(case_id="q1", chat_text=CHAT, claimed_firm=FIRM, checks=checks,
                   images={"IMG-20261014-WA0001.jpg": qr_png(QR)})
    pays = {p.value_norm: p for p in c.payees}
    assert pays["sunita.t@upi"].source == "image" and pays["sunita.t@upi"].msg_id == 2
    d = c.result_for(pays["sunita.t@upi"].id)
    assert d.result == "HUMAN_REVIEW" and any("QR code" in r for r in d.reasons)  # class D: caution, not accusation
    qr_ev = [e for e in c.evidence if e.lane == "payee_name" and e.class_ == "D"]
    assert len(qr_ev) == 1 and qr_ev[0].observed == "SUNITA TRADERS"
    assert c.amounts[pays["sunita.t@upi"].id].startswith("₹25,000")
    assert any(x.type == "payee_change" and "QR code" in x.excerpt for x in c.extraction.cues)


def test_uploaded_image_not_named_in_chat_and_image_without_qr():
    c = build_case(case_id="q2", chat_text=CHAT, claimed_firm=FIRM, checks={},
                   images={"extra.png": qr_png("upi://pay?pa=om.sai@ybl&pn=OM%20SAI"), "blank.png": qr_png("hello")})
    assert "om.sai@ybl" in [p.value_norm for p in c.payees]
    assert any("not a UPI payment code" in w for w in c.extraction.warnings)


def test_demo_qr_file_is_synthetic_and_readable():
    from pathlib import Path
    data = (Path(__file__).resolve().parents[1] / "demo_media" / "demo_qr_synthetic.png").read_bytes()
    (u,) = [parse_upi(p) for p in decode_qr(data)]
    assert u["pa"] == "omsai.ent@ybl" and u["pn"] == "OM SAI ENTERPRISES"


# ---------------------------------------------------------------- names and cues ----
@pytest.mark.parametrize("typed,result", [("NAVYUG ONLINE TRADERS", "HUMAN_REVIEW"), ("Navyug Broking Services", "HUMAN_REVIEW"),
                                          ("NAVYUG BROKING PRIVATE LIMITED", "NO_MAJOR_ISSUE")],
                         ids=["online_traders", "broking_services", "genuine_variant"])
def test_lookalike_shell_names_go_to_review(typed, result):
    fx = load_demo("B")  # registration consistent, no hard cues: only the typed name changes
    di = demo_inputs(fx)
    checks = {k: UserCheck(typed, v["source"], v["date"]) for k, v in di["checks"].items()}
    c = build_case(case_id=di["case_id"], chat_text=di["chat_text"], claimed_firm=di["claimed_firm"], checks=checks,
                   transcripts=di["transcripts"], fixture=fx)
    assert c.result_for(c.payees[0].id).result == result


@pytest.mark.parametrize("text,cue", [("gu@r@nteed 3x returns", "guaranteed_return"), ("u_r_g_e_n_t", "urgency"),
                                      ("P.a.y 18% t@x to withdraw", "fee_to_withdraw"), ("no loss pakka double", "guaranteed_return"),
                                      ("pay unfreeze account fee", "fee_to_withdraw"), ("send in 5 mins", "urgency")],
                         ids=["leet", "spaced", "dotted_leet_fee", "hinglish", "unfreeze", "minutes"])
def test_obfuscated_pressure_phrases(text, cue):
    assert any(t == cue and (rx.search(text) or rx.search(deobfuscate(text))) for t, rx in CUE_RX)


def test_onboarding_fee_is_not_a_withdrawal_fee():
    assert not any(t == "fee_to_withdraw" and (rx.search(s) or rx.search(deobfuscate(s)))
                   for t, rx in CUE_RX for s in ["Onboarding fee ₹10,000"])


def test_high_pressure_variant_for_unassessable_audio():
    fx = load_demo("C")
    di = demo_inputs(fx)
    c = build_case(case_id=di["case_id"], chat_text=di["chat_text"], claimed_firm=di["claimed_firm"], checks={},
                   transcripts=di["transcripts"], fixture=fx)
    d = c.decisions[0]
    assert d.result == "INCONCLUSIVE" and d.reasons[0].startswith("HIGH PRESSURE:") and "1930" in d.next_step


# ---------------------------------------------------------------- mistake recovery ----
def test_review_request_overturn_and_audit_has_no_raw_identifier(tmp_path):
    from registry.sqlite_registry import BURST_WINDOW_S, SQLiteRegistry, create_db, new_reporter_token

    db = tmp_path / "r.db"
    create_db(db)
    t = [1_800_000_000.0]
    reg = SQLiteRegistry(db, secret=b"test-secret-0123456789", clock=lambda: t[0])
    for _ in range(2):
        reg.report("upi_vpa", "navyug.brk@validhdfc", new_reporter_token())
        t[0] += BURST_WINDOW_S + 1
    assert reg.lookup("p", "upi_vpa", "navyug.brk@validhdfc").status == "linked"

    led = Ledger()
    with pytest.raises(ValueError):
        led.request("p1", "x@upi", "NO_MAJOR_ISSUE", "Other (explain)", "", "")  # nothing to overturn
    led.request("p1", "navyug.brk@validhdfc", "LINKED", "The firm uses a different legal or trading name", "our broker",
                "navyug.brk@validhdfc")
    with pytest.raises(ValueError):
        led.decide("p1", "overturned", "", "")  # reviewer name and reason required
    r = led.decide("p1", "overturned", "Reviewer A", "SEBI Check shows the @valid handle", registry=reg)
    assert r.status == "overturned" and "decided in" in r.elapsed()
    assert reg.lookup("p", "upi_vpa", "navyug.brk@validhdfc").status == "clean"  # reviewer rejection stops linking
    audit = led.audit_json()
    assert "navyug.brk@validhdfc" not in audit.split('"reference"')[0] and payee_hash("navyug.brk@validhdfc") in audit
    assert [a["action"] for a in json.loads(audit)["audit_trail"]] == ["review requested", "overturned"]
    assert is_valid_handle("navyug.brk@validhdfc") and not is_valid_handle("ramesh.k@upi")


# ---------------------------------------------------------------- incident card ----
def test_incident_card_json():
    fx = load_demo("A")
    di = demo_inputs(fx)
    checks = {k: UserCheck(v["name"], v["source"], v["date"]) for k, v in di["checks"].items()}
    c = build_case(case_id=di["case_id"], chat_text=di["chat_text"], claimed_firm=di["claimed_firm"], checks=checks,
                   transcripts=di["transcripts"], fixture=fx, files=[{"name": "chat.txt", "kind": "chat", "sha256": "ab" * 32}])
    card = json.loads(incident_json(report_data(c, money_sent=True, reviews={c.payees[0].id: "review requested"})))
    assert "not an official NCRP format" in card["format"] and card["money_already_sent"] is True
    assert card["complainant"]["mobile"] is None and card["payees"][0]["transaction"]["utr"] is None  # never invented
    assert [p["identifier"] for p in card["payees"]] == ["ramesh.k@upi", "sunita.t@upi", "30112233445021"]
    assert card["payees"][1]["found_in"] == "voice" and card["payees"][0]["mistake_review"] == "review requested"
    assert card["evidence_chain"]["files"][0]["sha256"] == "ab" * 32
    assert all("0.12" not in json.dumps(v) for v in card["voice_audit"])  # stub voice numbers never exported


# ---------------------------------------------------------------- image intake ----
def test_image_intake_checks():
    it = Intake()
    add_image(it, "qr.png", qr_png(QR))
    assert it.images[0].kind == "image" and len(it.images[0].sha256) == 64
    for name, data, msg in [("x.gif", b"GIF89a", "supported image"), ("x.png", b"", "empty"),
                            ("x.png", b"not really a png", "does not look like")]:
        with pytest.raises(IntakeError, match=msg):
            add_image(Intake(), name, data)
