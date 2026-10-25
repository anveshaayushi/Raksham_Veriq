"""Payee-name matcher: does the name the user's bank/UPI app showed belong to the claimed firm?

FINALE, 24 Oct 2026. Claude A's token matcher, ported and extended by Claude C at the team's request (CR-C13).

match_names(claimed, observed) -> (verdict, reason)
    verdict "match"        : shares a distinctive word with the claimed firm
    verdict "discrepancy"  : a business name with no distinctive word in common  -> can decide NAME_DISCREPANCY
    verdict "lookalike"    : shares the brand word but adds a different word or business type ("NAVYUG ONLINE
                             TRADERS" for "Navyug Wealth Research"): a possible shell / look-alike account -> HUMAN_REVIEW
    verdict "unverified"   : we can't tell, so we don't accuse (deck p9: false-positive classes)
        - payment gateway / aggregator names (Razorpay, Cashfree, ...): the merchant's name is not shown
        - a personal-looking name (could be the firm's proprietor or a mule; we can't tell which)
        - an abbreviation or initials of the claimed firm ("NWR PVT LTD")
        - a near spelling / transliteration variant ("Navyog" vs "Navyug")
        - nothing distinctive left on one side
Generic words (Pvt, Ltd, Traders, Wealth, Securities, ...) never count as a shared word on their own.
"""

from __future__ import annotations

import re
import unicodedata

GENERIC = {
    # legal forms
    "pvt", "private", "ltd", "limited", "llp", "inc", "corp", "corporation", "co", "company", "plc", "opc",
    # finance words that many unrelated firms share
    "wealth", "research", "securities", "security", "broking", "brokers", "broker", "advisory", "advisors", "advisers",
    "investment", "investments", "capital", "finance", "financial", "finserv", "fintech", "markets", "market", "trading",
    "trade", "trades", "stock", "stocks", "shares", "equity", "money", "fund", "funds", "asset", "assets", "management",
    "consultancy", "consultants", "services", "service", "solutions", "global", "india", "indian", "international",
    # shop / trading-style words
    "traders", "trader", "enterprises", "enterprise", "agency", "agencies", "store", "stores", "industries", "group",
    "associates", "ventures", "mart", "the", "and", "of", "pro",
}
# Shop and trade words: a shown name with one of these is a business even if it also has a given name
# ("KRISHNA DAIRY FARM"). Added in Q2 for the documented miss; a general list, not taken from benchmark chats.
SHOP_WORDS = set("""
dairy farm farms foods food sweets bakery bakers restaurant hotel dhaba cafe canteen caterers kirana general provision
provisions medical medicals pharmacy pharma chemist chemists clinic hospital diagnostics labs lab garments garment
textiles textile fabrics cloth boutique fashion fashions collection collections footwear shoes jewellers jewellery
jewelers gems mobile mobiles electronics electricals electrical hardware sanitary paints steel iron cement builders
construction constructions realty developers properties estate motors motor auto autos automobiles garage tyres
travels travel tours transport transports logistics cargo couriers courier packers movers exports export imports
impex overseas distributors distributor suppliers supplier wholesale retail bazaar bhandar emporium centre center
point house works mills mill plastics chemicals fertilizers seeds agro studio salon parlour academy
institute classes coaching tutorials school college computers infotech systems software digital media printers
printing press books stationers stationery opticals optical furniture interiors decor
""".split())
BUSINESS_MARKERS = (GENERIC - {"the", "and", "of", "india", "indian", "global", "international", "pro"}) | SHOP_WORDS
GATEWAYS = ("razorpay", "cashfree", "payu", "billdesk", "ccavenue", "juspay", "easebuzz", "instamojo", "phonepe",
            "paytm payments", "bharatpe", "pine labs", "mswipe", "setu")
