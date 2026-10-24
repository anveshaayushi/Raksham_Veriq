"""Synthetic benchmark generator for VERIQ's chat side (FINALE, Claude C).

Every chat, name and identifier is fictional. Ground truth is set by construction (what the generator put in), not by
running VERIQ. Two splits use DIFFERENT phrasings, firm names, mule names and distractors:
    dev  : used while building and fixing the engine
    test : run once for the reported numbers; never used for tuning
Limitations: written by us, English only, WhatsApp-style text; it tests consistency and robustness to formatting,
not real-world accuracy.

Usage: python -m bench.generate   (writes bench/data/dev.json and bench/data/test.json)
"""

from __future__ import annotations

import json
import random
from pathlib import Path

OUT = Path(__file__).resolve().parent / "data"

POOLS = {
    "dev": {
        "firms": ["Navyug Broking Pvt Ltd", "Sahyadri Securities Ltd", "Kaveri Capital Advisors LLP",
                  "Pratham Wealth Research Pvt Ltd", "Indravati Stockline Ltd", "Meghdoot Investments Pvt Ltd"],
        "mule_business": ["SHREE GANESH TRADERS", "OM SAI ENTERPRISES", "MAA DURGA STORES", "JAI AMBE AGENCIES",
                          "BALAJI GARMENTS", "RK MOBILE POINT", "NEW STAR ELECTRICALS", "SAI KRUPA TRADING CO"],
        "mule_person": ["RAMESH KUMAR", "SUNITA DEVI", "MOHD ASLAM", "PRAKASH YADAV"],
        "gateways": ["Razorpay Software Pvt Ltd", "Cashfree Payments India"],
        "agent": ["Rahul", "Neha", "Vikram", "Pooja"],
        "intro": ["Hello {victim}, I am {agent} from {firm}.", "Namaste {victim} ji, this is {agent} at {firm}."],
        "pay": ["Pay {amt} to UPI {payee} today.", "Send {amt} to {payee} for activation."],
        "acct": ["Transfer {amt} to A/c {acct} IFSC {ifsc}.", "Deposit {amt} in account no. {acct}, IFSC {ifsc}."],
        "fee": ["Pay 18% tax to withdraw your profit.", "Clearance charges must be paid before withdrawal."],
        "rotate": ["Our payment department has a new ID: {payee}.", "Use this new UPI now: {payee}"],
        "distract": ["Mail us at support.{slug}@gmail.com", "Call 98{n8} for help.", "Your order no 4421{n8} is confirmed.",
                     "Visit www.{slug}-markets.in"],
    },
    "test": {
        "firms": ["Godavari Broking Ltd", "Tapti Wealth Managers Pvt Ltd", "Nilgiri Share Services Ltd",
                  "Chambal Equity Research LLP", "Vindhya Securities Pvt Ltd", "Sabarmati Capital Ltd"],
        "mule_business": ["LAXMI HARDWARE", "GURU KRIPA TRAVELS", "MAHALAXMI FOOTWEAR", "ANNAPURNA SWEETS",
                          "VIGHNAHARTA AUTO PARTS", "KRISHNA DAIRY FARM", "SHIV SHAKTI TENT HOUSE", "ROYAL TAILORS"],
        "mule_person": ["DEEPAK SHARMA", "ANITA KUMARI", "SALIM KHAN", "VIJAY PATIL"],
        "gateways": ["PayU Payments Pvt Ltd", "BillDesk Merchant"],
        "agent": ["Arjun", "Kavya", "Sameer", "Ritu"],
        "intro": ["Good morning {victim}. {agent} here, senior analyst with {firm}.",
                  "Hi {victim}, {agent} from {firm} customer desk."],
        "pay": ["Kindly remit {amt} via UPI to {payee} before 6 pm.", "Complete payment of {amt}: {payee}"],
        "acct": ["Bank transfer {amt}, account number {acct}, IFSC {ifsc}, name as shown.",
                 "NEFT {amt} to a/c {acct} ({ifsc})."],
        "fee": ["To release funds, a withdrawal fee of 12% applies.", "Withdrawal is blocked until GST charges are paid."],
        "rotate": ["Earlier ID is closed. Pay on {payee} only.", "Treasury changed the UPI, new one is {payee}"],
        "distract": ["Write to helpdesk@{slug}.co.in", "WhatsApp +91 97{n8} for queries.", "Ticket ref 55{n8}00 noted.",
                     "Read terms at https://{slug}.example.in/t"],
    },
}
BANKS = ["SBIN", "HDFC", "ICIC", "UTIB", "PUNB", "BARB", "KKBK", "IDIB"]
VPA_HOSTS = ["upi", "ybl", "okaxis", "oksbi", "paytm", "ibl", "axl"]


def legit_variants(firm: str, rng: random.Random) -> str:
    words = firm.replace("Pvt Ltd", "Private Limited").replace("Ltd", "Limited").upper().split()
    choice = rng.randrange(4)
    if choice == 0:
        return " ".join(words)
    if choice == 1:
        return firm.upper()
    if choice == 2:
        return " ".join(words[:2]) + " LTD"
    return "M/S " + " ".join(words[:2]) + " PVT LTD"


