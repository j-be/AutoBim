import logging
import threading
from time import sleep

import pytest

from octoprint_autobim.autobim import AutobimPlugin
from tests.mocks import MockPrinter, MockSettings, MockPluginManager


class ThreadWithValue(threading.Thread):
	def __init__(self, fn, args):
		super(ThreadWithValue, self).__init__()
		self.fn = fn
		self.args = args
		self.result = None

	def run(self):
		self.result = self.fn(*self.args)

	def get(self):
		self.join(0)
		return self.result


@pytest.fixture
def plugin():
	plugin = AutobimPlugin()

	settings = MockSettings(plugin.get_settings_defaults())
	settings.set_boolean(["has_ubl"], False)

	logging.basicConfig(level=logging.INFO)
	plugin._identifier = "AutoBim"
	plugin._logger = logging.getLogger("test")
	plugin._plugin_manager = MockPluginManager()
	plugin._printer = MockPrinter()
	plugin._settings = settings

	plugin.on_after_startup()

	return plugin


def test_g30_test(plugin):
	point = (1, 2)

	thread = ThreadWithValue(plugin.on_test_point, (point,))
	thread.start()
	sleep(0.01)

	plugin.process_gcode(None, "Bed X: 1.0 Y: 2.0 Z: 3.0")
	plugin.process_gcode(None, "ok")
	sleep(0.01)

	assert plugin._printer.sent_commands == ['G30 X1 Y2']
	assert {'message': 'Point X1 Y2 seems to work fine', 'type': 'info'} in plugin._plugin_manager.sent_messages

	assert thread.get()


def test_g30_test_fails(plugin):
	point = (1, 2)

	thread = ThreadWithValue(plugin.on_test_point, (point,))
	thread.start()
	sleep(0.01)

	plugin.process_gcode(None, "ok")
	sleep(0.01)

	assert plugin._printer.sent_commands == ['G30 X1 Y2']
	assert {'message': 'Point X1 Y2 seems to be unreachable!', 'type': 'error'} in plugin._plugin_manager.sent_messages

	assert not thread.get()


def test_first_corner_is_reference(plugin):
	plugin._settings.set_boolean(["first_corner_is_reference"], True)

	thread = threading.Thread(target=plugin.autobim)
	thread.start()
	sleep(0.01)

	assert plugin._settings.get_boolean(["first_corner_is_reference"]) is True

	assert plugin._printer.sent_commands == [
		'M117 wait...', "G28 ['x', 'y', 'z']", 'G0 Z20', 'G29 J', 'M117 Getting reference...', 'G30 X30 Y30'
	]
	del plugin._printer.sent_commands[:]

	plugin.process_gcode(None, "Bed X: 1.0 Y: 2.0 Z: 3.0")
	plugin.process_gcode(None, "ok")
	sleep(0.01)

	assert plugin._printer.sent_commands == ['M117 wait...', 'G30 X30 Y200']
	del plugin._printer.sent_commands[:]

	plugin.process_gcode(None, "Bed X: 1.0 Y: 2.0 Z: 2.0")
	plugin.process_gcode(None, "ok")
	sleep(0.01)

	assert plugin._printer.sent_commands == ['M117 -1.00 <<< (adjust)', 'G30 X30 Y200']
	del plugin._printer.sent_commands[:]

	plugin.on_api_command("abort", {})

	assert plugin.running is False

	thread.join(0)


def test_invert_arrows(plugin):
	thread = threading.Thread(target=plugin.autobim)
	thread.start()
	sleep(0.01)

	del plugin._printer.sent_commands[:]
	plugin.process_gcode(None, "Bed X: 1.0 Y: 2.0 Z: 3.0")
	plugin.process_gcode(None, "ok")
	sleep(0.01)

	plugin._settings.set_boolean(["invert"], True)

	assert plugin._printer.sent_commands == ['M117 3.00 >>> (adjust)', 'G30 X30 Y30']
	del plugin._printer.sent_commands[:]

	plugin.process_gcode(None, "Bed X: 1.0 Y: 2.0 Z: 3.0")
	plugin.process_gcode(None, "ok")
	sleep(0.01)

	assert plugin._printer.sent_commands == ['M117 3.00 <<< (adjust)', 'G30 X30 Y30']

	plugin.on_api_command("abort", {})

	assert plugin.running is False

	thread.join(0)


def test_multipass_off(plugin):
	plugin._settings.set_boolean(["multipass"], False)

	thread = threading.Thread(target=plugin.autobim)
	thread.start()
	sleep(0.01)

	for point in plugin.get_probe_points():
		del plugin._printer.sent_commands[:]
		plugin.process_gcode(None, "Bed X: %s.0 Y: %s.0 Z: 3.0" % point)
		plugin.process_gcode(None, "ok")
		sleep(0.01)

		assert plugin._printer.sent_commands == ["M117 3.00 >>> (adjust)", "G30 X%s Y%s" % point]
		plugin.process_gcode(None, "Bed X: %s.0 Y: %s.0 Z: 0.0" % point)
		plugin.process_gcode(None, "ok")
		sleep(0.01)
		assert plugin._printer.sent_commands[2] == "M117 ok. moving to next"

	assert plugin.running is False

	thread.join(0)


