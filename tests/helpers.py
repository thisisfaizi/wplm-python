"""Shared test helpers: a server-compatible token signer and a fake transport."""

from __future__ import annotations

import base64
import json
from collections.abc import Callable
from typing import Any

from nacl.signing import SigningKey

from wplm.transport import Response


def _b64url(raw: bytes) -> str:
    return base64.urlsafe_b64encode(raw).rstrip(b"=").decode("ascii")


class TestSigner:
    """Issues WPLM-format signed tokens, mirroring the server's Signer."""

    __test__ = False  # Not a pytest test class.

    def __init__(self) -> None:
        self.signing_key = SigningKey.generate()
        self.public_key_base64 = base64.b64encode(
            bytes(self.signing_key.verify_key)
        ).decode("ascii")

    def sign(self, payload: dict[str, Any]) -> str:
        body = _b64url(json.dumps(payload).encode("utf-8"))
        signature = self.signing_key.sign(body.encode("utf-8")).signature
        return f"{body}.{_b64url(signature)}"


class FakeTransport:
    """A scripted transport for unit tests."""

    def __init__(
        self,
        handler: Callable[[str, str, str | None], Response],
    ) -> None:
        self.handler = handler
        self.calls: list[tuple[str, str, str | None]] = []

    def send(
        self,
        method: str,
        url: str,
        headers: dict[str, str] | None = None,
        body: str | None = None,
    ) -> Response:
        self.calls.append((method, url, body))
        return self.handler(method, url, body)

    def close(self) -> None:
        pass


def success_body(data: dict[str, Any]) -> str:
    return json.dumps({"success": True, "data": data, "meta": {}})


def error_body(code: str, message: str, status: int) -> str:
    return json.dumps({"code": code, "message": message, "data": {"status": status}})
