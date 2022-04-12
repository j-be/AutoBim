import logging

from octoprint_autobim.autobim import AutobimPlugin


class MockPrinter(object):
	def __init__(self):
		self._logger = logging.getLogger("MockPrinter")

		self.sent_commands = []
		self.__operational = True
		self.__printing = False
		self.firmware_info = {"name": "Marlin 2.0.9.2"}

	def commands(self, commands):
		self._logger.info("Got command %s" % str(commands))
		if isinstance(commands, list):
			self.sent_commands.extend(commands)
		else:
			self.sent_commands.append(commands)

	def is_operational(self):
		return self.__operational

	def is_printing(self):
		return self.__printing

	def home(self, axis):
		self.commands("G28 %s" % str(axis))


class MockSettings(object):
	def __init__(self, settings=None):
		if settings is None:
			settings = AutobimPlugin().get_settings_defaults()
		self.__settings = settings

	def get(self, key):
		assert len(key) == 1
		if key[0] in self.__settings:
			return self.__settings[key[0]]
		return None

	def get_float(self, key):
		return self.get(key)

	def get_boolean(self, key):
		return self.get(key)

	def set(self, key, value):
		assert len(key) == 1
		self.__settings[key[0]] = value

	def set_boolean(self, key, value):
		self.set(key, value)

	def save(self, *args, **kwargs):
		pass


class MockPluginManager(object):
	def __init__(self):
		self.sent_messages = []

	def send_plugin_message(self, _, msg):
		self.sent_messages.append(msg)