def test_multipass_on(plugin):
	plugin._settings.set_boolean(["multipass"], True)

	thread = threading.Thread(target=plugin.autobim)
	thread.start()
	sleep(0.01)

	for point in plugin.get_probe_points():
		del plugin._printer.sent_commands[:]
		plugin.process_gcode(None, "Bed X: %s.0 Y: %s.0 Z: 3.0" % point)
		plugin.process_gcode(None, "ok")
		sleep(0.01)

		assert plugin._printer.sent_commands == ["M117 3.00 >>> (adjust)", "G30 X%s Y%s" % point]
		plugin.process_gcode(None, "Bed X: %s.0 Y: %s.0 Z: 0.0" % point)
		plugin.process_gcode(None, "ok")
		sleep(0.01)
		assert plugin._printer.sent_commands[2] == "M117 ok. moving to next"

	assert plugin.running is True
	plugin.on_api_command("abort", {})

	thread.join(0)


def test_before_gcode(plugin):
	plugin._settings.set_boolean(["before_gcode"], "\tM117 123 \n   \n\t  M117 321\n\t\n")

	thread = threading.Thread(target=plugin.autobim)
	thread.start()
	sleep(0.01)

	assert plugin._printer.sent_commands == [
		'M117 wait...', "G28 ['x', 'y', 'z']", 'G0 Z20', 'G29 J', 'M117 123', 'M117 321', 'G30 X30 Y30'
	]

	plugin.on_api_command("abort", {})
	thread.join(0)


def test_after_gcode_abort(plugin):
	plugin._settings.set_boolean(["after_gcode"], "\tM117 123 \n   \n\t  M117 321\n\t\n")

	thread = threading.Thread(target=plugin.autobim)
	thread.start()
	sleep(0.01)

	del plugin._printer.sent_commands[:]

	plugin.on_api_command("abort", {})
	thread.join(0)

	assert plugin._printer.sent_commands == ['M117 Aborted by user', 'M117 123', 'M117 321']


def test_after_gcode_success(plugin):
	plugin._settings.set_boolean(["after_gcode"], "\tM117 123 \n   \n\t  M117 321\n\t\n")

	thread = threading.Thread(target=plugin.autobim)
	thread.start()
	sleep(0.01)

	for point in plugin.get_probe_points():
		del plugin._printer.sent_commands[:]
		plugin.process_gcode(None, "Bed X: %s.0 Y: %s.0 Z: 0.0" % point)
		plugin.process_gcode(None, "ok")
		sleep(0.01)

	assert plugin.running is False
	assert plugin._printer.sent_commands[-2:] == ['M117 123', 'M117 321']

	thread.join(0)


def test_all_in_a_row(plugin):
	plugin._settings.set_boolean(["multipass"], True)

	thread = threading.Thread(target=plugin.autobim)
	thread.start()
	sleep(0.01)

	point = plugin.get_probe_points()[0]
	for delta in [3, 0]:
		plugin.process_gcode(None, "Bed X: %s.0 Y: %s.0 Z: %s.0" % (point[0], point[1], delta))
		plugin.process_gcode(None, "ok")
		sleep(0.01)

	for point in plugin.get_probe_points()[1:]:
		assert plugin._printer.sent_commands[-1] == "G30 X%s Y%s" % point
		plugin.process_gcode(None, "Bed X: %s.0 Y: %s.0 Z: 0.0" % point)
		plugin.process_gcode(None, "ok")
		sleep(0.01)
		assert plugin._printer.sent_commands[-2] == "M117 ok. moving to next"

	assert plugin.running is False
	assert plugin._printer.sent_commands[-1] == "M117 done"

	thread.join(0)


def test_at_command(plugin):
	assert plugin.running is False
	plugin.atcommand_handler(None, None, "AUTOBIM", None)
	sleep(0.01)

	assert plugin.running is True
	plugin.on_api_command("abort", {})
	sleep(0.01)

	assert plugin.running is False


def test_only_one_running(plugin):
	assert plugin.running is False

	plugin.atcommand_handler(None, None, "AUTOBIM", None)
	sleep(0.01)

	assert plugin.running is True

	thread = threading.Thread(target=plugin.autobim)
	thread.start()
	sleep(0.01)

	assert thread.is_alive() is False
	assert plugin.running is True

	plugin.on_api_command("abort", {})
	sleep(0.01)

	assert plugin.running is False


