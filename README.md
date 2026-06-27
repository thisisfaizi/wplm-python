# WPLM SDK for Python

[![CI](https://github.com/wplm/wplm-python/actions/workflows/ci.yaml/badge.svg)](https://github.com/wplm/wplm-python/actions/workflows/ci.yaml)
[![PyPI](https://img.shields.io/pypi/v/wplm.svg)](https://pypi.org/project/wplm/)

The official Python client for **[WP License Manager (WPLM)](https://github.com/wplm/wp-license-manager)**.
Validate, activate, and verify software licenses — **online and fully offline** —
from desktop apps (PyQt/Tk), CLIs, scripts, and servers on Windows, macOS, and Linux.

- ✅ `validate` / `activate` / `deactivate` / `heartbeat`
- 🔏 **Offline** Ed25519 signature verification (no network needed)
- 🛡️ Signed CRL check (reject revoked keys offline)
- 🔌 Pluggable HTTP transport, fingerprint provider, and token store
- 🧯 Typed exceptions, retries with backoff, replay/clock-drift protection
- 🏷️ Fully type-hinted (`py.typed`)

## Install

```bash
pip install wplm
```

## Quick start

```python
from wplm import WplmClient

with WplmClient(
    base_url="https://license.vendor.com",
    product_id=42,
    license_key=user_entered_key,
) as wplm:
    wplm.activate()                          # bind this device (consumes a seat)
    result = wplm.validate(offline_ok=True)  # online; offline fallback
    if result.valid:
        ...                                  # unlock pro features
    wplm.heartbeat()                         # keep a floating lease alive
    wplm.deactivate()                        # free the seat on sign-out
```

## Offline verification

`validate(offline_ok=True)` verifies the cached, Ed25519-signed payload locally
and checks it against the cached revocation list — so your app keeps working
without a network, and a revoked key is rejected within your CRL refresh window.

For zero-network offline verification, bundle the public key:

```python
wplm = WplmClient(
    base_url="https://license.vendor.com",
    license_key=key,
    public_key_base64="PASTE FROM GET /wp-json/wplm/v1/public-key",
)
```

## Error handling

```python
from wplm import WplmLimitExceeded, WplmRevoked, WplmNetworkError

try:
    wplm.activate()
except WplmLimitExceeded:
    ...  # no seats available
except WplmRevoked:
    ...  # license revoked
except WplmNetworkError:
    ...  # offline / server unreachable
```

## Custom fingerprint and storage

Implement `FingerprintProvider` and `TokenStore` to bind to hardware ids or use
an OS keyring; pass them to the client. A persisted-UUID fingerprint and a JSON
`FileTokenStore` are provided out of the box.

## License

MIT — see [LICENSE](LICENSE). This SDK ships only the public key; no secrets.
