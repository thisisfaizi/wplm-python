from __future__ import annotations

import hashlib
import time

import pytest

from wplm import RevocationList, SignatureVerifier, WplmSignatureInvalid

from .helpers import TestSigner


def test_parses_and_detects_revoked_key() -> None:
    signer = TestSigner()
    revoked_key = "REVOKED-1234"
    revoked_hash = hashlib.sha256(revoked_key.encode()).hexdigest()

    token = signer.sign(
        {
            "revoked_keys": [revoked_hash],
            "revoked_fingerprints": [],
            "generated_at": "2026-06-16T00:00:00+00:00",
            "iat": int(time.time()),
        }
    )
    crl = RevocationList.parse(token, SignatureVerifier.from_base64(signer.public_key_base64))

    assert crl.is_key_revoked(revoked_key) is True
    assert crl.is_key_revoked("OTHER-KEY") is False
    assert revoked_hash in crl.revoked_key_hashes


def test_rejects_wrong_key() -> None:
    signer, other = TestSigner(), TestSigner()
    token = signer.sign({"revoked_keys": [], "revoked_fingerprints": [], "iat": 1})

    with pytest.raises(WplmSignatureInvalid):
        RevocationList.parse(token, SignatureVerifier.from_base64(other.public_key_base64))
