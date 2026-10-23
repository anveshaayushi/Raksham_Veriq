from app.adapters.extract import amount_in, parse_stub, payees, run

ANDROID = ("20/10/2026, 8:59 pm - Rahul: I am Rahul from Navyug Wealth. Reg INH000DEMO45\n"
           "20/10/2026, 9:01 pm - Rahul: Pay ₹10,000 to ramesh.k@upi\n"
           "second line of the same message\n"
           "21/10/2026, 10:00 am - Rahul: PTT-1.opus (file attached)\n"
           "22/10/2026, 4:20 pm - Rahul: Pay tax to withdraw. ₹60,000 to A/c 50210012345021 IFSC SBIN0001234 today only\n")
IOS = "[20/10/26, 8:59:12 PM] Rahul: Pay to x.y@ybl\n[20/10/26, 9:00:00 PM] Rahul: ‎<attached: 00000012-AUDIO.opus>\n"


def test_android_and_multiline():
    msgs, warn = parse_stub(ANDROID)
    assert [m.msg_id for m in msgs] == [1, 2, 3, 4] and msgs[0].ts == "2026-10-20T20:59" and not warn
    assert "second line" in msgs[1].text and msgs[2].kind == "voice" and msgs[2].media_ref == "PTT-1.opus"


def test_iphone():
    msgs, _ = parse_stub(IOS)
    assert msgs[0].ts == "2026-10-20T20:59" and msgs[1].kind == "voice" and msgs[1].media_ref == "00000012-AUDIO.opus"


def test_payees_separate_and_cues():
    ex = run(ANDROID, "c1", {"PTT-1.opus": "new ID sunita.t@upi"})
    ps = payees(ex.indicators)
    assert [p.value_norm for p in ps] == ["ramesh.k@upi", "sunita.t@upi", "50210012345021"]
    assert ps[1].source == "voice" and ps[1].confidence == "medium" and ps[0].id == "c1-I2" and isinstance(ps[0].span, list) and len(ps[0].span) == 2
    types = {(c.type, c.severity) for c in ex.cues}
    assert ("fee_to_withdraw", "hard") in types and ("payee_change", "soft") in types and ("urgency", "soft") in types
    assert ex.is_stub and "STUB" in ex.source


def test_no_messages_warns():
    msgs, warn = parse_stub("hello there")
    assert msgs == [] and warn


def test_amount_display():
    assert amount_in("Pay ₹10,000 now") == "₹10,000" and amount_in("no money") is None


def test_plain_export_without_times_is_refused_honestly_under_the_shared_contract():
    ex = run("Rahul: Pay ₹500 to a.b@upi\nstill Rahul\nMeera: ok", "c2")
    assert ex.messages == [] and len(ex.warnings) == 1 and "CR-C6" in ex.warnings[0]  # no invented timestamps


def test_month_first_file_is_detected():
    msgs, warn = parse_stub("10/25/26, 9:00 am - A: hi\n10/02/26, 9:05 am - A: again")
    assert msgs[0].ts == "2026-10-25T09:00" and msgs[1].ts == "2026-10-02T09:05" and "month-first" in warn[0]


def test_ambiguous_dates_read_day_first_with_warning():
    msgs, warn = parse_stub("01/02/26, 9:00 am - A: hi")
    assert msgs[0].ts == "2026-02-01T09:00" and "day-first" in warn[0]
