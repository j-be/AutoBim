import pytest

from octoprint_autobim import M503Handler
from tests.mocks import MockPrinter


@pytest.fixture
def m503():
	return M503Handler(MockPrinter())


def test_ubl(m503):
	m503._start()
	m503.handle("Unified Bed Leveling System v1.01")
	m503.handle("ok")

	result = m503._get(1)
	assert result.has_value() is True
	assert result.error is False
	assert result.abort is False
	assert result.value is True

	assert m503.is_running() is False


def test_no_ubl(m503):
	m503._start()
	m503.handle("ok")

	result = m503._get(1)
	assert result.has_value() is True
	assert result.error is False
	assert result.abort is False
	assert result.value is False

	assert m503.is_running() is False


def test_failed(m503):
	m503._start()
	m503.handle("Unknown command: M503")

	result = m503._get(1)
	assert result.has_value() is False
	assert result.error is True
	assert result.abort is False
	assert result.value is None

	assert m503.is_running() is False


def test_abort(m503):
	m503._start()
	m503.abort()

	result = m503._get(1)
	assert result.has_value() is False
	assert result.error is False
	assert result.abort is True
	assert result.value is None

	assert m503.is_running() is False


def test_start_flush(m503):
	m503._start()
	m503.handle("ok")

	m503._start()
	m503.handle("Unified Bed Leveling System v1.01")
	m503.handle("ok")

	result = m503._get(1)
	assert result.has_value() is True
	assert result.error is False
	assert result.abort is False
	assert result.value is True

	assert m503.is_running() is False
