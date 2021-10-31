import re

from octoprint_autobim.async_command import AsyncCommand, Result


MARLIN_PATTERN = re.compile(r"^Bed X: -?\d+\.\d+ Y: -?\d+\.\d+ Z: (-?\d+\.\d+)$")
KLIPPER_PATTERN = re.compile(r"^// Result is z=(-?\d+\.\d+)$")


class G30Handler(AsyncCommand):
	def __init__(self, printer, settings, logger, ignore_ok=True):
		super(G30Handler, self).__init__()
		self._logger = logger
		self._printer = printer
		self._settings = settings
		self._ok_is_error = not ignore_ok
		self.firmware_type = None
		self.custom_pattern = ""
		self.pattern = None

	def apply_custom_pattern(self, pattern):
		self.pattern = re.compile(pattern)

		self.custom_pattern = pattern
		self.firmware_type = None

		self._logger.info(f"Updated custom pattern.")

	def apply_firmware_pattern(self, new_firmware_type):
		if new_firmware_type == "klipper":
			self.pattern = KLIPPER_PATTERN
			self._logger.info("Updated G30 pattern to Klipper.")

		elif new_firmware_type == "marlin":
			self.pattern = MARLIN_PATTERN
			self._logger.info("Updated G30 pattern to Marlin.")

		else:
			# We try the Marlin pattern by default if the name isn't one we know
			firmware_name = self._printer.firmware_info['name']
			if firmware_name == "Klipper":
				self.pattern = KLIPPER_PATTERN
				self._logger.info("Updated G30 pattern to Klipper as the firmware name is %s", firmware_name)
			else:
				self.pattern = MARLIN_PATTERN
				self._logger.info("Updated G30 pattern to Marlin as the firmware name is %s", firmware_name)

		self.firmware_type = new_firmware_type
		self.custom_pattern = ""

	def update_pattern_if_changed(self):
		new_firmware_type = self._settings.get(["firmware_type"])
		new_custom_pattern = self._settings.get(["g30_regex"])

		self._logger.debug("G30 settings: firmware_type = %s, g30_regex = \"%s\"", new_firmware_type, new_custom_pattern)

		if new_custom_pattern != "" and new_custom_pattern != self.custom_pattern:
			# use custom pattern as it takes precedence
			self.apply_custom_pattern(new_custom_pattern)
		elif new_firmware_type != self.firmware_type:
			# configure pattern based on firmware / firmware choice
			self.apply_firmware_pattern(new_firmware_type)

	def do(self, point, timeout=180):
		self.update_pattern_if_changed()
		self._start(point)
		return self._get(timeout)

	def _start(self, point):
		self._set_running()
		self._printer.commands("G30 X%s Y%s" % point)

	def _handle_internal(self, line):
		if self._ok_is_error and "ok" == line.strip():
			self._register_result(Result.error())
			return

		match = self.pattern.match(line)
		if match:
			self._register_result(Result.of(float(match.group(1))))
			return