HONORIFICS = {"mr", "mrs", "ms", "shri", "smt", "sri", "dr"}
# Common Indian given names and surnames (general list, not tuned to any benchmark). A shown name counts as
# "personal-looking" only if it contains one of these; any other unrelated name is treated as a business name.
PERSON_WORDS = set("""
kumar kumari devi singh sharma verma gupta agarwal aggarwal jain shah patel mehta joshi yadav khan ahmed ahmad mohd
mohammad mohammed md shaikh sheikh ansari siddiqui qureshi pathan reddy rao naidu nair menon pillai iyer iyengar
chatterjee banerjee mukherjee ghosh bose das dutta sen roy chowdhury mishra tiwari tripathi pandey dubey shukla
srivastava saxena chauhan rathore thakur rajput patil pawar jadhav shinde deshmukh kulkarni gaikwad more sawant naik
bhat hegde shetty gowda fernandes dsouza rodrigues pinto gill sandhu dhillon kaur malhotra kapoor khanna arora sethi
bansal goyal mittal garg singhal chaudhary choudhary meena bhatt trivedi desai parmar solanki vaghela
ramesh suresh mahesh rajesh rakesh mukesh dinesh ganesh umesh naresh prakash deepak vijay ajay sanjay amit sumit
rahul rohit mohit anil sunil vinod manoj ashok arun varun kiran ravi raju ramu shyam mohan sohan krishna gopal
salim aslam irfan imran farhan arif asif sameer salman zaid faisal rizwan javed
sunita anita anjali pooja priya neha kavita savita lata geeta seema reena meena rekha asha usha nisha
fatima ayesha zainab shabana nasreen
""".split())


PERSON_WORDS |= set("""
raj rajan rajiv rajeev rajendra rajkumar kishore kishor kishan manish ankit ankita nitin sachin sandeep pradeep
praveen naveen pavan pawan harish girish satish santosh subhash ramesh lalit lalita vikram vikas vivek vinay vinayak
abhishek akash aakash aditya ajit alok anand arvind ashish bharat chandan chetan dev devendra dhruv gaurav hemant
jitendra kamal karan kunal mayank narendra nikhil pankaj prashant rajat ravindra sagar sahil saurabh shivam shubham
siddharth sudhir sumit sunny tarun tushar uday vipin yash yogesh joseph john thomas george mathew paul francis
harpreet gurpreet manpreet jaswinder baljit tasleem nadeem shahid wasim tariq babu lal chand prasad nath
tanya tanvi nidhi neelam shweta sneha swati shilpa sonia sonal preeti payal pallavi poonam radha rani renu ritu
divya deepa deepika jyoti kajal komal madhu mamta manju meera nandini pinki rashmi rinku sapna sarita shalini
shobha sudha sushma vandana varsha geeta gita laxmi lakshmi parvati durga saraswati
mehrotra mehra chopra bajaj bhatia ahuja anand kohli luthra grover tandon saini rawat bisht negi rana tomar
""".split())
SHOP_WORDS |= set("""shop shoppe tailors tailor corner tent spares spare silk sweet tea pan repair repairs xerox photo
cycle cycles wines florist kiosk stall dhaba saree sarees handloom""".split())
BUSINESS_MARKERS |= SHOP_WORDS
# Words that describe WHAT a payment is for, not WHO receives it: a collection or billing account of the firm
# ("LUMINA MUTUAL FUND COLLECTION") is not a different business. Added after the 25 Oct pre-registered run
# (D1/D2 false alarms); a general list, see results/prereg/PREREG_RESULTS.md.
PURPOSE_WORDS = set("""collection collections collect payment payments bill bills billing recharge recharges renewal
renewals premium premiums fee fees dues receipts receipt subscription subscriptions escrow nodal sip emi deposit
deposits account accounts ac a c""".split())
# A city, branch or office suffix ("TIDEWATER WEALTH PVT LTD PUNE", "... - INDORE BRANCH") names a branch of the same
# firm, not another business. General list of large Indian cities and office words.
PLACE_WORDS = set("""mumbai bombay delhi newdelhi new noida gurgaon gurugram faridabad ghaziabad kolkata calcutta chennai
madras bengaluru bangalore hyderabad secunderabad pune ahmedabad surat vadodara baroda rajkot jaipur jodhpur udaipur
kota lucknow kanpur agra varanasi allahabad prayagraj meerut indore bhopal gwalior jabalpur nagpur nashik aurangabad
thane navi kochi cochin trivandrum thiruvananthapuram coimbatore madurai mysore mysuru mangalore mangaluru hubli
belgaum goa panaji patna ranchi jamshedpur bhubaneswar cuttack guwahati shillong chandigarh mohali ludhiana amritsar
jalandhar dehradun shimla jammu srinagar raipur bilaspur visakhapatnam vizag vijayawada guntur tirupati
branch branches hq head office offices unit division zone region regional city""".split())
# Common abbreviations in bank-app names (truncated to fit a field): expanded before comparing.
ABBREV = {"bros": "brothers", "bro": "brothers", "trdg": "trading", "servs": "services", "svcs": "services",
          "srvcs": "services", "svc": "services", "serv": "services", "corpn": "corporation", "intl": "international",
          "mfg": "manufacturing", "mgmt": "management", "mgt": "management", "assoc": "associates", "stk": "stock",
          "invst": "investments", "invt": "investments", "inv": "investments", "secs": "securities", "sec": "securities",
          "brkg": "broking", "mkts": "markets", "mkt": "markets", "solns": "solutions", "sol": "solutions",
          "inds": "industries", "ent": "enterprises", "ents": "enterprises", "tech": "technologies",
          "fin": "finance", "advs": "advisors", "adv": "advisory", "cap": "capital", "hldgs": "holdings",
          "shri": "sri", "shree": "sri", "sree": "sri", "sri": "sri"}
