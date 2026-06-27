"""Offline Ed25519 verification of WPLM signed tokens and the CRL."""

from __future__ import annotations

import base64
import hashlib
import json
import time
from typing import Any

from nacl.exceptions import BadSignatureError
from nacl.signing import VerifyKey

from .errors import WplmSignatureInvalid


def _b64url_decode(value: str) -> bytes:
    normalized = value.replace("-", "+").replace("_", "/")
    padding = (-len(normalized)) % 4
    try:
        return base64.b64decode(normalized + ("=" * padding))
    except ValueError as exc:  # binascii.Error subclasses ValueError
        raise WplmSignatureInvalid(f"Invalid base64url segment: {exc}") from exc


class SignatureVerifier:
    """Verifies ``base64url(json).base64url(sig)`` tokens with the server's key.

    The signature is computed over the *base64url(json) string* (not the raw
    JSON). The public key is the standard-base64 value from ``/public-key``.
    """

    def __init__(self, public_key: bytes) -> None:
        self._verify_key = VerifyKey(public_key)

    @classmethod
    def from_base64(cls, public_key_base64: str) -> SignatureVerifier:
        try:
            return cls(base64.b64decode(public_key_base64.strip()))
        except Exception as exc:
            raise WplmSignatureInvalid(
                f"Invalid public key encoding: {exc}"
            ) from exc

    def verify(self, token: str) -> dict[str, Any]:
        """Verify ``token`` and return the decoded JSON payload."""
        dot = token.find(".")
        if dot <= 0 or dot >= len(token) - 1:
            raise WplmSignatureInvalid("Malformed signed token")

        body = token[:dot]
        signature = _b64url_decode(token[dot + 1 :])

        try:
            self._verify_key.verify(body.encode("utf-8"), signature)
        except BadSignatureError as exc:
            raise WplmSignatureInvalid("Signature verification failed") from exc

        payload = json.loads(_b64url_decode(body).decode("utf-8"))
        if not isinstance(payload, dict):
            raise WplmSignatureInvalid("Signed payload is not a JSON object")
        return payload

    @staticmethod
    def is_within_clock_drift(
        payload: dict[str, Any],
        max_drift_seconds: float,
    ) -> bool:
        """Whether a cached payload's ``iat`` is acceptable (one-sided check).

        Rejects only a payload that appears issued in the *future* by more than
        ``max_drift_seconds`` (the device clock was rolled back). An arbitrarily
        *old* payload is fine — offline validity is governed by ``expires``, not
        time-boxed to the drift window.
        """
        iat = payload.get("iat")
        if not isinstance(iat, (int, float)):
            return True
        return float(iat) - time.time() <= max_drift_seconds


class RevocationList:
    """A verified CRL: revoked license-key hashes and device fingerprints.

    A client can match its own license key offline (it knows the plaintext key,
    so it can compute the SHA-256), but cannot recompute the server-side HMAC of
    its fingerprint — device revocation is enforced online via ``/validate``.
    """

    def __init__(
        self,
        revoked_key_hashes: set[str],
        revoked_fingerprints: set[str],
        generated_at: str | None = None,
    ) -> None:
        self.revoked_key_hashes = revoked_key_hashes
        self.revoked_fingerprints = revoked_fingerprints
        self.generated_at = generated_at

    @classmethod
    def parse(cls, token: str, verifier: SignatureVerifier) -> RevocationList:
        payload = verifier.verify(token)

        def as_set(value: Any) -> set[str]:
            return {s for s in value if isinstance(s, str)} if isinstance(value, list) else set()

        generated = payload.get("generated_at")
        return cls(
            revoked_key_hashes=as_set(payload.get("revoked_keys")),
            revoked_fingerprints=as_set(payload.get("revoked_fingerprints")),
            generated_at=generated if isinstance(generated, str) else None,
        )

    def is_key_revoked(self, license_key: str) -> bool:
        digest = hashlib.sha256(license_key.encode("utf-8")).hexdigest()
        return digest in self.revoked_key_hashes
