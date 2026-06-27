"""Stable per-device fingerprint providers."""

from __future__ import annotations

import secrets
from typing import Protocol, runtime_checkable

from .storage import TokenStore


@runtime_checkable
class FingerprintProvider(Protocol):
    """Produces a stable per-device fingerprint (raw; the server hashes it)."""

    def get(self) -> str:
        ...


class PersistedUuidFingerprintProvider:
    """Generates a random fingerprint once and persists it in the store."""

    def __init__(self, store: TokenStore, storage_key: str = "wplm.fingerprint") -> None:
        self._store = store
        self.storage_key = storage_key

    def get(self) -> str:
        existing = self._store.read(self.storage_key)
        if existing:
            return existing
        fingerprint = secrets.token_hex(32)
        self._store.write(self.storage_key, fingerprint)
        return fingerprint


class StaticFingerprintProvider:
    """Always returns a caller-supplied value (e.g. a hardware id)."""

    def __init__(self, value: str) -> None:
        self.value = value

    def get(self) -> str:
        return self.value