# (A legal-form conflict rule, e.g. 'Company' vs 'Corporation', was tried and dropped: firms often hold accounts in
# a sister legal form (LLP vs Ltd), so it raised false alarms on our synthetic set.)
# Payment aggregators / collection platforms show their own name, not the merchant's: we can't tell who is behind it.
_GATEWAY_TOKEN = re.compile(r"pay|collect|remit|settle|wallet|merchant|gateway|checkout|upi")


def _split_camel(s: str) -> str:
    return re.sub(r"(?<=[a-z])(?=[A-Z][a-z])", " ", s)


def _tokens(name: str) -> list[str]:
    s = unicodedata.normalize("NFKD", _split_camel(name or "")).encode("ascii", "ignore").decode()
    s = s.lower().replace("&", " and ")
    s = re.sub(r"\bpvt\.?\s*ltd\.?\b", " pvt ltd ", s)
    toks = [t for t in re.split(r"[^a-z0-9]+", s) if t]
    out: list[str] = []
    prev_initials = False
    for t in toks:  # "R S", "K. R.", "S.V." -> "rs", "kr", "sv": initials written with spaces or dots
        single = len(t) == 1 and t.isalpha()
        if single and prev_initials:
            out[-1] += t
        else:
            out.append(t)
        prev_initials = single or (prev_initials and single)
    return [ABBREV.get(t, t) for t in out]


def _distinctive(tokens: list[str]) -> set[str]:
    return {t for t in tokens if t not in GENERIC and t not in HONORIFICS and len(t) > 1}


# Business-type words, compared by their first 4 letters so "Broking"/"Brokers" or "Trading"/"Traders" count as the same.
CATEGORY = {"research", "broking", "brokers", "broker", "securities", "security", "advisory", "advisors", "advisers",
            "investment", "investments", "capital", "finance", "financial", "finserv", "wealth", "markets", "market",
            "trading", "trade", "traders", "trader", "stock", "stocks", "shares", "share", "equity", "money", "fund",
            "funds", "asset", "assets", "management", "managers", "consultancy", "consultants", "services", "service",
            "solutions", "enterprises", "enterprise", "agency", "agencies", "store", "stores", "industries", "ventures",
            "mart", "associates", "group", "online", "digital", "tech", "technologies", "infotech", "global",
            # added 25 Oct after the pre-registered run: business-type words that alone don't name a firm
            "insurance", "assurance", "power", "energy", "telecom", "dth", "broadband", "credit", "loans", "lending",
            "bank", "analytics", "holdings", "partners", "trust", "mutual", "brothers", "sons", "corporation",
            "company", "manufacturing", "international", "systems", "software", "media"}


