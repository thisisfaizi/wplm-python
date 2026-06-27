"""Pluggable HTTP transport with timeouts and retries."""

from __future__ import annotations

import random
import time
from dataclasses import dataclass
from typing import Protocol, runtime_checkable

import requests

from .errors import WplmNetworkError


@dataclass(frozen=True)
class Response:
    """A raw HTTP response."""

    status_code: int
    body: str


@runtime_checkable
class Transport(Protocol):
    """HTTP transport interface. Inject a custom one for proxies/pinning/tests."""

    def send(
        self,
        method: str,
        url: str,
        headers: dict[str, str] | None = None,
        body: str | None = None,
    ) -> Response:
        ...

    def close(self) -> None:
        ...


class RequestsTransport:
    """Default transport on top of :mod:`requests` with retry + backoff."""

    _RETRYABLE = frozenset({429, 500, 502, 503, 504})

    def __init__(
        self,
        session: requests.Session | None = None,
        timeout: float = 15.0,
        max_retries: int = 2,
    ) -> None:
        self._session = session or requests.Session()
        self.timeout = timeout
        self.max_retries = max_retries

    def send(
        self,
        method: str,
        url: str,
        headers: dict[str, str] | None = None,
        body: str | None = None,
    ) -> Response:
        last_error: object = None

        for attempt in range(self.max_retries + 1):
            if attempt > 0:
                time.sleep(self._backoff(attempt))
            try:
                resp = self._session.request(
                    method,
                    url,
                    headers=headers,
                    data=body,
                    timeout=self.timeout,
                )
            except requests.RequestException as exc:
                last_error = exc
                continue

            if resp.status_code in self._RETRYABLE and attempt < self.max_retries:
                last_error = f"HTTP {resp.status_code}"
                continue

            return Response(resp.status_code, resp.text)

        raise WplmNetworkError(
            f"Request failed after {self.max_retries + 1} attempt(s): {last_error}",
            cause=last_error if isinstance(last_error, BaseException) else None,
        )

    def _backoff(self, attempt: int) -> float:
        base = 0.2 * (1 << (attempt - 1))  # 0.2s, 0.4s, 0.8s, ...
        return base + random.uniform(0, 0.1)

    def close(self) -> None:
        self._session.close()
