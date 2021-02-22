# coding=utf-8
from __future__ import absolute_import

import queue
import threading
import re

import octoprint.plugin
from flask_login import current_user


QUEUE_TIMEOUT = 180


class AutoBimError(Exception):

	def __init__(self, message):
		super(AutoBimError, self).__init__(message)
		self.message = message


class AutobimPlugin(
	octoprint.plugin.StartupPlugin,
	octoprint.plugin.AssetPlugin,
	octoprint.plugin.TemplatePlugin,
	octoprint.plugin.SimpleApiPlugin,
	octoprint.plugin.SettingsPlugin,
):

	def __init__(self):
		super(AutobimPlugin, self).__init__()
		self.z_values = queue.Queue(maxsize=1)
		# TODO: Move pattern to settings
		self.pattern = re.compile(r"^Bed X: -?\d+\.\d+ Y: -?\d+\.\d+ Z: (-?\d+\.\d+)$")
		self.running = False

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

	##~~ TemplatePlugin mixin

	def get_template_configs(self):
		return [
			dict(type="settings", custom_bindings=False)
		]

	##~~ SimpleApiPlugin mixin

	def get_api_commands(self):
		return dict(
			start=[],
			abort=[],
			status=[],
		)

	def on_api_command(self, command, data):
		if command == "start":
			if current_user.is_anonymous():
				return "Insufficient rights", 403
			if self.running:
				return "Already running", 400
			self._logger.info("Starting")
			thread = threading.Thread(target=self.autobim)
			thread.start()
		elif command == "abort":
			self.abort_now("Aborted by user")
		elif command == "status":
			return dict(running=self.running), 200

	##~~ SettingsPlugin mixin

	def get_settings_defaults(self):
		return dict(
			probe_points=[
				dict(x="30", y="30"),
				dict(x="30", y="200"),
				dict(x="200", y="200"),
				dict(x="200", y="30"),
			],
			invert=False,
			multipass=True,
			threshold=0.01,
		)

	##~~ Gcode received hook

	def process_gcode(self, _, line, *args, **kwargs):
		if not self.running:
			return line

		try:
			match = self.pattern.match(line)
			if match:
				z_value = float(match.group(1))
				self.z_values.put(z_value)
		except Exception as e:
			self._logger.error("Error in process_gcode: %s" % str(e))
		return line

	##~~ Plugin implementation

	def check_state(self):
		if not self._printer.is_operational() or self._printer.is_printing():
			raise AutoBimError("Can't set the temperature because the printer is not ready.")

	def autobim(self):
		self.check_state()
		self._plugin_manager.send_plugin_message(self._identifier, dict(type="started"))

		self._printer.commands("M117 wait...")

		self._printer.home(["x", "y", "z"])
		# Move up to avoid bed collisions
		self._printer.commands("G0 Z20")
		# Jettison saved mesh
		self._printer.commands("G29 J")

		self.running = True
		changed = True
		threshold = self._settings.get_boolean(["threshold"])
		multipass = self._settings.get_boolean(["multipass"])

		while changed and self.running:
			changed = False
			for corner in self.get_probe_points():
				z_current = 1
				while z_current >= threshold and self.running:
					self._printer.commands("G30 X%s Y%s" % corner)
					try:
						z_current = self.z_values.get(timeout=QUEUE_TIMEOUT)
					except queue.Empty:
						self.abort_now("Cannot get Z for corner %s" % str(corner))
						return
					if z_current is None:
						self._logger.info("'None' from queue means user abort")
						return

					if z_current >= threshold and multipass:
						changed = True
					self._printer.commands("M117 %s" % self.get_message(z_current))

		self._printer.commands("M117 done")
		self.running = False
		self._plugin_manager.send_plugin_message(self._identifier, dict(type="completed"))

	def get_probe_points(self):
		points = self._settings.get(['probe_points'])
		return [(p['x'], p['y']) for p in points]

	def get_message(self, diff):
		def get_count():
			return min(abs(int(diff / 0.025)) + 1, 5)

		if not diff:
			return "ok. moving to next"

		invert = self._settings.get_boolean(['invert'])
		if invert ^ (diff < 0):
			return "%.2f " % diff + "<" * get_count()
		return "%.2f " % diff + ">" * get_count()

	def abort_now(self, msg):
		self._logger.error(msg)
		self._printer.commands("M117 %s" % msg)
		self.running = False
		self.z_values.put(None)
		self._plugin_manager.send_plugin_message(self._identifier, dict(type="aborted", message=msg))


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
