import sys

if sys.version[0] == '2':
	import Queue as queue
else:
	import queue


class M503Handler(object):
	def __init__(self, printer):
		self._printer = printer
		self.m503_done = queue.Queue(maxsize=1)
		self.running = False

	def do(self, timeout=5):
		self._start()
		return self._get(timeout)

	def abort(self):
		self.running = False
		self._flush()
		self.m503_done.put(None)

	def handle(self, line):
		if not self.running:
			return

		if "Unknown command:" in line and "M503" in line:
			self.running = False
			self._flush()
			self.m503_done.put(float('nan'))
			return
		if line.startswith("ok"):
			self.running = False
			self._flush()
			self.m503_done.put(False)
			return
		if "Unified Bed Leveling System" in line:
			self.running = False
			self._flush()
			self.m503_done.put(True)
			return

	def _start(self):
		self._flush()
		self.running = True
		self._printer.commands("M503")

	def _get(self, timeout):
		try:
			return self.m503_done.get(timeout=timeout)
		except queue.Empty:
			return float('nan')
		finally:
			self.running = False

	def _flush(self):
		try:
			while not self.m503_done.empty():
				self.m503_done.get_nowait()
		except queue.Empty:
			pass
