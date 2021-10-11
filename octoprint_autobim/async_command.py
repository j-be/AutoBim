import sys

if sys.version[0] == '2':
	import Queue as queue
else:
	import queue


class AsyncCommand(object):
	def __init__(self):
		self.__running = False
		self.__result = queue.Queue(maxsize=1)

	def _handle_internal(self, line):
		raise NotImplementedError()

	def _set_running(self):
		self._flush()
		self.__running = True

	# Do not touch the rest of the implementation

	def handle(self, line):
		if not self.__running:
			return
		self._handle_internal(line)

	def _register_result(self, result):
		self.__running = False
		self._flush()
		self.__result.put(result, False)

	def abort(self):
		self.__running = False
		self._flush()
		self.__result.put(None, False)

	def _get(self, timeout):
		try:
			return self.__result.get(timeout=timeout)
		except queue.Empty:
			return float('nan')
		finally:
			self.__running = False

	def _flush(self):
		try:
			while not self.__result.empty():
				self.__result.get_nowait()
		except queue.Empty:
			pass

	def is_running(self):
		return self.__running
