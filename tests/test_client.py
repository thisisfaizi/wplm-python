from __future__ import annotations

import json
import time
from datetime import datetime, timedelta, timezone

import pytest

from wplm import (
    InMemoryTokenStore,
    WplmClient,
    WplmConfigError,
    WplmDeviceInfo,
    WplmLimitExceeded,
    WplmNetworkError,
)
from wplm.transport import Response

from .helpers import FakeTransport, TestSigner, error_body, success_body


def _offline(method: str, url: str, body: str | None) -> Response:
    raise WplmNetworkError("offline")


class _FakeDeviceInfo:
    def get(self) -> WplmDeviceInfo:
        return WplmDeviceInfo(
            name="srv01",
            hostname="srv01.local",
            platform="Linux 6.1 · Python 3.12",
            app_version="2.0.0",
        )


def test_validate_caches_signed_payload() -> None:
    store = InMemoryTokenStore()

    def handler(method: str, url: str, body: str | None) -> Response:
        if url.endswith("/validate"):
            return Response(
                200,
                success_body(
                    {
                        "valid": True,
                        "license": {"id": 1, "status": 1},
                        "signed_payload": "header.sig",
                        "needs_activation": False,
                    }
                ),
            )
        return Response(200, success_body({"crl": ""}))

    client = WplmClient(
        base_url="https://example.test",
        license_key="KEY",
        transport=FakeTransport(handler),
        store=store,
    )

    result = client.validate()

    assert result.valid is True
    assert result.license is not None
    assert result.license.id == 1
    assert store.read("wplm.signed_payload") == "header.sig"


def test_activate_returns_machine() -> None:
    client = WplmClient(
        base_url="https://example.test",
        license_key="KEY",
        transport=FakeTransport(
            lambda m, u, b: Response(
                201,
                success_body({"id": 7, "license_id": 1, "fingerprint": "fp", "status": 1}),
            )
        ),
    )

    machine = client.activate(name="Office PC")

    assert machine.id == 7
    assert machine.is_active is True


def test_error_mapping() -> None:
    client = WplmClient(
        base_url="https://example.test",
        license_key="KEY",
        transport=FakeTransport(
            lambda m, u, b: Response(
                422, error_body("machine_limit_exceeded", "No seats", 422)
            )
        ),
    )

    with pytest.raises(WplmLimitExceeded):
        client.activate()


def test_deactivate() -> None:
    client = WplmClient(
        base_url="https://example.test",
        license_key="KEY",
        transport=FakeTransport(
            lambda m, u, b: Response(200, success_body({"deactivated": True}))
        ),
    )

    assert client.deactivate() is True


def test_requires_key() -> None:
    client = WplmClient(
        base_url="https://example.test",
        transport=FakeTransport(lambda m, u, b: Response(200, success_body({}))),
    )

    with pytest.raises(WplmConfigError):
        client.validate()


def test_offline_valid() -> None:
    signer = TestSigner()
    token = signer.sign(
        {"key": "KEY", "expires": "2099-01-01T00:00:00Z", "max": 3, "iat": int(time.time())}
    )
    store = InMemoryTokenStore()
    store.write("wplm.signed_payload", token)

    client = WplmClient(
        base_url="https://example.test",
        license_key="KEY",
        public_key_base64=signer.public_key_base64,
        transport=FakeTransport(_offline),
        store=store,
    )

    result = client.validate(offline_ok=True)

    assert result.valid is True
    assert result.from_cache is True


def test_offline_expired() -> None:
    signer = TestSigner()
    token = signer.sign(
        {"key": "KEY", "expires": "2000-01-01T00:00:00Z", "max": 3, "iat": int(time.time())}
    )
    store = InMemoryTokenStore()
    store.write("wplm.signed_payload", token)

    client = WplmClient(
        base_url="https://example.test",
        license_key="KEY",
        public_key_base64=signer.public_key_base64,
        transport=FakeTransport(_offline),
        store=store,
    )

    result = client.validate(offline_ok=True)

    assert result.valid is False
    assert result.code == "expired"
    assert result.from_cache is True


def test_offline_no_cache_reraises() -> None:
    client = WplmClient(
        base_url="https://example.test",
        license_key="KEY",
        transport=FakeTransport(_offline),
        store=InMemoryTokenStore(),
    )

    with pytest.raises(WplmNetworkError):
        client.validate(offline_ok=True)


def test_offline_accepts_old_payload() -> None:
    # A payload issued long ago must still validate offline (its `expires`, not
    # the drift window, governs validity). This fails under the old abs() drift.
    signer = TestSigner()
    now = int(time.time())
    token = signer.sign(
        {
            "key": "KEY",
            "expires": "2099-01-01T00:00:00Z",
            "max": 3,
            "iat": now - 30 * 24 * 3600,
        }
    )
    store = InMemoryTokenStore()
    store.write("wplm.signed_payload", token)

    client = WplmClient(
        base_url="https://example.test",
        license_key="KEY",
        public_key_base64=signer.public_key_base64,
        transport=FakeTransport(_offline),
        store=store,
    )

    result = client.validate(offline_ok=True)

    assert result.valid is True
    assert result.from_cache is True


def test_offline_expired_even_if_clock_rolled_back() -> None:
    signer = TestSigner()
    now = int(time.time())
    # Valid by the device clock (expires tomorrow)...
    expires = (datetime.now(timezone.utc) + timedelta(days=1)).isoformat()
    token = signer.sign(
        {"key": "KEY", "expires": expires, "max": 3, "iat": now - 7 * 24 * 3600}
    )
    store = InMemoryTokenStore()
    store.write("wplm.signed_payload", token)
    # ...but a time PAST the expiry was already observed (high-water mark).
    store.write("wplm.time_floor", str(now + 2 * 24 * 3600))

    client = WplmClient(
        base_url="https://example.test",
        license_key="KEY",
        public_key_base64=signer.public_key_base64,
        transport=FakeTransport(_offline),
        store=store,
    )

    result = client.validate(offline_ok=True)

    assert result.valid is False
    assert result.code == "expired"


def test_activate_sends_device_info() -> None:
    transport = FakeTransport(
        lambda m, u, b: Response(
            201,
            success_body({"id": 1, "license_id": 1, "fingerprint": "fp", "status": 1}),
        )
    )
    client = WplmClient(
        base_url="https://example.test",
        license_key="KEY",
        transport=transport,
        device_info_provider=_FakeDeviceInfo(),
    )

    client.activate()

    sent = json.loads(transport.calls[-1][2] or "{}")
    assert sent["name"] == "srv01"
    assert sent["hostname"] == "srv01.local"
    assert sent["platform"] == "Linux 6.1 · Python 3.12"
    assert sent["app_version"] == "2.0.0"


def test_explicit_activate_args_override_device_info() -> None:
    transport = FakeTransport(
        lambda m, u, b: Response(
            201,
            success_body({"id": 1, "license_id": 1, "fingerprint": "fp", "status": 1}),
        )
    )
    client = WplmClient(
        base_url="https://example.test",
        license_key="KEY",
        transport=transport,
        device_info_provider=_FakeDeviceInfo(),
    )

    client.activate(name="Custom")

    sent = json.loads(transport.calls[-1][2] or "{}")
    assert sent["name"] == "Custom"
