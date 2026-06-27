# Security Policy

## Reporting a vulnerability

Report security issues privately to **security@wplm.dev** or via a GitHub
security advisory. Do not open public issues for vulnerabilities.

## Design guarantees

- This SDK ships **only the Ed25519 public key, product id, and server URL** —
  never the signing private key or any API consumer secret.
- License payloads are verified with Ed25519 detached signatures; tampered
  tokens raise `WplmSignatureInvalid`.
- Replay protection rejects cached payloads whose issue time drifts beyond a
  configurable window (default 5 minutes).
- TLS verification is on by default; pinning is possible via a custom transport.
- Secrets and fingerprints are never logged.