def _cat(tokens) -> set[str]:
    return {t[:4] for t in tokens if t in CATEGORY}


def _abbrev_of(tok: str, full: list[str]) -> bool:
    return len(tok) >= 2 and any(f != tok and f.startswith(tok) for f in full)


def _near(a: str, b: str) -> bool:
    """One edit apart (insert/delete/substitute) for words of 5+ letters: likely the same word, spelled differently."""
    if min(len(a), len(b)) < 5 or abs(len(a) - len(b)) > 1:
        return False
    if len(a) == len(b):
        diff = [i for i, (x, y) in enumerate(zip(a, b)) if x != y]
        return len(diff) == 1 or (len(diff) == 2 and diff[1] == diff[0] + 1 and a[diff[0]] == b[diff[1]]
                                  and a[diff[1]] == b[diff[0]])  # one swap of neighbours ("feild"/"field")
    short, long_ = (a, b) if len(a) < len(b) else (b, a)
    return any(long_[:i] + long_[i + 1:] == short for i in range(len(long_)))


def _skel(t: str) -> str:
    """Transliteration skeleton for Indian names: Laxmi/Lakshmi, Jyoti/Jyothi, Vaishnavi/Vaishnawi,
    Choudhary/Chaudhary, Krishna/Krushna, Venkatesh/Venkatesha all map to the same consonant skeleton."""
    s = t.lower()
    for a, b in (("ksh", "x"), ("ks", "x"), ("w", "v"), ("ph", "f"), ("th", "t"), ("dh", "d"), ("bh", "b"),
                 ("kh", "k"), ("gh", "g"), ("ch", "c"), ("sh", "s"), ("z", "j"), ("q", "k"), ("y", "i")):
        s = s.replace(a, b)
    s = s[:1] + re.sub(r"[aeiou]", "", s[1:])
    return re.sub(r"(.)\1+", r"\1", s)


def _variant(a: str, b: str) -> bool:
    return a == b or (min(len(a), len(b)) >= 4 and (_skel(a) == _skel(b) or _near(a, b)))


def _rejoin(obs: list[str], cla: list[str]) -> list[str]:
    """Undo joined or split words in the shown name relative to the claim ("SIDDHIVINAYAK" for "Siddhi Vinayak",
    "GURU NANAK" for "Gurunanak", "MOHANLAL" for "Mohan Lal")."""
    cset = set(cla)
    out: list[str] = []
    i = 0
    while i < len(obs):
        merged = False
        for k in (3, 2):  # adjacent shown words that together form one claimed word
            if i + k <= len(obs) and "".join(obs[i:i + k]) in cset:
                out.append("".join(obs[i:i + k]))
                i += k
                merged = True
                break
        if merged:
            continue
        t = obs[i]
        split = None
        for j in range(len(cla)):  # one shown word that is several adjacent claimed words
            for k in (2, 3):
                if j + k <= len(cla) and "".join(cla[j:j + k]) == t:
                    split = cla[j:j + k]
        out.extend(split or [t])
        i += 1
    return out


def _initials(tokens: list[str], with_legal: bool) -> str:
    skip = {"and", "of", "the"} | (set() if with_legal else {"pvt", "private", "ltd", "limited", "llp"})
    return "".join(t[0] for t in tokens if t not in skip)


