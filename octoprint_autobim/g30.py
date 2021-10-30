import re

from octoprint_autobim.async_command import AsyncCommand, Result


class G30Handler(AsyncCommand):
	def __init__(self, printer, settings, ignore_ok=True):
		super(G30Handler, self).__init__()
		self._printer = printer
		self._settings = settings
		self._ok_is_error = not ignore_ok
		self.pattern = None

	def update_pattern(self):
		g30_regex = self._settings.get(["g30_regex"])
		self.pattern = re.compile(r"^Bed X: -?\d+\.\d+ Y: -?\d+\.\d+ Z: (-?\d+\.\d+)$") if g30_regex == "marlin" \
			else re.compile(r"^// Result is z=(-?\d+\.\d+)$")

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
