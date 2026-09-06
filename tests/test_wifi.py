"""Mocked Windows WLAN tests; run with uv run python -m unittest discover -s tests -v."""

import ctypes
import importlib.util
from pathlib import Path
import sys
from types import ModuleType
import unittest
from unittest.mock import Mock, patch


def load_plugin():
	stubs = {
		name: ModuleType(name)
		for name in (
			"globalPluginHandler",
			"inputCore",
			"ui",
			"addonHandler",
			"core",
			"logHandler",
		)
	}
	stubs["globalPluginHandler"].GlobalPlugin = type("GlobalPlugin", (), {})
	stubs["inputCore"].InputGesture = object
	stubs["ui"].message = Mock()
	stubs["addonHandler"].initTranslation = Mock()
	stubs["logHandler"].log = Mock()
	path = Path(__file__).resolve().parents[1] / "addon/globalPlugins/nvdaNetworkStatus.py"
	spec = importlib.util.spec_from_file_location("wifi_test_plugin", path)
	module = importlib.util.module_from_spec(spec)
	module._ = lambda text: text
	with patch.dict(sys.modules, stubs):
		spec.loader.exec_module(module)
	return module


plugin = load_plugin()


def set_output(pointer, kind, value):
	ctypes.cast(pointer, ctypes.POINTER(kind))[0] = value


class FakeWlan:
	def __init__(
		self,
		states=(1,),
		quality=73,
		realtime_error=0,
		query_error=0,
		open_error=0,
		enum_error=0,
		malformed=False,
		null_data=False,
		close_error=0,
	):
		self.states = states
		self.quality = quality
		self.realtime_error = realtime_error
		self.query_error = query_error
		self.open_error = open_error
		self.enum_error = enum_error
		self.malformed = malformed
		self.null_data = null_data
		self.close_error = close_error
		self.allocations = {}
		self.freed = []
		self.closed = []
		self.queries = []

	def allocate(self, data, pointer):
		buffer = ctypes.create_string_buffer(data)
		address = ctypes.addressof(buffer)
		self.allocations[address] = buffer
		set_output(pointer, ctypes.c_void_p, address)

	def WlanOpenHandle(self, version, reserved, negotiated, handle):
		if not self.open_error:
			set_output(negotiated, ctypes.wintypes.DWORD, 2)
			set_output(handle, ctypes.wintypes.HANDLE, 123)
		return self.open_error

	def WlanEnumInterfaces(self, handle, reserved, output):
		if self.enum_error:
			return self.enum_error
		header = plugin._WLAN_INTERFACE_INFO_LIST_HEADER()
		header.dwNumberOfItems = len(self.states)
		data = bytes(header)
		for index, state in enumerate(self.states):
			interface = plugin._WLAN_INTERFACE_INFO()
			interface.isState = state
			interface.InterfaceGuid.Data1 = index + 1
			data += bytes(interface)
		self.allocate(data, output)
		return 0

	def WlanQueryInterface(self, handle, guid, opcode, reserved, size, output, value_type):
		interface_id = ctypes.cast(guid, ctypes.POINTER(plugin._GUID)).contents.Data1
		self.queries.append((interface_id, opcode))
		error = self.realtime_error if opcode == 19 else self.query_error
		if error:
			return error
		if opcode == 19:
			result = plugin._WLAN_REALTIME_CONNECTION_QUALITY_HEADER()
			result.ulLinkQuality = self.quality
		else:
			result = plugin._WLAN_CONNECTION_ATTRIBUTES()
			result.isState = 1
			result.wlanAssociationAttributes.wlanSignalQuality = self.quality
		data = bytes(result)
		if not self.null_data:
			self.allocate(data, output)
		set_output(size, ctypes.wintypes.DWORD, 1 if self.malformed else len(data))
		return 0

	def WlanFreeMemory(self, pointer):
		address = pointer.value
		if address in self.freed or address not in self.allocations:
			raise AssertionError("Invalid or duplicate free")
		self.freed.append(address)

	def WlanCloseHandle(self, handle, reserved):
		self.closed.append(handle.value)
		return self.close_error


