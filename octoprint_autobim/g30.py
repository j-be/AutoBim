import re

from octoprint_autobim.async_command import AsyncCommand, Result


MARLIN_PATTERN = re.compile(r"^Bed X: -?\d+\.\d+ Y: -?\d+\.\d+ Z: (-?\d+\.\d+)$")
KLIPPER_PATTERN = re.compile(r"^// Result is z=(-?\d+\.\d+)$")


class G30Handler(AsyncCommand):
	def __init__(self, printer, settings, ignore_ok=True):
		super(G30Handler, self).__init__()
		self._printer = printer
		self._settings = settings
		self._ok_is_error = not ignore_ok
		self.firmware_type = None
		self.custom_pattern = None
		self.pattern = None

	def update_pattern(self):
		new_custom_pattern = self._settings.get(["g30_regex"])
		if new_custom_pattern != self.custom_pattern and new_custom_pattern.strip() != "":
			self.pattern = re.compile(new_custom_pattern)
			self.custom_pattern = new_custom_pattern
			return

		new_firmware_type = self._settings.get(["firmware_type"])
		if new_firmware_type != self.firmware_type:
			if new_firmware_type == "klipper":
				self.pattern = KLIPPER_PATTERN
			elif new_firmware_type == "marlin":
				self.pattern = MARLIN_PATTERN
			else:
				# We try the Marlin pattern by default if the name isn't one we know
				self.pattern = KLIPPER_PATTERN if self._printer.firmware_info['name'] == "klipper" else MARLIN_PATTERN

			self.firmware_type = new_firmware_type

	def do(self, point, timeout=180):
		self.update_pattern()
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
