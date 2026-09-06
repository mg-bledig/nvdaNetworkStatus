# coding=UTF-8
# NVDA Network Status
# Maintained by Mike Bledig
# Based on the original networkStrenght add-on by Rui Fontes
# Original copyright 2020 Rui Fontes
# Modifications/continuation copyright 2026 Mike Bledig

import globalPluginHandler
import inputCore
import subprocess
from ui import message
import addonHandler
from enum import Enum, auto
from importlib import import_module
from typing import Protocol, cast, override
from collections.abc import Callable
import core
from logHandler import log

addonHandler.initTranslation()


class _NetworkListManager(Protocol):
	def GetConnectivity(self) -> int: ...


class _CreateObject(Protocol):
	def __call__(self, progid: str, *, dynamic: bool) -> _NetworkListManager: ...


class _Timer(Protocol):
	def Stop(self) -> None: ...


class _State(Enum):
	DISCONNECTED = auto()
	LOCAL = auto()
	INTERNET = auto()


def _statusText(state: _State) -> str:
	if state is _State.DISCONNECTED:
		return _("Network disconnected")
	if state is _State.INTERNET:
		return _("Internet access")
	return _("No Internet access")


class GlobalPlugin(globalPluginHandler.GlobalPlugin):
	def __init__(self) -> None:
		super().__init__()
		self._terminated = False
		self._state: _State | None = None
		self._nlm: _NetworkListManager | None = None
		self._timer: _Timer | None = None
		self._poll()

	def _readState(self) -> _State | None:
		try:
			if self._nlm is None:
				# NVDA supplies comtypes. Describe its dynamic dispatch interface locally.
				createObject = cast(_CreateObject, import_module("comtypes.client").CreateObject)
				self._nlm = createObject("{DCB00C01-570F-4A9B-8D69-199FDBA5723B}", dynamic=True)
			connectivity = int(self._nlm.GetConnectivity())
		except Exception:
			log.exception("Unable to query Windows Network List Manager")  # pyright: ignore[reportUnknownMemberType]
			self._nlm = None
			return None
		if connectivity == 0:
			return _State.DISCONNECTED
		if connectivity & 0x440:
			return _State.INTERNET
		return _State.LOCAL

	def _poll(self) -> None:
		# core.callLater can already have queued this callback when Stop is called.
		if self._terminated:
			return
		try:
			state = self._readState()
			if state is not None:
				previous = self._state
				self._state = state
				if previous is not None and state is not previous:
					if state is _State.INTERNET:
						message(_("Internet access restored"))
					else:
						message(_statusText(state))
		finally:
			if not self._terminated:
				# NVDA's callLater has no annotations; calls here always run on the main thread.
				callLater = cast(Callable[[int, Callable[[], None]], _Timer], core.callLater)  # pyright: ignore[reportUnknownMemberType]
				self._timer = callLater(5000, self._poll)

	@override
	def terminate(self) -> None:
		self._terminated = True
		if self._timer is not None:
			self._timer.Stop()
			self._timer = None
		self._nlm = None
		super().terminate()

	def script_announceInternetStatus(self, gesture: inputCore.InputGesture) -> None:
		if self._terminated:
			return
		state = self._readState()
		if state is not None:
			# A manual reading can establish the first silent monitoring baseline.
			if self._state is None:
				self._state = state
			message(_statusText(state))

	def script_announceNetworkStrength(self, gesture: inputCore.InputGesture) -> None:
		results = subprocess.check_output(["netsh", "wlan", "show", "network", "mode=Bssid"])
		ns = str(results[results.find(b"%") - 3 : results.find(b"%") + 1])
		message(str(_("Strength of signal is: ") + ns[2:]))

	#: Now defining a dictionary with key bindings for this plugin
	__gestures = {
		"kb:Control+NVDA+n": "announceNetworkStrength",
		"kb:Control+Shift+NVDA+n": "announceInternetStatus",
	}
