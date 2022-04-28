import re

from octoprint_autobim.async_command import AsyncCommand, Result
from octoprint_autobim.utils import filter_commands


MARLIN_PATTERN = re.compile(r"^Bed X: -?\d+\.\d+ Y: -?\d+\.\d+ Z: (-?\d+\.\d+)$")
KLIPPER_PATTERN = re.compile(r"^// Result is z=(-?\d+\.\d+)$")


class G30Handler(AsyncCommand):
	def __init__(self, printer, settings, logger, ignore_ok=True):
		super(G30Handler, self).__init__()
		self._logger = logger
		self._printer = printer
		self._settings = settings
		self._ok_is_error = not ignore_ok
		self.pattern = None

	def _update_pattern_if_changed(self):
		custom_pattern = self._settings.get(["g30_regex"])
		if custom_pattern:
			if not self.pattern or self.pattern.pattern != custom_pattern:
				self.pattern = re.compile(custom_pattern)
		else:
			firmware_name = self._printer.firmware_info['name']
			if "klipper" in firmware_name.lower():
				self.pattern = KLIPPER_PATTERN
				self._logger.info("Updated G30 pattern to Klipper as the firmware name is %s", firmware_name)
			else:
				self.pattern = MARLIN_PATTERN
				self._logger.info("Updated G30 pattern to Marlin as the firmware name is %s", firmware_name)

	def do(self, point, timeout=180):
		self._start(point)
		return self._get(timeout)

	def _start(self, point):
		self._update_pattern_if_changed()
		self._set_running()
		custom_g30 = filter_commands(self._settings.get(["custom_g30"]))
		if not custom_g30:
			self._printer.commands("G30 X%s Y%s" % point)
		else:
			self._ok_is_error = False
			for command in custom_g30:
				if "X%s Y%s" in command:
					self._intercept_output = True
					self._printer.commands(command % point)
				else:
					self._printer.commands(command)

	def _handle_internal(self, line):
		if self._ok_is_error and "ok" == line.strip():
			self._register_result(Result.error())
			return

		match = self.pattern.match(line)
		if match:
			self._register_result(Result.of(float(match.group(1))))
