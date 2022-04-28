import logging
import time

import pytest

from octoprint_autobim.g30 import G30Handler
from tests.mocks import MockPrinter, MockSettings


@pytest.fixture
def g30():
	return G30Handler(MockPrinter(), MockSettings(), logging.getLogger("G30 Handler"), ignore_ok=False)


def test_basic(g30):
	g30._start((1, 2))
	g30.handle("Bed X: 1.0 Y: 2.0 Z: 3.0")

	result = g30._get(1)
	assert result.has_value() is True
	assert result.error is False
	assert result.abort is False
	assert result.value == 3.0

	assert g30.is_running() is False


def test_failed(g30):
	g30._start((1, 2))
	time.sleep(1)

	g30.handle("ok\n")

	result = g30._get(1)
	assert result.has_value() is False
	assert result.error is True
	assert result.abort is False
	assert result.value is None

	assert g30.is_running() is False


def test_double_line(g30):
	g30._start((1, 2))

	g30.handle("Bed X: 1.0 Y: 2.0 Z: 3.0")
	g30.handle("Bed X: 1.0 Y: 2.0 Z: 4.0")

	result = g30._get(1)
	assert result.has_value() is True
	assert result.error is False
	assert result.abort is False
	assert result.value == 3.0

	assert g30.is_running() is False


def test_abort(g30):
	g30._start((1, 2))
	g30.abort()

	result = g30._get(1)
	assert result.has_value() is False
	assert result.error is False
	assert result.abort is True
	assert result.value is None

	assert g30.is_running() is False


def test_start_flush(g30):
	g30._start((1, 2))
	g30.handle("Bed X: 1.0 Y: 2.0 Z: 3.0")

	g30._start((1, 2))
	g30.handle("Bed X: 1.0 Y: 2.0 Z: 4.0")

	result = g30._get(1)
	assert result.has_value() is True
	assert result.error is False
	assert result.abort is False
	assert result.value == 4.0

	assert g30.is_running() is False


def test_pattern_selection(g30):
	printer = g30._printer

	# Default is Marlin
	printer.firmware_info = {"name": ""}
	g30._start((1, 2))
	assert g30.pattern.pattern == "^Bed X: -?\\d+\\.\\d+ Y: -?\\d+\\.\\d+ Z: (-?\\d+\\.\\d+)$"

	# Marlin
	printer.firmware_info = {"name": "Marlin 2.0.9.1"}
	g30._start((1, 2))
	assert g30.pattern.pattern == "^Bed X: -?\\d+\\.\\d+ Y: -?\\d+\\.\\d+ Z: (-?\\d+\\.\\d+)$"

	# Klipper
	printer.firmware_info = {"name": "Klipper"}
	g30._start((1, 2))
	assert g30.pattern.pattern == "^// Result is z=(-?\\d+\\.\\d+)$"


def test_pattern_from_settings(g30):
	settings = g30._settings
	printer = g30._printer

	# Custom pattern takes precedence
	settings.set(["g30_regex"], ".*")
	for firmware in ["Marlin 2.0.9.1", "Klipper", ""]:
		printer.firmware_info = {"name": firmware}
		g30._start((1, 2))
		assert g30.pattern.pattern == ".*"
