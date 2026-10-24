"""UPI QR codes in screenshots and images (FINALE, Claude C; class D: comes from the sender, never decides alone).

decode_qr(data: bytes) -> list[str]          every QR payload OpenCV finds in the image (no network, CPU only)
parse_upi(payload: str) -> dict | None       fields of a UPI payment link:
    upi://pay?pa=<payee address>&pn=<payee name>&am=<amount>&tn=<note>&mc=<merchant code>...
    (NPCI UPI linking specification; Bharat QR / EMVCo merchant codes carry the same UPI link in a tag
    and are only read here when the decoded text contains "upi://pay").

The payee name inside a QR ("pn") is typed by whoever made the QR. It is NOT the bank's registered name, so VERIQ
uses it only to notice when the sender's own QR names someone other than the claimed firm, and always asks the user
to check the name their own UPI app shows (class A).
"""

from __future__ import annotations

import re
from urllib.parse import parse_qs, unquote_plus, urlsplit

MAX_SIDE = 2200  # downscale very large screenshots before decoding


def decode_qr(data: bytes) -> list[str]:
    try:
        import cv2  # type: ignore
        import numpy as np  # type: ignore
    except ImportError:
        return []
    arr = np.frombuffer(data, dtype=np.uint8)
    img = cv2.imdecode(arr, cv2.IMREAD_GRAYSCALE)
    if img is None:
        return []
    h, w = img.shape[:2]
    if max(h, w) > MAX_SIDE:
        f = MAX_SIDE / max(h, w)
        img = cv2.resize(img, (int(w * f), int(h * f)), interpolation=cv2.INTER_AREA)
    det = cv2.QRCodeDetector()
    found: list[str] = []
    for candidate in (img, cv2.copyMakeBorder(img, 40, 40, 40, 40, cv2.BORDER_CONSTANT, value=255)):
        try:
            ok, texts, _, _ = det.detectAndDecodeMulti(candidate)
        except cv2.error:
            ok, texts = False, []
        if ok:
            found += [t for t in texts if t]
        if not found:
            try:
                t, _, _ = det.detectAndDecode(candidate)
            except cv2.error:
                t = ""
            if t:
                found.append(t)
        if found:
            break
    return list(dict.fromkeys(found))


_UPI = re.compile(r"upi://pay\?[^\s\"'<>]+", re.I)


def parse_upi(payload: str) -> dict | None:
    m = _UPI.search(payload or "")
    if not m:
        return None
    link = m.group(0)
    q = parse_qs(urlsplit(link).query, keep_blank_values=True)

    def one(k):
        v = q.get(k) or q.get(k.upper())
        return unquote_plus(v[0]).strip() if v else ""

    pa = one("pa").lower()
    if not re.fullmatch(r"[a-z0-9][a-z0-9._-]{1,63}@[a-z][a-z0-9]{1,31}", pa):
        return None
    am = one("am")
    try:
        amount = int(float(am)) if am else None
    except ValueError:
        amount = None
    return {"link": link, "pa": pa, "pn": one("pn")[:80], "am": amount, "tn": one("tn")[:80], "mc": one("mc")}
