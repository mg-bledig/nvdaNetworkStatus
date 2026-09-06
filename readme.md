# NVDA Network Status

NVDA Network Status reports network and Internet connectivity status and wireless signal strength.

* Version: 1.0
* Maintainer: Michael Bledig
* Repository: https://github.com/mg-bledig/nvdaNetworkStatus

## Compatibility

Requires NVDA 2026.1 or later.
Tested with NVDA 2026.2.

## Current behavior

* Automatically announces "Network disconnected" when network connectivity is lost.
* Announces "No Internet access" when the local network remains connected but Internet access is lost.
* Announces "Internet access restored" when Internet connectivity returns.
* NVDA+Control+Shift+N reports the current Internet status manually.
* NVDA+Control+N reports connected Wi-Fi signal strength.

Wi-Fi signal strength uses the native Windows WLAN API instead of parsing netsh output.

## Attribution / History

Rui Fontes created the original "networkStrenght" NVDA add-on in 2020, first released on 18 March 2020. The original project provided wireless signal-strength reporting.

NVDA Network Status is a continuation/derivative maintained by Michael Bledig, based in part on Rui's original work, with added Internet connectivity monitoring. Rui retains clear credit and copyright for his original work.

* Original copyright 2020 Rui Fontes.
* Modifications/continuation copyright 2026 Michael Bledig.

## Changes

### Version 1.0

Initial NVDA Network Status release, based on Rui Fontes' original networkStrenght add-on. Adds automatic Internet connectivity change announcements, a manual Internet status command, and connected Wi-Fi signal strength reporting using the native Windows WLAN API.

## License

See [COPYING.txt](COPYING.txt) for the unchanged license terms.