def ts(rng: random.Random, day: int, fmt: str) -> str:
    h, m = rng.randrange(8, 22), rng.randrange(60)
    if fmt == "android12":
        return f"{day:02d}/10/2026, {h % 12 or 12}:{m:02d} {'pm' if h >= 12 else 'am'} - "
    if fmt == "android24":
        return f"{day:02d}/10/2026, {h:02d}:{m:02d} - "
    return f"[{day:02d}/10/26, {h % 12 or 12}:{m:02d}:{rng.randrange(60):02d} {'PM' if h >= 12 else 'AM'}] "


def line(fmt: str, stamp: str, who: str, text: str) -> str:
    return f"{stamp}{who}: {text}"


def make_case(split: str, idx: int, kind: str, rng: random.Random) -> dict:
    P = POOLS[split]
    firm = rng.choice(P["firms"])
    agent, victim = rng.choice(P["agent"]), rng.choice(["Meera", "Ankit", "Priya", "Suresh", "Fatima", "John"])
    fmt = rng.choice(["android12", "android24", "ios"])
    slug = firm.split()[0].lower()
    msgs, payees, voice_tr = [], [], {}
    day = 5

    def say(who, text):
        nonlocal day
        msgs.append(line(fmt, ts(rng, day, fmt), who, text))
        day += rng.choice([0, 1])

    def new_vpa():
        return f"{rng.choice(['pay', 'acct', 'fund', 'desk', 'kyc', 'svc'])}{rng.randrange(10, 999)}.{rng.choice('abcdefghjk')}@{rng.choice(VPA_HOSTS)}"

    def new_acct():
        return str(rng.randrange(10 ** 10, 10 ** 14)), f"{rng.choice(BANKS)}0{rng.randrange(100000, 999999)}"

    say(agent, P["intro"][rng.randrange(2)].format(victim=victim, agent=agent, firm=firm))
    if rng.random() < 0.6:
        say(agent, rng.choice(P["distract"]).format(slug=slug, n8=rng.randrange(10 ** 7, 10 ** 8)))
    say(victim, rng.choice(["ok", "How do I pay?", "Please share details", "Okay sir"]))

    n_payees = {"scam_rotation": rng.choice([2, 3]), "scam_person": 1, "legit_match": 1, "legit_gateway": 1,
                "no_check": rng.choice([1, 2]), "scam_single": 1}[kind]
    for k in range(n_payees):
        amt = f"₹{rng.choice([5, 10, 15, 25, 40, 60])},000"
        as_voice = kind == "scam_rotation" and k == 1 and rng.random() < 0.5
        use_acct = rng.random() < 0.3 and not as_voice
        if use_acct:
            acct, ifsc = new_acct()
            text, pid_val, ptype = rng.choice(P["acct"]).format(amt=amt, acct=acct, ifsc=ifsc), acct, "bank_account"
        else:
            vpa = new_vpa()
            tmpl = rng.choice(P["rotate"]) if k > 0 else rng.choice(P["pay"])
            text, pid_val, ptype = tmpl.format(amt=amt, payee=vpa), vpa, "upi_vpa"
        if as_voice:
            ref = f"PTT-202610{day:02d}-WA00{rng.randrange(10, 99)}.opus"
            voice_tr[ref] = text
            say(agent, f"{ref} (file attached)")
        else:
            say(agent, text)
        payees.append({"value_norm": pid_val, "type": ptype, "from_voice": as_voice})
        if kind.startswith("scam") and k == n_payees - 1 and rng.random() < 0.7:
            say(agent, rng.choice(P["fee"]))
        if rng.random() < 0.4:
            say(victim, rng.choice(["done", "sent", "ok wait", "paying now"]))

    checks, expected = {}, []
    for k, p in enumerate(payees):
        if kind in ("scam_rotation", "scam_single"):
            checks[p["value_norm"]] = rng.choice(P["mule_business"])
            expected.append("NAME_DISCREPANCY")
        elif kind == "scam_person":
            checks[p["value_norm"]] = rng.choice(P["mule_person"])
            expected.append("INCONCLUSIVE")  # by design: a personal name is never an accusation
        elif kind == "legit_match":
            checks[p["value_norm"]] = legit_variants(firm, rng)
            expected.append("NO_MAJOR_ISSUE")
        elif kind == "legit_gateway":
            checks[p["value_norm"]] = rng.choice(P["gateways"])
            expected.append("INCONCLUSIVE")
        else:
            expected.append("INCONCLUSIVE")  # no name check run
    if kind.startswith("scam") and any("fee" in m.lower() or "withdraw" in m.lower() for m in msgs):
        pass  # hard cue present; NAME_DISCREPANCY still outranks it
    chat = "\n".join(msgs) + "\n"
    return {"case_id": f"{split}-{idx:03d}", "kind": kind, "is_scam": kind.startswith("scam"), "claimed_firm": firm,
            "chat_txt": chat, "transcripts": voice_tr, "payees": payees, "checks": checks,
            "expected": expected, "format": fmt}


def generate(split: str, n: int, seed: int) -> list[dict]:
    rng = random.Random(seed)
    kinds = ["scam_rotation", "scam_single", "scam_person", "legit_match", "legit_gateway", "no_check"]
    return [make_case(split, i, kinds[i % len(kinds)], rng) for i in range(n)]


def main() -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    for split, n, seed in (("dev", 120, 101), ("test", 300, 20261024)):
        (OUT / f"{split}.json").write_text(json.dumps(generate(split, n, seed), ensure_ascii=False, indent=1),
                                           encoding="utf-8")
        print(f"wrote {split}: {n} chats")


if __name__ == "__main__":
    main()
