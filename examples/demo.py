"""A runnable command-line demo of the WPLM Python SDK.

Usage:
    python examples/demo.py <server-url> <license-key>
"""

from __future__ import annotations

import sys

from wplm import WplmClient, WplmError, WplmLimitExceeded, WplmNetworkError, WplmRevoked


def main() -> None:
    if len(sys.argv) < 3:
        print("Usage: python examples/demo.py <server-url> <license-key>")
        return

    with WplmClient(base_url=sys.argv[1], license_key=sys.argv[2]) as wplm:
        try:
            print("-> Activating this device...")
            machine = wplm.activate(name="CLI demo", platform="python", app_version="1.0.0")
            print(f"   activated machine #{machine.id} (status {machine.status})")

            print("-> Validating (offline-capable)...")
            result = wplm.validate(offline_ok=True)
            print(
                f"   valid={result.valid} "
                f"status={result.license.status_label if result.license else '-'} "
                f"from_cache={result.from_cache}"
            )

            print("-> Heartbeat...")
            wplm.heartbeat(app_version="1.0.0")
            print("   ok")

            print("-> Deactivating...")
            print(f"   deactivated={wplm.deactivate()}")
        except WplmRevoked:
            print("   license is revoked.")
        except WplmLimitExceeded:
            print("   no activation seats available.")
        except WplmNetworkError as exc:
            print(f"   network error: {exc.message}")
        except WplmError as exc:
            print(f"   {exc.code or 'error'}: {exc.message}")


if __name__ == "__main__":
    main()
