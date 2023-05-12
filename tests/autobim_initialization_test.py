import logging
import threading
from time import sleep

import pytest

from octoprint_autobim.autobim import AutobimPlugin
from tests.mocks import MockPrinter, MockSettings, MockPluginManager


@pytest.fixture
def plugin():
	plugin = AutobimPlugin()

	settings = MockSettings(plugin.get_settings_defaults())

	logging.basicConfig(level=logging.INFO)
	plugin._identifier = "AutoBim"
	plugin._logger = logging.getLogger()
	plugin._plugin_manager = MockPluginManager()
	plugin._printer = MockPrinter()
	plugin._settings = settings

	plugin.on_after_startup()

	return plugin


def test_autobim_abort_rightaway(plugin):
	thread = threading.Thread(target=plugin.autobim)
	thread.start()
	sleep(0.01)

	assert plugin.running is True

	plugin.on_api_command("abort", {})

	assert plugin.running is False

	thread.join(0)


def test_autobim_ubl(plugin):
	thread = threading.Thread(target=plugin.autobim)
	thread.start()
	sleep(0.01)

	plugin.process_gcode(None, "Unified Bed Leveling System v1.01")
	plugin.process_gcode(None, "ok")

	sleep(0.01)
	assert plugin._settings.get_boolean(["has_ubl"]) is True

	assert plugin._printer.sent_commands == ['M503', 'M117 wait...', "G28 ['x', 'y', 'z']", 'G0 Z20', 'G29 D','G30 X30 Y30']

	plugin.on_api_command("abort", {})

	assert plugin.running is False

	thread.join(0)


def test_autobim_no_ubl(plugin):
	thread = threading.Thread(target=plugin.autobim)
	thread.start()
	sleep(0.01)

	plugin.process_gcode(None, "ok")
	sleep(0.01)

	assert plugin._settings.get_boolean(["has_ubl"]) is False
	assert plugin._settings.get_boolean(["first_corner_is_reference"]) is False

	assert plugin._printer.sent_commands == ['M503', 'M117 wait...', "G28 ['x', 'y', 'z']", 'G0 Z20', 'G29 J','G30 X30 Y30']

	del plugin._printer.sent_commands[:]
	plugin.process_gcode(None, "Bed X: 1.0 Y: 2.0 Z: 3.0")
	plugin.process_gcode(None, "ok")
	sleep(0.01)

	assert plugin._printer.sent_commands == ['M117 3.00 >>> (adjust)', 'G30 X30 Y30']
	del plugin._printer.sent_commands[:]

	plugin.process_gcode(None, "Bed X: 1.0 Y: 2.0 Z: -0.015")
	plugin.process_gcode(None, "ok")
	sleep(0.01)

	assert plugin._printer.sent_commands == ['M117 -0.01 <<< (adjust)', 'G30 X30 Y30']
	del plugin._printer.sent_commands[:]

	plugin.on_api_command("abort", {})

	assert plugin.running is False

	thread.join(0)
