# coding=utf-8
from __future__ import absolute_import

import queue
import re

import octoprint.plugin
from flask_login import current_user
from octoprint.printer import PrinterCallback


QUEUE_TIMEOUT = 60


class AutoBimError(Exception):

	def __init__(self, message):
		super(AutoBimError, self).__init__(message)
		self.message = message


class LogParser(PrinterCallback):

	def __init__(self, z_values, pattern=r"^Bed X: -?\d+\.\d+ Y: -?\d+\.\d+ Z: (-?\d+\.\d+)$", logger=None):
		self.z_values = z_values
		self.pattern = pattern
		self.logger = logger

	def on_printer_add_log(self, data):
		self.on_printer_message("on_printer_add_log", data)

	def on_printer_add_message(self, data):
		self.on_printer_message("on_printer_add_message", data)

	def on_printer_add_temperature(self, data):
		self.on_printer_message("on_printer_add_temperature", str(data))

	def on_printer_send_initial_data(self, data):
		self.on_printer_message("on_printer_send_initial_data", str(data))

	def on_printer_send_current_data(self, data):
		self.on_printer_message("on_printer_send_current_data", str(data))

	def on_printer_message(self, fn, data):
		self.log("%s: Got data '%s'" % (fn, data))
		match = re.compile(self.pattern).match(data)
		if match:
			z_value = float(match.group(1))
			self.log("Match! Adding to queue: '%f'" % z_value)
			self.z_values.put(z_value)

	def on_printer_received_registered_message(self, name, output):
		self.log("Got registered message name='%s', output='%s'" % (name, output))

	def log(self, msg):
		if self.logger:
			self.logger.info(msg)


class AutobimPlugin(
	octoprint.plugin.StartupPlugin,
	octoprint.plugin.AssetPlugin,
	octoprint.plugin.TemplatePlugin,
	octoprint.plugin.SimpleApiPlugin,
):

	def __init__(self):
		super(AutobimPlugin, self).__init__()
		self.z_values = queue.Queue(maxsize=1)
		self.log_parser = None

	##~~ StartupPlugin mixin

	def on_after_startup(self):
		self._logger.info("AutoBim *ring-ring*")

	##~~ AssetPlugin mixin

	def get_assets(self):
		# Define your plugin's asset files to automatically include in the
		# core UI here.
		return dict(
			js=["js/autobim.js"],
		)

	##~~ Softwareupdate hook

	def get_update_information(self):
		# Define the configuration for your plugin to use with the Software Update
		# Plugin here. See https://docs.octoprint.org/en/master/bundledplugins/softwareupdate.html
		# for details.
		return dict(
			autobim=dict(
				displayName="Autobim Plugin",
				displayVersion=self._plugin_version,

				# version check: github repository
				type="github_release",
				user="j-be",
				repo="AutoBim",
				current=self._plugin_version,

				# update method: pip
				pip="https://github.com/j-be/AutoBim/archive/{target_version}.zip"
			)
		)

	##~~ SimpleApiPlugin mixin

	def get_api_commands(self):
		return dict(
			start=[]
		)

	def on_api_command(self, command, data):
		if command == "start":
			if current_user.is_anonymous():
				return "Insufficient rights", 403
			try:
				self.autobim()
			except AutoBimError as error:
				self._logger.info("AutoBim error: " + str(error.message))
				return str(error.message), 405

	##~~ Gcode received hook
	def process_gcode(self, comm, line, *args, **kwargs):
		self._logger.info("process_gcode - Line: '%s' Comm: '%s'" % (comm, line))
		return line

	##~~ Plugin implementation

	def check_state(self):
		if not self._printer.is_operational() or self._printer.is_printing():
			raise AutoBimError("Can't set the temperature because the printer is not ready.")

	def autobim(self):
		self.check_state()

		self.log_parser = LogParser(self.z_values, logger=self._logger)
		self._printer.register_callback(self.log_parser)
		self._printer.commands("M117 wait...")

		self._printer.home(["x", "y", "z"])
		# Jettison saved mesh
		self._printer.commands("G29 J")
		# TODO: Use bed geometry
		self._printer.commands("G30 X115 Y115")
		try:
			self._logger.info("Waiting for center Z...")
			z_center = self.z_values.get(timeout=QUEUE_TIMEOUT)
		except queue.Empty:
			self.abort("Cannot get center Z")
			return

		if not z_center:
			self.abort("Cannot determine Z value for center")
			return

		# TODO: Use from settings
		for corner in [(30, 30), (200, 30), (200, 200), (30, 200)]:
			z_current = None
			while z_current != z_center:
				self._printer.commands("G30 X%d Y%d" % corner)
				try:
					z_current = self.z_values.get(timeout=QUEUE_TIMEOUT)
				except queue.Empty:
					self.abort("Cannot get corner Z for corner %s" % str(corner))
					return

				self._printer.commands("M117 %s" % self.get_message(z_current - z_center))

		self._printer.commands("done")
		self._printer.unregister_callback(self.log_parser)

	def get_message(self, diff):
		def get_count():
			return min(abs(int(diff / 0.1)) + 1, 5)

		if diff < 0:
			return ">" * get_count()
		elif diff < 0:
			return "<" * get_count()
		return "|"

	def abort(self, msg):
		self._logger.error(msg)
		self._printer.commands("M117 %s" % msg)
		self._printer.unregister_callback(self.log_parser)

__plugin_name__ = "AutoBim"
__plugin_pythoncompat__ = ">=2.7,<4"  # python 2 and 3


def __plugin_load__():
	global __plugin_implementation__
	__plugin_implementation__ = AutobimPlugin()

	global __plugin_hooks__
	__plugin_hooks__ = {
		"octoprint.plugin.softwareupdate.check_config": __plugin_implementation__.get_update_information,
		"octoprint.comm.protocol.gcode.received": __plugin_implementation__.process_gcode,
	}

if __name__ == "__main__":
	q = queue.Queue(maxsize=1)
	l = LogParser(q)
	l.on_printer_add_message("Bed X: 115.00 Y: 115.00 Z: 0.00")
	print(q.get(timeout=0))
