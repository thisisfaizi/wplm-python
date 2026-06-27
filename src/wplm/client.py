"""The WPLM client."""

from __future__ import annotations

import contextlib
import json
import re
import time
from datetime import datetime, timezone
from types import TracebackType
from typing import Any

from .crypto import RevocationList, SignatureVerifier
from .device_info import DeviceInfoProvider, WplmDeviceInfo
from .errors import WplmApiError, WplmConfigError, WplmError, WplmNetworkError, WplmSignatureInvalid
from .fingerprint import FingerprintProvider, PersistedUuidFingerprintProvider
from .models import Machine, ValidationResult
from .storage import InMemoryTokenStore, TokenStore
from .transport import RequestsTransport, Response, Transport

_K_SIGNED = "wplm.signed_payload"
_K_PUBKEY = "wplm.public_key"
_K_CRL = "wplm.crl"
_K_CRL_AT = "wplm.crl_at"
_K_TIME_FLOOR = "wplm.time_floor"


class WplmClient:
    """Talks to a WPLM server's ``wplm/v1`` API and verifies licenses offline.

    Example::

        with WplmClient(base_url="https://license.vendor.com", license_key=key) as wplm:
            wplm.activate()
            result = wplm.validate(offline_ok=True)
    """

    def __init__(
        self,
        *,
        base_url: str,
        license_key: str | None = None,
        product_id: int | None = None,
        public_key_base64: str | None = None,
        max_clock_drift: float = 300.0,
        crl_ttl: float = 3600.0,
        transport: Transport | None = None,
        store: TokenStore | None = None,
        fingerprint_provider: FingerprintProvider | None = None,
        device_info_provider: DeviceInfoProvider | None = None,
    ) -> None:
        self._base = self._normalize_base(base_url)
        self.license_key = license_key
        self.product_id = product_id
        self.public_key_base64 = public_key_base64
        self.max_clock_drift = max_clock_drift
        self.crl_ttl = crl_ttl
        self._transport: Transport = transport or RequestsTransport()
        self._store: TokenStore = store or InMemoryTokenStore()
        self._fingerprint: FingerprintProvider = (
            fingerprint_provider or PersistedUuidFingerprintProvider(self._store)
        )
        self._device_info_provider = device_info_provider
        self._device_info_cache: WplmDeviceInfo | None = None
        self._verifier: SignatureVerifier | None = None

    # ------------------------------------------------------------------ ops

    def validate(self, offline_ok: bool = False) -> ValidationResult:
        """Validate the license. Falls back to a cached signed payload offline."""
        key = self._require_key()
        try:
            data = self._post(
                "/validate",
                {"license_key": key, "fingerprint": self._fingerprint.get()},
            )
            result = ValidationResult.from_json(data)
            if result.signed_payload:
                self._store.write(_K_SIGNED, result.signed_payload)
            # A successful online call is a trusted clock reading — advance the
            # monotonic time floor so a later offline rollback is detectable.
            self._advance_time_floor(int(time.time()))
            self._maybe_refresh_crl()
            return result
        except WplmNetworkError:
            if offline_ok:
                offline = self._validate_offline(key)
                if offline is not None:
                    return offline
            raise

    def activate(
        self,
        *,
        name: str | None = None,
        hostname: str | None = None,
        platform: str | None = None,
        app_version: str | None = None,
    ) -> Machine:
        """Activate (bind) the current device. Idempotent."""
        body: dict[str, Any] = {
            "license_key": self._require_key(),
            "fingerprint": self._fingerprint.get(),
            **self._device_fields(
                name=name,
                hostname=hostname,
                platform=platform,
                app_version=app_version,
            ),
        }
        return Machine.from_json(self._post("/activate", body))

    def deactivate(self) -> bool:
        """Deactivate the current device, freeing its seat."""
        data = self._post(
            "/deactivate",
            {"license_key": self._require_key(), "fingerprint": self._fingerprint.get()},
        )
        return data.get("deactivated") is True

    def heartbeat(self, *, app_version: str | None = None) -> Machine:
        """Send a heartbeat / renew a floating lease."""
        resolved_version = app_version
        if resolved_version is None:
            info = self._device_info()
            resolved_version = info.app_version if info else None
        body: dict[str, Any] = {
            "license_key": self._require_key(),
            "fingerprint": self._fingerprint.get(),
        }
        if resolved_version is not None:
            body["app_version"] = resolved_version
        return Machine.from_json(self._post("/heartbeat", body))

    def verify_offline(self, token: str) -> dict[str, Any]:
        """Verify an arbitrary signed token offline; returns the payload."""
        return self._get_verifier().verify(token)

    def check_crl(self) -> RevocationList:
        """Fetch, verify, and cache the revocation list."""
        data = self._get("/crl")
        token = str(data.get("crl") or "")
        verifier = self._get_verifier()
        crl = RevocationList.parse(token, verifier)
        self._store.write(_K_CRL, token)
        self._store.write(_K_CRL_AT, str(int(time.time() * 1000)))
        return crl

    def close(self) -> None:
        """Release the underlying transport."""
        self._transport.close()

    def __enter__(self) -> WplmClient:
        return self

    def __exit__(
        self,
        exc_type: type[BaseException] | None,
        exc: BaseException | None,
        tb: TracebackType | None,
    ) -> None:
        self.close()

    # -------------------------------------------------------------- offline

    def _validate_offline(self, key: str) -> ValidationResult | None:
        token = self._store.read(_K_SIGNED)
        if not token:
            return None

        verifier = self._verifier_or_none(allow_network=False)
        if verifier is None:
            return None

        try:
            payload = verifier.verify(token)
        except WplmSignatureInvalid:
            return ValidationResult(valid=False, code="signature_invalid", from_cache=True)

        if not SignatureVerifier.is_within_clock_drift(payload, self.max_clock_drift):
            return ValidationResult(valid=False, code="clock_drift", from_cache=True)

        # Monotonic time floor (high-water mark): use the greatest of the device
        # clock, the payload's issue time, and the highest time ever observed, so
        # a rolled-back clock cannot un-expire the license offline.
        iat = payload.get("iat")
        if isinstance(iat, (int, float)):
            self._advance_time_floor(int(iat))
        device_now = int(time.time())
        self._advance_time_floor(device_now)
        effective_now = self._read_time_floor()

        expires = payload.get("expires")
        if isinstance(expires, str) and expires:
            try:
                exp = datetime.fromisoformat(expires.replace("Z", "+00:00"))
                exp_epoch = int(exp.astimezone(timezone.utc).timestamp())
                if effective_now > exp_epoch:
                    return ValidationResult(valid=False, code="expired", from_cache=True)
            except ValueError:
                pass

        crl = self._cached_crl(verifier)
        if crl is not None and crl.is_key_revoked(key):
            return ValidationResult(valid=False, code="revoked", from_cache=True)

        return ValidationResult(valid=True, from_cache=True)

    def _read_time_floor(self) -> int:
        """Highest trusted unix-second time ever observed (defaults to 0)."""
        raw = self._store.read(_K_TIME_FLOOR)
        try:
            return int(raw) if raw is not None else 0
        except ValueError:
            return 0

    def _advance_time_floor(self, epoch_seconds: int) -> None:
        """Advance the floor if newer; never moves backwards."""
        if epoch_seconds <= 0:
            return
        if epoch_seconds > self._read_time_floor():
            self._store.write(_K_TIME_FLOOR, str(epoch_seconds))

    # -------------------------------------------------------- device metadata

    def _device_info(self) -> WplmDeviceInfo | None:
        if self._device_info_provider is None:
            return None
        if self._device_info_cache is None:
            self._device_info_cache = self._device_info_provider.get()
        return self._device_info_cache

    def _device_fields(
        self,
        *,
        name: str | None,
        hostname: str | None,
        platform: str | None,
        app_version: str | None,
    ) -> dict[str, str]:
        """Merge explicit args over provider-supplied device info, dropping empties."""
        info = self._device_info()
        out: dict[str, str] = {}
        values = {
            "name": name or (info.name if info else None),
            "hostname": hostname or (info.hostname if info else None),
            "platform": platform or (info.platform if info else None),
            "app_version": app_version or (info.app_version if info else None),
        }
        for key, value in values.items():
            if value:
                out[key] = value
        return out

    def _cached_crl(self, verifier: SignatureVerifier) -> RevocationList | None:
        token = self._store.read(_K_CRL)
        if not token:
            return None
        try:
            return RevocationList.parse(token, verifier)
        except WplmSignatureInvalid:
            return None

    def _maybe_refresh_crl(self) -> None:
        at = self._store.read(_K_CRL_AT)
        if at is not None:
            try:
                age = time.time() * 1000 - int(at)
                if age < self.crl_ttl * 1000:
                    return
            except ValueError:
                pass
        # Best-effort; a stale/missing CRL must not break online validation.
        with contextlib.suppress(WplmError):
            self.check_crl()

    # ------------------------------------------------------------- verifier

    def _get_verifier(self) -> SignatureVerifier:
        verifier = self._verifier_or_none(allow_network=True)
        if verifier is None:
            raise WplmConfigError(
                "No Ed25519 public key available. Pass public_key_base64 or call "
                "an online method once to fetch and cache it."
            )
        return verifier

    def _verifier_or_none(self, *, allow_network: bool) -> SignatureVerifier | None:
        if self._verifier is not None:
            return self._verifier
        b64 = self.public_key_base64 or self._store.read(_K_PUBKEY)
        if not b64 and allow_network:
            data = self._get("/public-key")
            fetched = data.get("public_key")
            if isinstance(fetched, str) and fetched:
                self._store.write(_K_PUBKEY, fetched)
                b64 = fetched
        if not b64:
            return None
        self._verifier = SignatureVerifier.from_base64(b64)
        return self._verifier

    # ----------------------------------------------------------------- http

    def _post(self, path: str, body: dict[str, Any]) -> dict[str, Any]:
        res = self._transport.send(
            "POST",
            self._base + path,
            headers={"Content-Type": "application/json", "Accept": "application/json"},
            body=json.dumps(body),
        )
        return self._unwrap(res)

    def _get(self, path: str) -> dict[str, Any]:
        res = self._transport.send(
            "GET",
            self._base + path,
            headers={"Accept": "application/json"},
        )
        return self._unwrap(res)

    def _unwrap(self, res: Response) -> dict[str, Any]:
        try:
            decoded = json.loads(res.body)
        except ValueError:
            decoded = None

        if not isinstance(decoded, dict):
            raise WplmApiError(
                f"Unexpected response (HTTP {res.status_code})",
                status=res.status_code,
            )

        if decoded.get("success") is True and isinstance(decoded.get("data"), dict):
            return decoded["data"]  # type: ignore[no-any-return]

        code = str(decoded.get("code") or "wplm_unknown_error")
        message = str(decoded.get("message") or f"Request failed (HTTP {res.status_code}).")
        raise WplmError.from_code(code, message, status=res.status_code)

    def _require_key(self) -> str:
        if not self.license_key:
            raise WplmConfigError("No license_key configured.")
        return self.license_key

    @staticmethod
    def _normalize_base(base_url: str) -> str:
        trimmed = re.sub(r"/+$", "", base_url.strip())
        return f"{trimmed}/wp-json/wplm/v1"
