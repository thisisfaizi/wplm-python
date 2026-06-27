<div align="center">

<img src="https://capsule-render.vercel.app/api?type=waving&color=gradient&customColorList=12,18,25&height=160&section=header&text=wplm-python&fontSize=50&fontAlignY=42&animation=fadeIn&fontColor=ffffff" />

### WP License Manager — Python SDK

[![PyPI](https://img.shields.io/pypi/v/wplm?style=for-the-badge&logo=pypi&logoColor=white&color=3776AB)](https://pypi.org/project/wplm/)
[![CI](https://img.shields.io/github/actions/workflow/status/wplm/wplm-python/ci.yaml?style=for-the-badge&label=CI&logo=github-actions&logoColor=white)](https://github.com/thisisfaizi/wplm-python/actions/workflows/ci.yaml)
[![Coverage](https://img.shields.io/codecov/c/github/wplm/wplm-python?style=for-the-badge&logo=codecov&logoColor=white)](https://codecov.io/gh/wplm/wplm-python)
[![License](https://img.shields.io/badge/License-MIT-green?style=for-the-badge)](LICENSE)
[![Python](https://img.shields.io/badge/Python-3.9%2B-3776AB?style=for-the-badge&logo=python&logoColor=white)](https://python.org)

<p>Offline-first Ed25519 license validation for Python desktop apps, CLIs, and servers,<br>
backed by a self-hosted <a href="https://github.com/thisisfaizi/wp-license-manager">WP License Manager</a> server.</p>

</div>

---

The official Python client for **[WP License Manager (WPLM)](https://github.com/thisisfaizi/wp-license-manager)**.
Validate, activate, and verify software licenses — **online and fully offline** —
from desktop apps (PyQt/Tk), CLIs, scripts, and servers on Windows, macOS, and Linux.

- ✅ `validate` / `activate` / `deactivate` / `heartbeat`
- 🔏 **Offline** Ed25519 signature verification (no network needed)
- 🛡️ Signed CRL check (reject revoked keys offline)
- 🔌 Pluggable HTTP transport, fingerprint provider, and token store
- 🧯 Typed exceptions, retries with backoff, replay/clock-drift protection
- 🏷️ Fully type-hinted (`py.typed`)

---

## Install

```bash
pip install wplm
```

---

## Quick Start

```python
from wplm import WplmClient

with WplmClient(
    base_url="https://license.vendor.com",
    product_id=42,
    license_key=user_entered_key,
) as wplm:
    wplm.activate()                           # bind this device (consumes a seat)
    result = wplm.validate(offline_ok=True)   # online; offline fallback from cache
    if result.valid:
        ...                                   # unlock pro features
    wplm.heartbeat()                          # keep a floating lease alive
    wplm.deactivate()                         # free the seat on sign-out
```

---

## Offline Verification

`validate(offline_ok=True)` verifies the cached, Ed25519-signed payload locally
and checks it against the cached revocation list — so your app keeps working
without a network, and a revoked key is rejected within your CRL refresh window.

For zero-network offline verification, bundle the public key at build time:

```python
wplm = WplmClient(
    base_url="https://license.vendor.com",
    license_key=key,
    public_key_base64="PASTE FROM GET /wp-json/wplm/v1/public-key",
)
```

---

## Custom Fingerprint and Storage

Implement `FingerprintProvider` and `TokenStore` to bind to hardware IDs or use
an OS keyring; pass them to the client. A persisted-UUID fingerprint and a JSON
`FileTokenStore` are provided out of the box.

```python
from wplm import WplmClient
from wplm.storage import FileTokenStore
from wplm.fingerprint import PersistedUuidFingerprintProvider

wplm = WplmClient(
    base_url="https://license.vendor.com",
    license_key=key,
    store=FileTokenStore("/var/lib/myapp/.wplm"),
    fingerprint_provider=PersistedUuidFingerprintProvider("/var/lib/myapp/.wplm"),
)
```

---

## Subscription Renewal

Renewals are handled through **WooCommerce My Account → Subscriptions → Renew**.
No SDK code is needed: after the customer pays, the server extends `expires_at`
and re-signs the offline payload. The next `validate()` call returns the updated
expiry and refreshes the local cache automatically.

---

## Error Handling

```python
from wplm import WplmExpired, WplmRevoked, WplmLimitExceeded, WplmNetworkError

try:
    wplm.activate()
except WplmLimitExceeded:
    ...  # no seats available
except WplmRevoked:
    ...  # license revoked
except WplmExpired:
    ...  # license expired — prompt renewal
except WplmNetworkError:
    ...  # offline / server unreachable
```

---

## Development

```bash
pip install -e ".[dev]"
ruff check .
mypy --strict src/
pytest
```

---

## Links

- [WP License Manager (server plugin)](https://github.com/thisisfaizi/wp-license-manager)
- [Dart / Flutter SDK](https://github.com/thisisfaizi/wplm-dart)
- [PHP SDK](https://github.com/thisisfaizi/wplm-php)
- [JavaScript / TypeScript SDK](https://github.com/thisisfaizi/wplm-js)
- [OpenAPI 3.1 spec](https://github.com/thisisfaizi/wplm-openapi)

---

<div align="center">

MIT License · Part of the [WP License Manager](https://github.com/thisisfaizi/wp-license-manager) ecosystem

<img src="https://capsule-render.vercel.app/api?type=waving&color=gradient&customColorList=12,18,25&height=80&section=footer" />

</div>
