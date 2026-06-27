"""Official Python SDK for WP License Manager (WPLM).

Validate, activate, and verify software licenses online and offline.
"""

from __future__ import annotations

from .client import WplmClient
from .crypto import RevocationList, SignatureVerifier
from .device_info import DeviceInfoProvider, LocalDeviceInfoProvider, WplmDeviceInfo
from .errors import (
    WplmApiError,
    WplmBlacklisted,
    WplmConfigError,
    WplmError,
    WplmExpired,
    WplmLimitExceeded,
    WplmMachineNotFound,
    WplmNetworkError,
    WplmNotActive,
    WplmNotFound,
    WplmProductMismatch,
    WplmRevoked,
    WplmSignatureInvalid,
    WplmSuspended,
    WplmTerminated,
)
from .fingerprint import (
    FingerprintProvider,
    PersistedUuidFingerprintProvider,
    StaticFingerprintProvider,
)
from .models import License, Machine, ValidationResult
from .storage import FileTokenStore, InMemoryTokenStore, TokenStore
from .transport import RequestsTransport, Response, Transport

__version__ = "0.2.0"

__all__ = [
    "DeviceInfoProvider",
    "FileTokenStore",
    "FingerprintProvider",
    "InMemoryTokenStore",
    "License",
    "LocalDeviceInfoProvider",
    "Machine",
    "PersistedUuidFingerprintProvider",
    "RequestsTransport",
    "Response",
    "RevocationList",
    "SignatureVerifier",
    "StaticFingerprintProvider",
    "TokenStore",
    "Transport",
    "ValidationResult",
    "WplmApiError",
    "WplmBlacklisted",
    "WplmClient",
    "WplmConfigError",
    "WplmDeviceInfo",
    "WplmError",
    "WplmExpired",
    "WplmLimitExceeded",
    "WplmMachineNotFound",
    "WplmNetworkError",
    "WplmNotActive",
    "WplmNotFound",
    "WplmProductMismatch",
    "WplmRevoked",
    "WplmSignatureInvalid",
    "WplmSuspended",
    "WplmTerminated",
]
