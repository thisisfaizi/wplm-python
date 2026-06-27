"""Pluggable persistent store for cached tokens."""

from __future__ import annotations

import json
import os
import tempfile
from typing import Protocol, runtime_checkable


@runtime_checkable
class TokenStore(Protocol):
    """Persistent key/value store for cached tokens (signed payload, CRL, fp)."""

    def read(self, key: str) -> str | None:
        ...

    def write(self, key: str, value: str) -> None:
        ...

    def delete(self, key: str) -> None:
        ...


class InMemoryTokenStore:
    """Default in-memory store (suitable for tests and short-lived processes)."""

    def __init__(self) -> None:
        self._data: dict[str, str] = {}

    def read(self, key: str) -> str | None:
        return self._data.get(key)

    def write(self, key: str, value: str) -> None:
        self._data[key] = value

    def delete(self, key: str) -> None:
        self._data.pop(key, None)


class FileTokenStore:
    """Persists tokens as a JSON file (default: a per-user temp path).

    For desktop apps prefer an OS keyring; this is a simple cross-platform
    default for CLIs and servers.
    """

    def __init__(self, path: str | None = None) -> None:
        self.path = path or os.path.join(tempfile.gettempdir(), "wplm_store.json")

    def _load(self) -> dict[str, str]:
        try:
            with open(self.path, encoding="utf-8") as fh:
                data = json.load(fh)
            return {str(k): str(v) for k, v in data.items()} if isinstance(data, dict) else {}
        except (OSError, ValueError):
            return {}

    def _save(self, data: dict[str, str]) -> None:
        with open(self.path, "w", encoding="utf-8") as fh:
            json.dump(data, fh)

    def read(self, key: str) -> str | None:
        return self._load().get(key)

    def write(self, key: str, value: str) -> None:
        data = self._load()
        data[key] = value
        self._save(data)

    def delete(self, key: str) -> None:
        data = self._load()
        data.pop(key, None)
        self._save(data)
