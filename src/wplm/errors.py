"""Typed exception hierarchy for the WPLM SDK."""

from __future__ import annotations


class WplmError(Exception):
    """Base class for all errors raised by the SDK."""

    def __init__(
        self,
        message: str,
        *,
        code: str | None = None,
        status: int | None = None,
    ) -> None:
        super().__init__(message)
        self.message = message
        self.code = code
        self.status = status

    @staticmethod
    def from_code(
        code: str,
        message: str,
        status: int | None = None,
    ) -> WplmError:
        """Map a server error ``code`` to a concrete exception type."""
        mapping: dict[str, type[WplmError]] = {
            "license_not_found": WplmNotFound,
            "wplm_not_found": WplmNotFound,
            "expired": WplmExpired,
            "license_expired": WplmExpired,
            "license_suspended": WplmSuspended,
            "license_revoked": WplmRevoked,
            "license_terminated": WplmTerminated,
            "machine_limit_exceeded": WplmLimitExceeded,
            "blacklisted": WplmBlacklisted,
            "license_pending": WplmNotActive,
            "license_not_active": WplmNotActive,
            "machine_not_found": WplmMachineNotFound,
            "machine_inactive": WplmMachineNotFound,
            "product_mismatch": WplmProductMismatch,
        }
        cls = mapping.get(code, WplmApiError)
        return cls(message, code=code, status=status)


class WplmNotFound(WplmError):
    """The license/key was not found."""


class WplmExpired(WplmError):
    """The license is past its expiry (plus any grace period)."""


class WplmSuspended(WplmError):
    """The license is temporarily suspended."""


class WplmRevoked(WplmError):
    """The license has been revoked."""


class WplmTerminated(WplmError):
    """The license has been permanently terminated."""


class WplmLimitExceeded(WplmError):
    """No activation seats are available under the overage strategy."""


class WplmBlacklisted(WplmError):
    """The key, fingerprint, or IP is on a deny list."""


class WplmNotActive(WplmError):
    """The license is not yet active (pending first payment/delivery)."""


class WplmMachineNotFound(WplmError):
    """The device/machine was not found or is inactive."""


class WplmProductMismatch(WplmError):
    """The license is bound to a different product than this client expects.

    Raised when the signed payload's ``pid`` does not match the configured
    ``product_id``. Enforced online and offline from the cryptographically
    signed payload, so a key issued for product A cannot run in product B's app.
    """


class WplmApiError(WplmError):
    """A generic API error that did not map to a more specific type."""


class WplmNetworkError(WplmError):
    """The network request failed (offline, timeout, DNS, TLS)."""

    def __init__(self, message: str, *, cause: BaseException | None = None) -> None:
        super().__init__(message)
        self.cause = cause


class WplmSignatureInvalid(WplmError):
    """A signed payload or CRL failed Ed25519 verification."""


class WplmConfigError(WplmError):
    """The SDK was misconfigured (e.g. missing license key or base URL)."""
