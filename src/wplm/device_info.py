"""Device metadata sent to the server on activate/heartbeat.

Identifies each seat in the vendor dashboard. The field names mirror the WPLM
``machines`` columns; values are host-appropriate (a server/desktop, not a
handset). Implement :class:`DeviceInfoProvider` to customise, or use the
default :class:`LocalDeviceInfoProvider`.
"""

from __future__ import annotations

import platform as _platform
import socket
from dataclasses import dataclass
from typing import Protocol, runtime_checkable


@dataclass(frozen=True)
class WplmDeviceInfo:
    """Human-readable metadata about the current device."""

    name: str | None = None
    hostname: str | None = None
    platform: str | None = None
    app_version: str | None = None


@runtime_checkable
class DeviceInfoProvider(Protocol):
    """Supplies :class:`WplmDeviceInfo` for the current device."""

    def get(self) -> WplmDeviceInfo:
        ...


class LocalDeviceInfoProvider:
    """Default provider: derives info from the host machine.

    ``name``/``hostname`` come from the hostname; ``platform`` combines the OS
    and Python version.
    """

    def __init__(self, app_version: str | None = None) -> None:
        self._app_version = app_version

    def get(self) -> WplmDeviceInfo:
        host = socket.gethostname()
        return WplmDeviceInfo(
            name=host,
            hostname=host,
            platform=(
                f"{_platform.system()} {_platform.release()} "
                f"· Python {_platform.python_version()}"
            ).strip(),
            app_version=self._app_version,
        )