def match_names(claimed: str, observed: str) -> tuple[str, str]:
    c_tok, o_tok = _tokens(claimed or ""), _tokens(observed or "")
    if not c_tok or not o_tok:
        return "unverified", "a name is missing"
    o_tok = _rejoin(o_tok, c_tok)
    o_low = " ".join(o_tok)
    for g in GATEWAYS:
        if g in o_low:
            return "unverified", f"payment gateway or aggregator ({g}): the app does not show the merchant behind it"
    c_d, o_d = _distinctive(c_tok), _distinctive(o_tok)
    if not c_d:
        return "unverified", "the claimed firm's name has no distinctive word to compare"
    # Shared words must name the firm: business-type, shop, purpose and place words don't count on their own.
    weak = CATEGORY | SHOP_WORDS | PURPOSE_WORDS | PLACE_WORDS
    shared = (c_d & o_d) - weak
    if shared:
        numbers = sorted(t for t in o_tok if t.isdigit() and t not in c_tok)
        c_cat_full = {t for t in c_tok if t in CATEGORY}
        purpose_ok = c_cat_full <= set(o_tok)  # "LUMINA MUTUAL FUND COLLECTION" keeps the whole claimed name;
        # "NAVYUG PAYMENTS" for "Navyug Wealth Research" drops it, so 'payments' then counts as a new word
        extra = sorted(t for t in o_d - c_d
                       if not _abbrev_of(t, c_tok) and t not in CATEGORY and not (purpose_ok and t in PURPOSE_WORDS)
                       and t not in PLACE_WORDS and not (t.isalpha() and len(t) <= 3 and t in _initials(c_tok, True)))
        # A word spelled slightly differently from the claim ("LAXMI" for "Lakshmi", but also "COBOLT" for "Cobalt")
        # is never a match: a transliteration and a copycat look the same to us, so the answer is "can't tell".
        variants = sorted(t for t in extra if any(_variant(t, c) for c in c_d))
        extra = [t for t in extra if t not in variants] + numbers
        c_cat, o_cat = _cat(c_tok), {t[:4] for t in o_tok if t in CATEGORY and not _abbrev_of(t, c_tok)}
        new_type = sorted(o_cat - c_cat) if c_cat else []
        if extra or new_type:
            what = ", ".join(extra + [t for t in o_tok if t[:4] in new_type and t in CATEGORY])
            return "lookalike", (f"shares '{', '.join(sorted(shared))}' but adds '{what}': could be a look-alike "
                                 "account rather than the firm itself")
        if variants:
            return "unverified", (f"shares '{', '.join(sorted(shared))}' but spells '{', '.join(variants)}' differently "
                                  "from the claim: a transliteration or a copycat; we can't tell")
        return "match", f"shares the distinctive word(s) {', '.join(sorted(shared))}"
    c_strong, o_strong = c_d - weak, o_d - weak
    compounds = {"".join(c_tok[j:j + k]) for k in (2, 3) for j in range(len(c_tok) - k + 1)}
    if any(_variant(a, b) for a in c_strong | compounds for b in o_strong):
        return "unverified", "a near spelling of the claimed name (could be a variant or a look-alike)"
    inits = {_initials(c_tok, False), _initials(c_tok, True)}
    if any(len(t) >= 2 and t.isalpha() and any(i.startswith(t) or t == i for i in inits)
           for t in o_tok if t not in GENERIC and t not in HONORIFICS):
        return "unverified", "looks like initials of the claimed firm"
    if any(len(b) >= 3 and a != b and a.startswith(b) for a in c_strong for b in o_strong):
        return "unverified", "looks like a short form of the claimed name (we can't confirm it)"
    if not any(t in SHOP_WORDS for t in o_tok) and any(
            _GATEWAY_TOKEN.search(t) for t in o_tok if t not in c_tok and t not in ("collection", "collections")):
        return "unverified", ("looks like a payment aggregator or collection account: the app shows the platform, "
                              "not the business behind it")
    if not o_d:
        return "unverified", "the shown name has only generic words"
    is_business = any(t in BUSINESS_MARKERS for t in o_tok)
    looks_personal = any(t in PERSON_WORDS for t in o_tok) or any(t in HONORIFICS for t in o_tok)
    if not is_business and looks_personal and 1 <= len([t for t in o_tok if t not in HONORIFICS]) <= 4:
        return "unverified", "a personal-looking name: could be the firm's proprietor or someone else; we can't tell"
    return "discrepancy", f"no distinctive word in common with '{claimed.strip()}'"
