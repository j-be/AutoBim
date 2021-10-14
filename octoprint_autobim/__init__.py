# coding=utf-8
from __future__ import absolute_import

import math
import threading
import time

import octoprint.plugin
from flask import jsonify
from flask_login import current_user

from octoprint_autobim.g30 import G30Handler
from octoprint_autobim.m503 import M503Handler


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
		self.g30 = None
		self.m503 = None
		self.handlers = []
		self.running = False

	##~~ StartupPlugin mixin

	def on_after_startup(self):
		self.g30 = G30Handler(self._printer)
		self.m503 = M503Handler(self._printer)
		self.handlers = [
			self.g30,
			self.m503,
		]
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
				displayName="Autobim",
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
		templates = [
			dict(type="settings", custom_bindings=True),
		]
		if self._settings.get_boolean(["button_in_navbar"]):
			templates = templates + [dict(type="navbar", template="autobim_button.jinja2")]
		return templates

	##~~ SimpleApiPlugin mixin

	def get_api_commands(self):
		return dict(
			start=[],
			abort=[],
			status=[],
			home=[],
			test_corner=[],
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
			return jsonify({"running": self.running}), 200
		elif command == "home":
			self._printer.home(["x", "y", "z"])
			return jsonify({}), 200
		elif command == "test_corner":
			thread = threading.Thread(target=self.on_test_point, args=((data['x'], data['y']),))
			thread.start()
			return jsonify({}), 200

	def on_test_point(self, point):
		self._logger.info("Got X%s, Y%s" % point)
		result = self.g30.do(point, 30)
		if math.isnan(result):
			self._plugin_manager.send_plugin_message(
				self._identifier,
				dict(type="error", message="Point X%s Y%s seems to be unreachable!" % point))
		else:
			self._plugin_manager.send_plugin_message(
				self._identifier,
				dict(type="info", message="Point X%s Y%s seems to work fine" % point))

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
			button_in_navbar=True,
			has_ubl=None,
			next_point_delay=0.0,
			first_corner_is_reference=False,
		)

	##~~ Gcode received hook

	def process_gcode(self, _, line, *args, **kwargs):
		try:
			for handler in self.handlers:
				handler.handle(line)
		except Exception as e:
			self._logger.error("Error in process_gcode: %s" % str(e))

		return line

	def _set_ubl_flag(self, value):
		self._settings.set_boolean(["has_ubl"], value)
		self._settings.save(trigger_event=True)

	##~~ AtCommand hook

	def atcommand_handler(self, comm, phase, command, parameters, tags=None, *args, **kwargs):
		if command != "AUTOBIM":
			return
		thread = threading.Thread(target=self.autobim)
		thread.start()

	##~~ Plugin implementation

	def check_state(self):
		if not self._printer.is_operational():
			raise AutoBimError("Can't start AutoBim - printer is not operational!")
		if self._printer.is_printing():
			raise AutoBimError("Can't start AutoBim - printer is printing!")
		if self._settings.get_boolean(["has_ubl"]) is None:
			self._logger.info("Unknown whether UBL or not - checking")
			self._handle_m503_result(self.m503.do())

	def _handle_m503_result(self, result):
		if result is None:
			self._logger.info("'None' from queue means user abort")
			return
		elif math.isnan(result):
			self._plugin_manager.send_plugin_message(self._identifier, dict(
				type="warn",
				message="Cannot determine whether UBL is active or not! Assuming it isn't. If it is, please set it manually in the settings."))
			self._set_ubl_flag(False)
		elif result:
			self._plugin_manager.send_plugin_message(self._identifier, dict(
				type="info",
				message="Seems like UBL system is active! If not, please change the setting."))
			self._set_ubl_flag(True)
		else:
			self._plugin_manager.send_plugin_message(self._identifier, dict(
				type="info",
				message="Seems like no UBL system is active! If so, please change the setting."))
			self._set_ubl_flag(False)

	def autobim(self):
		self.running = True

		self.check_state()

		self._plugin_manager.send_plugin_message(self._identifier, dict(type="started"))

		self._printer.commands("M117 wait...")

		self._printer.home(["x", "y", "z"])
		# Move up to avoid bed collisions
		self._printer.commands("G0 Z20")
		# Jettison saved mesh
		self._clear_saved_mesh()

		changed = True
		threshold = self._settings.get_float(["threshold"])
		multipass = self._settings.get_boolean(["multipass"])
		next_point_delay = self._settings.get_float(["next_point_delay"])

		# Default reference is Z=0
		if self._settings.get_boolean(["first_corner_is_reference"]):
			reference = None
		else:
			reference = 0

		while changed and self.running:
			changed = False
			for index, corner in enumerate(self.get_probe_points()):
				if reference is None:
					self._logger.info("Treating first corner as reference")
					self._printer.commands("M117 Getting reference...")

					reference = self.g30.do(corner)
					if reference is None:
						self._logger.info("'None' from queue means user abort")
						return
					elif math.isnan(reference):
						self.abort_now("Cannot probe X%s Y%s! Please check settings!" % corner)
						return

					self._printer.commands("M117 wait...")
				else:
					delta = 2 * threshold
					while abs(delta) >= threshold and self.running:
						z_current = self.g30.do(corner)

						if z_current is None:
							self._logger.info("'None' from queue means user abort")
							return
						elif math.isnan(z_current):
							self.abort_now("Cannot probe X%s Y%s! Please check settings!" % corner)
							return
						else:
							delta = z_current - reference

						if abs(delta) >= threshold and multipass:
							changed = True
							self._printer.commands("M117 %s" % self.get_message(delta))
						else:
							self._printer.commands("M117 %s" % self.get_message())

					if next_point_delay:
						time.sleep(next_point_delay)

		self._printer.commands("M117 done")
		self.running = False
		self._plugin_manager.send_plugin_message(self._identifier, dict(type="completed"))

	def get_probe_points(self):
		points = self._settings.get(['probe_points'])
		return [(p['x'], p['y']) for p in points]

	def get_message(self, diff=None):
		if not diff:
			return "ok. moving to next"

		invert = self._settings.get_boolean(['invert'])
		if invert ^ (diff < 0):
			msg = "%.2f " % diff + "<<<"
		else:
			msg = "%.2f " % diff + ">>>"
		return msg + " (adjust)"

	def abort_now(self, msg):
		self._logger.error(msg)
		self._printer.commands("M117 %s" % msg)
		self.running = False
		for handler in self.handlers:
			handler.abort()
		self._plugin_manager.send_plugin_message(self._identifier, dict(type="aborted", message=msg))

	def _clear_saved_mesh(self):
		if self._settings.get_boolean(["has_ubl"]):
			self._printer.commands("G29 D")
		else:
			self._printer.commands("G29 J")

__plugin_name__ = "AutoBim"
__plugin_pythoncompat__ = ">=2.7,<4"  # python 2 and 3


def __plugin_load__():
	global __plugin_implementation__
	__plugin_implementation__ = AutobimPlugin()

	global __plugin_hooks__
	__plugin_hooks__ = {
		"octoprint.plugin.softwareupdate.check_config": __plugin_implementation__.get_update_information,
		"octoprint.comm.protocol.gcode.received": __plugin_implementation__.process_gcode,
		"octoprint.comm.protocol.atcommand.queuing": __plugin_implementation__.atcommand_handler,
	}
