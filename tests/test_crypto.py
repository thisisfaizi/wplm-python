from __future__ import annotations

import time

import pytest

from wplm import SignatureVerifier, WplmSignatureInvalid

from .helpers import TestSigner


def test_verifies_genuine_token() -> None:
    signer = TestSigner()
    token = signer.sign({"key": "ABCD-EFGH", "max": 3, "iat": int(time.time())})
    verifier = SignatureVerifier.from_base64(signer.public_key_base64)

    payload = verifier.verify(token)

    assert payload["key"] == "ABCD-EFGH"
    assert payload["max"] == 3


def test_rejects_tampered_token() -> None:
    signer = TestSigner()
    token = signer.sign({"key": "X", "iat": 1})
    verifier = SignatureVerifier.from_base64(signer.public_key_base64)

    tampered = "A" + token[1:]

    with pytest.raises(WplmSignatureInvalid):
        verifier.verify(tampered)


def test_rejects_wrong_key() -> None:
    a, b = TestSigner(), TestSigner()
    token = a.sign({"key": "A", "iat": 1})
    verifier = SignatureVerifier.from_base64(b.public_key_base64)

    with pytest.raises(WplmSignatureInvalid):
        verifier.verify(token)


def test_rejects_malformed_token() -> None:
    signer = TestSigner()
    verifier = SignatureVerifier.from_base64(signer.public_key_base64)

    with pytest.raises(WplmSignatureInvalid):
        verifier.verify("not-a-token")


def test_clock_drift() -> None:
    now = int(time.time())
    # Fresh payload: accepted.
    assert SignatureVerifier.is_within_clock_drift({"iat": now}, 300) is True
    # Old payload: still accepted — offline validity is governed by `expires`,
    # not time-boxed to the drift window.
    assert SignatureVerifier.is_within_clock_drift({"iat": now - 3600}, 300) is True
    # Payload issued in the future beyond the window: rejected (clock rolled back).
    assert SignatureVerifier.is_within_clock_drift({"iat": now + 3600}, 300) is False
