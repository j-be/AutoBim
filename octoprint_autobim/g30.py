import re
import sys

if sys.version[0] == '2':
	import Queue as queue
else:
	import queue


class G30Handler(object):
	def __init__(self, printer):
		self._printer = printer
		self.z_values = queue.Queue(maxsize=1)
		self.running = False
		# TODO: Move pattern to settings
		self.pattern = re.compile(r"^Bed X: -?\d+\.\d+ Y: -?\d+\.\d+ Z: (-?\d+\.\d+)$")

	def do(self, point, timeout=180):
		self._start(point)
		return self._get(timeout)

	def abort(self):
		self.z_values.put(None)

	def handle(self, line):
		if not self.running:
			return

		if "ok" == line:
			self.z_values.put(float("nan"))
			return

		match = self.pattern.match(line)
		if match:
			z_value = float(match.group(1))
			self.z_values.put(z_value)

	def _start(self, point):
		self._flush()
		self.running = True
		self._printer.commands("G30 X%s Y%s" % point)

	def _get(self, timeout):
		try:
			return self.z_values.get(timeout=timeout)
		except queue.Empty:
			return float('nan')
		finally:
			self.running = False

	def _flush(self):
		try:
			while not self.z_values.empty():
				self.z_values.get_nowait()
		except queue.Empty:
			pass
