# coding=UTF-8
# NVDA Network Status
# Maintained by Mike Bledig
# Based on the original networkStrenght add-on by Rui Fontes
# Original copyright 2020 Rui Fontes
# Modifications/continuation copyright 2026 Mike Bledig

import globalPluginHandler
import inputCore
import ctypes
from ctypes import wintypes
from ui import message
import addonHandler
from enum import Enum, auto
from importlib import import_module
from typing import Protocol, cast, override
from collections.abc import Callable
import core
from logHandler import log

addonHandler.initTranslation()


# Native layouts from wlanapi.h. DWORD/enums/BOOL are 32-bit on both Windows architectures.
_WLAN_CONNECTED = 1
_CURRENT_CONNECTION = 7
_REALTIME_CONNECTION_QUALITY = 19
# Older Windows versions can reject the newer opcode with either error.
_UNSUPPORTED_OPCODE_ERRORS = (50, 87)  # ERROR_NOT_SUPPORTED, ERROR_INVALID_PARAMETER


class _GUID(ctypes.Structure):
	_fields_ = [
		("Data1", wintypes.DWORD),
		("Data2", wintypes.WORD),
		("Data3", wintypes.WORD),
		("Data4", wintypes.BYTE * 8),
	]


class _WLAN_INTERFACE_INFO(ctypes.Structure):
	InterfaceGuid: _GUID  # pyright: ignore[reportUninitializedInstanceVariable]  # Initialized by ctypes.
	isState: int  # pyright: ignore[reportUninitializedInstanceVariable]  # Initialized by ctypes.
	_fields_ = [
		("InterfaceGuid", _GUID),
		("strInterfaceDescription", wintypes.WCHAR * 256),
		("isState", wintypes.DWORD),
	]


class _WLAN_INTERFACE_INFO_LIST_HEADER(ctypes.Structure):
	dwNumberOfItems: int  # pyright: ignore[reportUninitializedInstanceVariable]  # Initialized by ctypes.
	_fields_ = [("dwNumberOfItems", wintypes.DWORD), ("dwIndex", wintypes.DWORD)]


class _WLAN_REALTIME_CONNECTION_QUALITY_HEADER(ctypes.Structure):
	# Only the fixed header is needed; the variable linksInfo array is never accessed.
	ulLinkQuality: int  # pyright: ignore[reportUninitializedInstanceVariable]  # Initialized by ctypes.
	_fields_ = [
		("dot11PhyType", wintypes.DWORD),
		("ulLinkQuality", wintypes.ULONG),
		("ulRxRate", wintypes.ULONG),
		("ulTxRate", wintypes.ULONG),
		("bIsMLOConnection", wintypes.BOOL),
		("ulNumLinks", wintypes.ULONG),
	]


class _DOT11_SSID(ctypes.Structure):
	_fields_ = [("uSSIDLength", wintypes.ULONG), ("ucSSID", wintypes.BYTE * 32)]


class _WLAN_ASSOCIATION_ATTRIBUTES(ctypes.Structure):
	wlanSignalQuality: int  # pyright: ignore[reportUninitializedInstanceVariable]  # Initialized by ctypes.
	_fields_ = [
		("dot11Ssid", _DOT11_SSID),
		("dot11BssType", wintypes.DWORD),
		("dot11Bssid", wintypes.BYTE * 6),
		("dot11PhyType", wintypes.DWORD),
		("uDot11PhyIndex", wintypes.ULONG),
		("wlanSignalQuality", wintypes.ULONG),
		("ulRxRate", wintypes.ULONG),
		("ulTxRate", wintypes.ULONG),
	]


class _WLAN_SECURITY_ATTRIBUTES(ctypes.Structure):
	_fields_ = [
		("bSecurityEnabled", wintypes.BOOL),
		("bOneXEnabled", wintypes.BOOL),
		("dot11AuthAlgorithm", wintypes.DWORD),
		("dot11CipherAlgorithm", wintypes.DWORD),
	]


class _WLAN_CONNECTION_ATTRIBUTES(ctypes.Structure):
	isState: int  # pyright: ignore[reportUninitializedInstanceVariable]  # Initialized by ctypes.
	wlanAssociationAttributes: _WLAN_ASSOCIATION_ATTRIBUTES  # pyright: ignore[reportUninitializedInstanceVariable]  # Initialized by ctypes.
	_fields_ = [
		("isState", wintypes.DWORD),
		("wlanConnectionMode", wintypes.DWORD),
		("strProfileName", wintypes.WCHAR * 256),
		("wlanAssociationAttributes", _WLAN_ASSOCIATION_ATTRIBUTES),
		("wlanSecurityAttributes", _WLAN_SECURITY_ATTRIBUTES),
	]


