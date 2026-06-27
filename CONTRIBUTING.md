# Contributing

```bash
python -m venv .venv && . .venv/bin/activate   # Windows: .venv\Scripts\activate
pip install -e ".[dev]"

ruff check .
mypy src
pytest
```

All three must pass before a PR is merged; CI enforces them across supported
Python versions.

## Guidelines

- Keep the public API small, fully type-hinted, and documented.
- Never log license keys, fingerprints, or tokens.
- Add tests for every behaviour, including offline / revoked / failure paths.
- Update `CHANGELOG.md` under an "Unreleased" heading.
