from octoprint_autobim.async_command import AsyncCommand, Result


class M503Handler(AsyncCommand):
	def __init__(self, printer):
		super(M503Handler, self).__init__()
		self._printer = printer

	def do(self, timeout=5):
		self._start()
		return self._get(timeout)

	def _start(self):
		self._set_running()
		self._printer.commands("M503")

	def _handle_internal(self, line):
		if "Unknown command:" in line and "M503" in line:
			self._register_result(Result.error())
			return
		if line.startswith("ok"):
			self._register_result(Result.of(False))
			return
		if "Unified Bed Leveling System" in line:
			self._register_result(Result.of(True))
			return