def _loadWlanApi() -> ctypes.WinDLL:
	# Lazy loading keeps a missing DLL from preventing the global plugin from loading.
	api = ctypes.WinDLL("wlanapi.dll", winmode=0x00000800)  # LOAD_LIBRARY_SEARCH_SYSTEM32
	api.WlanOpenHandle.argtypes = [
		wintypes.DWORD,
		ctypes.c_void_p,
		ctypes.POINTER(wintypes.DWORD),
		ctypes.POINTER(wintypes.HANDLE),
	]
	api.WlanOpenHandle.restype = wintypes.DWORD
	api.WlanEnumInterfaces.argtypes = [wintypes.HANDLE, ctypes.c_void_p, ctypes.POINTER(ctypes.c_void_p)]
	api.WlanEnumInterfaces.restype = wintypes.DWORD
	api.WlanQueryInterface.argtypes = [
		wintypes.HANDLE,
		ctypes.POINTER(_GUID),
		wintypes.DWORD,
		ctypes.c_void_p,
		ctypes.POINTER(wintypes.DWORD),
		ctypes.POINTER(ctypes.c_void_p),
		ctypes.POINTER(wintypes.DWORD),
	]
	api.WlanQueryInterface.restype = wintypes.DWORD
	api.WlanFreeMemory.argtypes = [ctypes.c_void_p]
	api.WlanFreeMemory.restype = None
	api.WlanCloseHandle.argtypes = [wintypes.HANDLE, ctypes.c_void_p]
	api.WlanCloseHandle.restype = wintypes.DWORD
	return api


def _checkWlanResult(result: int, operation: str) -> None:
	if result:
		raise OSError(result, f"{operation} failed with Windows error {result}")


def _decodeWifiQuality(data: bytes, opcode: int) -> int | None:
	if opcode == _REALTIME_CONNECTION_QUALITY:
		quality = _WLAN_REALTIME_CONNECTION_QUALITY_HEADER.from_buffer_copy(data).ulLinkQuality
	else:
		connection = _WLAN_CONNECTION_ATTRIBUTES.from_buffer_copy(data)
		if connection.isState != _WLAN_CONNECTED:
			return None
		quality = connection.wlanAssociationAttributes.wlanSignalQuality
	if not 0 <= quality <= 100:
		raise ValueError(f"Invalid WLAN signal quality: {quality}")
	return quality


def _queryWifiQuality(api: ctypes.WinDLL, handle: wintypes.HANDLE, guid: _GUID) -> int | None:
	for opcode in (_REALTIME_CONNECTION_QUALITY, _CURRENT_CONNECTION):
		data = ctypes.c_void_p()
		size = wintypes.DWORD()
		try:
			result = api.WlanQueryInterface(
				handle,
				ctypes.byref(guid),
				opcode,
				None,
				ctypes.byref(size),
				ctypes.byref(data),
				None,
			)
			if opcode == _REALTIME_CONNECTION_QUALITY and result in _UNSUPPORTED_OPCODE_ERRORS:
				continue
			if result == 5023:  # ERROR_INVALID_STATE: disconnected since enumeration.
				return None
			_checkWlanResult(result, "WlanQueryInterface")
			layout = (
				_WLAN_REALTIME_CONNECTION_QUALITY_HEADER
				if opcode == _REALTIME_CONNECTION_QUALITY
				else _WLAN_CONNECTION_ATTRIBUTES
			)
			if not data.value or size.value < ctypes.sizeof(layout):
				raise ValueError("WlanQueryInterface returned missing or truncated data")
			return _decodeWifiQuality(ctypes.string_at(data, ctypes.sizeof(layout)), opcode)
		finally:
			if data.value:
				api.WlanFreeMemory(data)
	return None


def _readWifiSignalQuality() -> int | None:
	api = _loadWlanApi()
	handle = wintypes.HANDLE()
	version = wintypes.DWORD()
	_checkWlanResult(
		api.WlanOpenHandle(2, None, ctypes.byref(version), ctypes.byref(handle)),
		"WlanOpenHandle",
	)
	try:
		interfaces = ctypes.c_void_p()
		try:
			_checkWlanResult(
				api.WlanEnumInterfaces(handle, None, ctypes.byref(interfaces)),
				"WlanEnumInterfaces",
			)
			if not interfaces.value:
				raise ValueError("WlanEnumInterfaces returned no interface list")
			header = _WLAN_INTERFACE_INFO_LIST_HEADER.from_address(interfaces.value)
			start = interfaces.value + ctypes.sizeof(_WLAN_INTERFACE_INFO_LIST_HEADER)
			for index in range(header.dwNumberOfItems):
				interface = _WLAN_INTERFACE_INFO.from_address(
					start + index * ctypes.sizeof(_WLAN_INTERFACE_INFO),
				)
				if interface.isState == _WLAN_CONNECTED:
					return _queryWifiQuality(api, handle, interface.InterfaceGuid)
			return None
		finally:
			if interfaces.value:
				api.WlanFreeMemory(interfaces)
	finally:
		_checkWlanResult(api.WlanCloseHandle(handle, None), "WlanCloseHandle")


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
		try:
			quality = _readWifiSignalQuality()
		except Exception:
			log.exception("Unable to query Windows WLAN signal quality")  # pyright: ignore[reportUnknownMemberType]
			# Translators: Wi-Fi signal strength could not be read.
			message(_("Unable to determine Wi-Fi signal strength"))
			return
		if quality is None:
			# Translators: No wireless interface is currently connected.
			message(_("Wi-Fi not connected"))
		else:
			# Translators: {quality} is the Wi-Fi signal strength, from 0 to 100.
			message(_("Wi-Fi signal strength: {quality} percent").format(quality=quality))

	#: Now defining a dictionary with key bindings for this plugin
	__gestures = {
		"kb:Control+NVDA+n": "announceNetworkStrength",
		"kb:Control+Shift+NVDA+n": "announceInternetStatus",
	}
