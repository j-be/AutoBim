# coding=utf-8
from __future__ import absolute_import

import threading
import time

import octoprint.plugin
from flask import jsonify
from flask_login import current_user

from octoprint_autobim.g30 import G30Handler
from octoprint_autobim.m503 import M503Handler
from octoprint_autobim.utils import filter_commands


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
		self.g30_tester = None
		self.m503 = None
		self.handlers = []
		self.running = False

	##~~ StartupPlugin mixin

	def on_after_startup(self):
		self.g30 = G30Handler(self._printer, self._settings, self._logger)
		self.g30_tester = G30Handler(self._printer, self._settings, self._logger, False)
		self.m503 = M503Handler(self._printer)

		self.handlers = [
			self.g30,
			self.g30_tester,
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
			test_all_corners=[],
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
			self._abort_now("Aborted by user")
		elif command == "status":
			return jsonify({"running": self.running}), 200
		elif command == "home":
			self._printer.home(["x", "y", "z"])
			return jsonify({}), 200
		elif command == "test_corner":
			thread = threading.Thread(target=self.on_test_point, args=((data['x'], data['y']),))
			thread.start()
			return jsonify({}), 200
		elif command == "test_all_corners":
			return jsonify(self.on_test_points(data['points'])), 200

	def on_test_point(self, point):
		self._logger.info("Got X%s, Y%s" % point)
		result = self.g30_tester.do(point, 30)
		if result.has_value():
			self._plugin_manager.send_plugin_message(
				self._identifier,
				dict(type="info", message="Point X%s Y%s seems to work fine" % point))
		else:
			self._plugin_manager.send_plugin_message(
				self._identifier,
				dict(type="error", message="Point X%s Y%s seems to be unreachable!" % point))
		return result.has_value()

	def on_test_points(self, point_list):
		results = []
		self._logger.info("PointList: %s" % str(point_list))
		for point in point_list:
			results.append({
				'point': point,
				'result': self.on_test_point((point['x'], point['y'])),
			})
		return {'results': results}

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
			g30_regex="",
			before_gcode=None,
			after_gcode=None,
		)

	##~~ Gcode received hook

	def process_gcode(self, _, line, *args, **kwargs):
		try:
			for handler in self.handlers:
				handler.handle(line)
		except Exception as e:
			self._logger.error("Error in process_gcode: %s" % str(e))

		return line

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
		if result.abort:
			self._logger.info("'None' from queue means user abort")
		elif not result.has_value:
			self._plugin_manager.send_plugin_message(self._identifier, dict(
				type="warn",
				message="Cannot determine whether UBL is active or not! Assuming it isn't. If it is, please set it manually in the settings."))
			self._set_ubl_flag(False)
		elif result.value is True:
			self._plugin_manager.send_plugin_message(self._identifier, dict(
				type="info",
				message="Seems like UBL system is active! If not, please change the setting."))
			self._set_ubl_flag(True)
		else:
			self._plugin_manager.send_plugin_message(self._identifier, dict(
				type="info",
				message="Seems like no UBL system is active! If so, please change the setting."))
			self._set_ubl_flag(False)

	def _set_ubl_flag(self, value):
		self._settings.set_boolean(["has_ubl"], value)
		self._settings.save(trigger_event=True)

	def autobim(self):
		if self.running:
			return

		self.running = True

		self.check_state()

		self._plugin_manager.send_plugin_message(self._identifier, dict(type="started"))

		self._printer.commands("M117 wait...")

		self._printer.home(["x", "y", "z"])
		# Move up to avoid bed collisions
		self._printer.commands("G0 Z20")
		# Jettison saved mesh
		self._clear_saved_mesh()

		# Custom GCode
		before_gcode = self._settings.get(["before_gcode"])
		if before_gcode:
			self._printer.commands(filter_commands(before_gcode))

		threshold = self._settings.get_float(["threshold"])
		multipass = self._settings.get_boolean(["multipass"])
		next_point_delay = self._settings.get_float(["next_point_delay"])

		# Default reference is Z=0
		reference = 0
		corner_index = 0
		correct_corners = 0

		if self._settings.get_boolean(["first_corner_is_reference"]):
			self._logger.info("Treating first corner as reference")
			self._printer.commands("M117 Getting reference...")

			result = self._probe_point(self.get_probe_points()[0])
			if not result.has_value():
				return

			reference = result.value
			corner_index = 1
			correct_corners = 1
			self._printer.commands("M117 wait...")

		while correct_corners < len(self.get_probe_points()) and self.running:
			corner = self.get_probe_points()[corner_index]
			corner_index = (corner_index + 1) % len(self.get_probe_points())

			delta = 2 * threshold
			while abs(delta) >= threshold and self.running:

				z_current = self._probe_point(corner)
				if not z_current.has_value():
					return

				delta = z_current.value - reference
				if abs(delta) >= threshold:
					if multipass:
						correct_corners = 0
					self._printer.commands("M117 %s" % self._get_message(delta))
				else:
					self._printer.commands("M117 %s" % self._get_message())

			correct_corners += 1
			if next_point_delay:
				time.sleep(next_point_delay)

		self._printer.commands("M117 done")
		self.running = False

		# Custom GCode
		after_gcode = self._settings.get(["after_gcode"])
		if after_gcode:
			self._printer.commands(filter_commands(after_gcode))

		self._plugin_manager.send_plugin_message(self._identifier, dict(type="completed"))

	def get_probe_points(self):
		points = self._settings.get(['probe_points'])
		return [(p['x'], p['y']) for p in points]

	def _get_message(self, diff=None):
		if not diff:
			return "ok. moving to next"

		invert = self._settings.get_boolean(['invert'])
		if invert ^ (diff < 0):
			msg = "%.2f " % diff + "<<<"
		else:
			msg = "%.2f " % diff + ">>>"
		return msg + " (adjust)"

	def _abort_now(self, msg):
		self._logger.error(msg)
		self._printer.commands("M117 %s" % msg)
		self.running = False
		for handler in self.handlers:
			handler.abort()

		# Custom GCode
		after_gcode = self._settings.get(["after_gcode"])
		if after_gcode:
			self._printer.commands(filter_commands(after_gcode))

		self._plugin_manager.send_plugin_message(self._identifier, dict(type="aborted", message=msg))

	def _clear_saved_mesh(self):
		if self._settings.get_boolean(["has_ubl"]):
			self._printer.commands("G29 D")
		else:
			self._printer.commands("G29 J")

	def _probe_point(self, point, max_tries=3):
		result = None
		counter = 0

		while counter < max_tries:
			counter += 1
			result = self.g30.do(point)
			if result.has_value() or result.abort:
				return result
			if counter < max_tries:
				self._printer.commands("M117 Error, retrying X%s Y%s" % point)

		if result and not result.has_value():
			self._abort_now("Cannot probe X%s Y%s! Please check settings!" % point)
		return result
