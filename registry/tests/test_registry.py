import hashlib

import pytest

from registry.interface import hmac_indicator, is_non_attributable
from registry.stub import StubRegistry


def test_unknown_payee_is_unavailable_not_clean():
    r = StubRegistry().lookup("p1", "upi_vpa", "someone.new@upi")
    assert r.status == "unavailable" and "STUB" in r.source


def test_only_fixture_keys_return_clean_or_linked():
    reg = StubRegistry()
    assert reg.lookup("p", "upi_vpa", "navyug.brk@validhdfc").status == "clean"
    assert reg.lookup("p", "upi_vpa", "fixture.linked@upi").status == "linked"


def test_gateway_handles_never_link():
    assert is_non_attributable("upi_vpa", "shop@razorpay")
    assert StubRegistry().lookup("p", "upi_vpa", "shop@razorpay").status == "unavailable"


def test_hmac_is_keyed_namespaced_and_not_a_plain_hash():
    s = b"0123456789abcdef-secret"
    a = hmac_indicator(s, "upi_vpa", "ramesh.k@upi")
    assert a != hashlib.sha256(b"ramesh.k@upi").hexdigest()
    assert a != hmac_indicator(s, "phone", "ramesh.k@upi")
    assert a != hmac_indicator(b"another-secret-of-16b", "upi_vpa", "ramesh.k@upi")
    assert a == hmac_indicator(s, "upi_vpa", " RAMESH.K@UPI ")
    with pytest.raises(ValueError):
        hmac_indicator(b"short", "upi_vpa", "x@upi")
