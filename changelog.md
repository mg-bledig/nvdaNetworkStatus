# NVDA Network Status 1.0

Initial standalone release of NVDA Network Status, based on Rui Fontes' original networkStrenght add-on.

## Highlights

- Automatically announces when network connectivity is disconnected.
- Announces when the local network remains connected but Internet access is unavailable.
- Announces when Internet access is restored.
- NVDA+Control+Shift+N reports current Internet connectivity status.
- NVDA+Control+N reports connected Wi-Fi signal strength.
- Wi-Fi signal strength uses the native Windows WLAN API instead of parsing netsh output.
- Includes automated Windows unit tests for WLAN behavior.

## Compatibility

- Requires NVDA 2026.1 or later.
- Tested with NVDA 2026.2.

## Attribution

- Original networkStrenght add-on: Rui Fontes, 2020.
- NVDA Network Status continuation and modifications: Michael Bledig, 2026.