def test_show_in_navbar(plugin):
	plugin._settings.set_boolean(["button_in_navbar"], True)
	assert plugin.get_template_configs() == [
		dict(type="settings", custom_bindings=True),
		dict(type="navbar", template="autobim_button.jinja2"),
	]
	plugin._settings.set_boolean(["button_in_navbar"], False)
	assert plugin.get_template_configs() == [dict(type="settings", custom_bindings=True)]


def test_next_point_delay(plugin):
	plugin._settings.set(["next_point_delay"], 0.1)

	thread = threading.Thread(target=plugin.autobim)
	thread.start()
	sleep(0.01)

	point = plugin.get_probe_points()[0]
	assert plugin._printer.sent_commands[-1] == "G30 X%s Y%s" % point
	plugin.process_gcode(None, "Bed X: %s.0 Y: %s.0 Z: 0.0" % point)
	plugin.process_gcode(None, "ok")
	sleep(0.01)
	assert plugin._printer.sent_commands[-1] == "M117 ok. moving to next"
	del plugin._printer.sent_commands[:]

	for point in plugin.get_probe_points()[1:]:
		assert plugin._printer.sent_commands == []
		sleep(0.2)
		assert plugin._printer.sent_commands[-1] == "G30 X%s Y%s" % point
		plugin.process_gcode(None, "Bed X: %s.0 Y: %s.0 Z: 0.0" % point)
		plugin.process_gcode(None, "ok")
		sleep(0.1)
		assert plugin._printer.sent_commands[-1] == "M117 ok. moving to next"
		del plugin._printer.sent_commands[:]


def test_test_points(plugin):
	thread = ThreadWithValue(plugin.on_test_points, ([{'x': 1, 'y': 2}, {'x': 2, 'y': 3}],))
	thread.start()
	sleep(0.01)

	plugin.process_gcode(None, "Bed X: 1.0 Y: 2.0 Z: 3.0")
	plugin.process_gcode(None, "ok")
	sleep(0.01)

	plugin.process_gcode(None, "ok")
	sleep(0.01)

	assert plugin._printer.sent_commands == ['G30 X1 Y2', 'G30 X2 Y3']
	assert plugin._plugin_manager.sent_messages == [
		{'message': 'Point X1 Y2 seems to work fine', 'type': 'info'},
		{'message': 'Point X2 Y3 seems to be unreachable!', 'type': 'error'},
	]

	x = thread.get()
	assert x == {'results': [
		{'point': {'x': 1, 'y': 2}, 'result': True},
		{'point': {'x': 2, 'y': 3}, 'result': False},
	]}


def test_repeat_on_error(plugin):
	thread = threading.Thread(target=plugin.autobim)
	thread.start()
	sleep(0.01)

	del plugin._printer.sent_commands[:]
	plugin.process_gcode(None, "Bed X: 1.0 Y: 2.0 Z: 0.0")
	plugin.process_gcode(None, "ok")
	sleep(0.01)

	assert plugin._printer.sent_commands == ['M117 ok. moving to next', 'G30 X30 Y200']
	del plugin._printer.sent_commands[:]

	# Try 3 times in total (1 above, 2 in here)
	for i in range(2):
		plugin.process_gcode(None, "Error:Probing Failed")
		sleep(0.01)

		assert plugin._printer.sent_commands == ['M117 Error, retrying X30 Y200', 'G30 X30 Y200']
		del plugin._printer.sent_commands[:]

	plugin.process_gcode(None, "Error:Probing Failed")
	sleep(0.01)

	assert plugin._printer.sent_commands == ['M117 Cannot probe X30 Y200! Please check settings!']
	assert not plugin.running
	thread.join(1)


def test_delay_between_porbes(plugin):
	plugin._settings.set(["next_probe_delay"], 0.1)

	thread = threading.Thread(target=plugin.autobim)
	thread.start()
	sleep(0.01)
	point = plugin.get_probe_points()[0]

	# Delay on adjust
	assert plugin._printer.sent_commands[-1] == "G30 X%s Y%s" % point
	del plugin._printer.sent_commands[:]
	plugin.process_gcode(None, "Bed X: %s.0 Y: %s.0 Z: 1.0" % point)
	plugin.process_gcode(None, "ok")
	sleep(0.02)
	assert plugin._printer.sent_commands == ['M117 1.00 >>> (adjust)']
	sleep(0.1)
	assert len(plugin._printer.sent_commands) == 2
	assert plugin._printer.sent_commands[1] == "G30 X%s Y%s" % point
	del plugin._printer.sent_commands[:]

	# No delay on ok
	plugin.process_gcode(None, "Bed X: %s.0 Y: %s.0 Z: 0.0" % point)
	plugin.process_gcode(None, "ok")
	sleep(0.01)
	assert plugin._printer.sent_commands[0] == 'M117 ok. moving to next'
