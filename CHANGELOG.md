# Changelog

All notable changes to the WPLM Python SDK are documented here.
The format follows [Keep a Changelog](https://keepachangelog.com/en/1.0.0/) and
this project adheres to [Semantic Versioning](https://semver.org/).

## [0.2.0] - 2026-06-28

### Added
- **Product binding.** Set `product_id` and the client rejects any license whose
  signed `pid` does not match — enforced both online and offline from the
  cryptographically signed payload (`WplmProductMismatch`). Omit `product_id` to
  opt out (backward compatible).
- **Keypair-rotation self-heal.** If the cached public key fails verification
  during an online `validate`, the SDK drops it, re-fetches `/public-key` once,
  and retries — so a vendor rotating the signing keypair no longer bricks clients.

## [0.1.0] - 2026-06-18

### Added
- Initial release.
- `WplmClient` with `validate`, `activate`, `deactivate`, and `heartbeat`.
- Offline Ed25519 verification of the signed license payload (PyNaCl).
- Offline-capable validation (`validate(offline_ok=True)`) with configurable
  clock-drift / replay protection.
- Signed CRL fetch + verification + offline revoked-key check.
- Pluggable transport (retries + backoff), fingerprint provider, and token store.
- Typed exception hierarchy mapping every server error code.
- Fully type-hinted (`py.typed`).