class WifiTests(unittest.TestCase):
	def announce(self, api):
		with (
			patch.object(plugin, "_loadWlanApi", return_value=api),
			patch.object(plugin, "message") as message,
			patch.object(plugin, "log") as log,
		):
			instance = object.__new__(plugin.GlobalPlugin)
			instance.script_announceNetworkStrength(None)
			self.assertCountEqual(api.freed, api.allocations)
			self.assertEqual(api.closed, [] if api.open_error else [123])
			return message.call_args.args[0], log.exception.called

	def test_connected_percentage_and_boundaries(self):
		for quality in (0, 73, 100):
			with self.subTest(quality=quality):
				api = FakeWlan(quality=quality)
				self.assertEqual(self.announce(api), (f"Wi-Fi signal strength: {quality} percent", False))
				self.assertEqual(api.queries, [(1, 19)])

	def test_no_connected_interfaces(self):
		for states in ((), (4,), (0, 2, 3, 4, 5, 6, 7)):
			with self.subTest(states=states):
				api = FakeWlan(states=states)
				self.assertEqual(self.announce(api), ("Wi-Fi not connected", False))
				self.assertEqual(api.queries, [])

	def test_first_connected_interface(self):
		api = FakeWlan(states=(4, 1, 1))
		self.assertEqual(self.announce(api)[0], "Wi-Fi signal strength: 73 percent")
		self.assertEqual(api.queries, [(2, 19)])

	def test_unsupported_realtime_falls_back(self):
		for error in (50, 87):
			with self.subTest(error=error):
				api = FakeWlan(realtime_error=error)
				self.assertEqual(self.announce(api), ("Wi-Fi signal strength: 73 percent", False))
				self.assertEqual(api.queries, [(1, 19), (1, 7)])

	def test_failures_are_logged_and_announced_with_cleanup(self):
		for options in (
			{"open_error": 1062},
			{"enum_error": 5},
			{"realtime_error": 5},
			{"realtime_error": 50, "query_error": 5},
			{"quality": 101},
			{"malformed": True},
			{"null_data": True},
			{"close_error": 6},
		):
			with self.subTest(options=options):
				api = FakeWlan(**options)
				self.assertEqual(self.announce(api), ("Unable to determine Wi-Fi signal strength", True))
				if options.get("realtime_error") == 5:
					self.assertEqual(api.queries, [(1, 19)])

	def test_disconnect_during_query(self):
		api = FakeWlan(realtime_error=5023)
		self.assertEqual(self.announce(api), ("Wi-Fi not connected", False))

	def test_missing_dll_does_not_crash_command(self):
		with (
			patch.object(plugin, "_loadWlanApi", side_effect=OSError("missing DLL")),
			patch.object(plugin, "message") as message,
			patch.object(plugin, "log") as log,
		):
			object.__new__(plugin.GlobalPlugin).script_announceNetworkStrength(None)
			message.assert_called_once_with("Unable to determine Wi-Fi signal strength")
			log.exception.assert_called_once()

	def test_windows_layouts(self):
		self.assertEqual(ctypes.sizeof(plugin._GUID), 16)
		self.assertEqual(ctypes.sizeof(plugin._WLAN_INTERFACE_INFO), 532)
		self.assertEqual(ctypes.sizeof(plugin._WLAN_INTERFACE_INFO_LIST_HEADER), 8)
		self.assertEqual(ctypes.sizeof(plugin._WLAN_REALTIME_CONNECTION_QUALITY_HEADER), 24)
		self.assertEqual(ctypes.sizeof(plugin._WLAN_ASSOCIATION_ATTRIBUTES), 68)
		self.assertEqual(ctypes.sizeof(plugin._WLAN_CONNECTION_ATTRIBUTES), 604)
		self.assertEqual(plugin._WLAN_ASSOCIATION_ATTRIBUTES.wlanSignalQuality.offset, 56)
		self.assertEqual(plugin._WLAN_CONNECTION_ATTRIBUTES.wlanAssociationAttributes.offset, 520)

	def test_fallback_disconnected_state(self):
		data = plugin._WLAN_CONNECTION_ATTRIBUTES()
		data.isState = 4
		self.assertIsNone(plugin._decodeWifiQuality(bytes(data), 7))

	def test_shortcuts_and_manual_internet_status(self):
		self.assertEqual(
			plugin.GlobalPlugin._GlobalPlugin__gestures,
			{
				"kb:Control+NVDA+n": "announceNetworkStrength",
				"kb:Control+Shift+NVDA+n": "announceInternetStatus",
			},
		)
		for state, expected in (
			(plugin._State.DISCONNECTED, "Network disconnected"),
			(plugin._State.LOCAL, "No Internet access"),
			(plugin._State.INTERNET, "Internet access"),
		):
			with (
				self.subTest(state=state),
				patch.object(plugin, "message") as message,
				patch.object(plugin, "_readWifiSignalQuality") as wifi,
			):
				instance = object.__new__(plugin.GlobalPlugin)
				instance._terminated = False
				instance._state = None
				instance._readState = Mock(return_value=state)
				instance.script_announceInternetStatus(None)
				message.assert_called_once_with(expected)
				self.assertEqual(instance._state, state)
				wifi.assert_not_called()


if __name__ == "__main__":
	unittest.main()
