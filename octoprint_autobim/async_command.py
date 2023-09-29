import sys

if sys.version[0] == '2':
	import Queue as queue
else:
	import queue


class Result(object):
	def __init__(self, error, abort, value):
		self.error = error
		self.abort = abort
		self.value = value

	def has_value(self):
		return not self.error and not self.abort and self.value is not None

	@staticmethod
	def error():
		return Result(True, False, None)

	@staticmethod
	def abort():
		return Result(False, True, None)

	@staticmethod
	def of(value):
		return Result(False, False, value)

	@staticmethod
	def no_result():
		return Result(False, False, None)


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
		if not self.__running or not line:
			return
		self._handle_internal(line.strip())

	def _register_result(self, result):
		self.__running = False
		self._flush()
		self.__result.put(result, False)

	def abort(self):
		self.__running = False
		self._flush()
		self.__result.put(Result.abort(), False)

	def _get(self, timeout):
		try:
			return self.__result.get(timeout=timeout)
		except queue.Empty:
			return Result.no_result()
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
