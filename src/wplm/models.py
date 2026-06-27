"""Immutable data models mirroring the WPLM server responses."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Any


def _as_int(value: Any) -> int | None:
    return int(value) if isinstance(value, (int, float)) else None


def _as_dt(value: Any) -> datetime | None:
    if isinstance(value, str) and value:
        try:
            return datetime.fromisoformat(value.replace("Z", "+00:00"))
        except ValueError:
            return None
    return None


@dataclass(frozen=True)
class License:
    """A WPLM license, as returned by ``/validate``."""

    id: int
    status: int
    status_label: str
    activation_count: int
    is_floating: bool
    overage_strategy: str
    grace_days: int
    source: int
    product_id: int | None = None
    order_id: int | None = None
    user_id: int | None = None
    max_activations: int | None = None
    valid_for_days: int | None = None
    activated_at: datetime | None = None
    expires_at: datetime | None = None
    created_at: datetime | None = None
    updated_at: datetime | None = None

    @classmethod
    def from_json(cls, data: dict[str, Any]) -> License:
        return cls(
            id=_as_int(data.get("id")) or 0,
            status=_as_int(data.get("status")) or 0,
            status_label=str(data.get("status_label") or ""),
            activation_count=_as_int(data.get("activation_count")) or 0,
            is_floating=data.get("is_floating") in (True, 1),
            overage_strategy=str(data.get("overage_strategy") or "deny"),
            grace_days=_as_int(data.get("grace_days")) or 0,
            source=_as_int(data.get("source")) or 0,
            product_id=_as_int(data.get("product_id")),
            order_id=_as_int(data.get("order_id")),
            user_id=_as_int(data.get("user_id")),
            max_activations=_as_int(data.get("max_activations")),
            valid_for_days=_as_int(data.get("valid_for_days")),
            activated_at=_as_dt(data.get("activated_at")),
            expires_at=_as_dt(data.get("expires_at")),
            created_at=_as_dt(data.get("created_at")),
            updated_at=_as_dt(data.get("updated_at")),
        )

    @property
    def is_active(self) -> bool:
        return self.status == 1


@dataclass(frozen=True)
class Machine:
    """A device bound to a license, as returned by ``/activate`` / ``/heartbeat``."""

    id: int
    license_id: int
    fingerprint: str
    status: int
    name: str | None = None
    hostname: str | None = None
    platform: str | None = None
    app_version: str | None = None
    lease_expires_at: datetime | None = None
    last_heartbeat_at: datetime | None = None
    activated_at: datetime | None = None

    @classmethod
    def from_json(cls, data: dict[str, Any]) -> Machine:
        return cls(
            id=_as_int(data.get("id")) or 0,
            license_id=_as_int(data.get("license_id")) or 0,
            fingerprint=str(data.get("fingerprint") or ""),
            status=_as_int(data.get("status")) or 1,
            name=data.get("name"),
            hostname=data.get("hostname"),
            platform=data.get("platform"),
            app_version=data.get("app_version"),
            lease_expires_at=_as_dt(data.get("lease_expires_at")),
            last_heartbeat_at=_as_dt(data.get("last_heartbeat_at")),
            activated_at=_as_dt(data.get("activated_at")),
        )

    @property
    def is_active(self) -> bool:
        return self.status == 1


@dataclass(frozen=True)
class ValidationResult:
    """The outcome of :meth:`WplmClient.validate`."""

    valid: bool
    code: str | None = None
    license: License | None = None
    signed_payload: str | None = None
    needs_activation: bool = False
    from_cache: bool = False

    @classmethod
    def from_json(
        cls,
        data: dict[str, Any],
        *,
        from_cache: bool = False,
    ) -> ValidationResult:
        lic = data.get("license")
        return cls(
            valid=data.get("valid") is True,
            code=data.get("code"),
            license=License.from_json(lic) if isinstance(lic, dict) else None,
            signed_payload=data.get("signed_payload"),
            needs_activation=data.get("needs_activation") is True,
            from_cache=from_cache,
        )
