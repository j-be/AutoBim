/*
 * View model for AutoBim
 *
 * Author: Juri Berlanda
 * License: AGPLv3
 */
$(function () {
    function AutobimViewModel(parameters) {
        let self = this;
        self.connection = parameters[0];
        self.settings = parameters[1];
        self.autoBimRunning = ko.observable(false);
        self.probeResults = ko.observableArray();
        self.probes = ko.observable(0);
        self.probes.result = function (point) {
            return ko.pureComputed(function() {
                let found = self.probeResults().find(result => result.point.x == point.x && result.point.y == point.y);
                if (found) {
                    return found.result ? 'Ok' : 'Not ok';
                }
                return '';
            }, this)
        }.bind(self.probes);

        console.log("AutoBim *ring-ring*");

        self.startAutoBim = function () {
            $.ajax({
                url: API_BASEURL + "plugin/autobim",
                type: "POST",
                dataType: "json",
                data: JSON.stringify({
                    command: "start"
                }),
                contentType: "application/json; charset=UTF-8",
                error: function (data, _) {
                    new PNotify({
                        title: "Autobim failed.",
                        text: data.responseText,
                        hide: true,
                        type: "error"
                    });
                }
            });
        };

        self.abortAutoBim = function () {
            $.ajax({
                url: API_BASEURL + "plugin/autobim",
                type: "POST",
                dataType: "json",
                data: JSON.stringify({
                    command: "abort"
                }),
                contentType: "application/json; charset=UTF-8",
                error: function (data, _) {
                    new PNotify({
                        title: "Autobim failed.",
                        text: data.responseText,
                        type: "error"
                    });
                }
            });
        };

        self.home = function () {
            $.ajax({
                url: API_BASEURL + "plugin/autobim",
                type: "POST",
                dataType: "json",
                data: JSON.stringify({
                    command: "home"
                }),
                contentType: "application/json; charset=UTF-8",
                error: function (data, _) {
                    new PNotify({
                        title: "Homing failed.",
                        text: data.responseText,
                        type: "error"
                    });
                }
            });
        }

        self.testCorner = function (corner) {
            $.ajax({
                url: API_BASEURL + "plugin/autobim",
                type: "POST",
                dataType: "json",
                data: JSON.stringify({
                    command: "test_corner",
                    x: corner.x(),
                    y: corner.y()
                }),
                contentType: "application/json; charset=UTF-8",
                error: function (data, _) {
                    new PNotify({
                        title: "Testing failed.",
                        text: data.responseText,
                        type: "error"
                    });
                }
            });
        }

        self.testAllCorners = function () {
            console.log(self.settings.settings.plugins.autobim.probe_points())
            $.ajax({
                url: API_BASEURL + "plugin/autobim",
                type: "POST",
                dataType: "json",
                data: JSON.stringify({
                    command: "test_all_corners",
                    points: self.settings.settings.plugins.autobim.probe_points()
                                .map(observable => ({
                                    x: observable.x(),
                                    y: observable.y(),
                                })),
                }),
                contentType: "application/json; charset=UTF-8",
                error: function (data, _) {
                    new PNotify({
                        title: "Testing failed.",
                        text: data.responseText,
                        type: "error"
                    });
                },
                success: function (data, _) {
                    self.probeResults(data.results);
                }
            });
        }

        self.addCorner = function(_) {
            self.settings.settings.plugins.autobim.probe_points.push({x: '0', y: '0'});
        }

        self.removeCorner = function(_) {
            self.settings.settings.plugins.autobim.probe_points.pop();
        }

        /* OctoPrint Hooks */

        self.onDataUpdaterPluginMessage = function(plugin, data) {
            if (plugin !== "autobim")
                return;
            if (data.type === "started") {
                new PNotify({
                    title: "AutoBim started",
                    text: "Please look at the printer's screen",
                    type: "success",
                });
                self.autoBimRunning(true);
            } else if (data.type === "aborted") {
                new PNotify({
                    title: "AutoBim aborted",
                    text: data.message,
                    type: "error",
                });
                self.autoBimRunning(false);
            } else if (data.type === "completed") {
                new PNotify({
                    title: "AutoBim completed",
                    text: "Bed should be horizontal now",
                    type: "success",
                });
                self.autoBimRunning(false);
            } else if (data.message) {
                new PNotify({
                    title: "AutoBim",
                    text: data.message,
                    type: data.type,
                });
            }
        }

        self.onBeforeBinding = function () {
            $.ajax({
                url: API_BASEURL + "plugin/autobim",
                type: "POST",
                dataType: "json",
                data: JSON.stringify({
                    command: "status"
                }),
                contentType: "application/json; charset=UTF-8",
                error: function (data, _) {
                    new PNotify({
                        title: "Autobim initialization failed.",
                        text: data.responseText,
                        type: "error"
                    });
                },
                success: function (data) {
                    self.autoBimRunning(data.running);
                }
            });
        };
    }

    /* view model class, parameters for constructor, container to bind to
     * Please see http://docs.octoprint.org/en/master/plugins/viewmodels.html#registering-custom-viewmodels for more details
     * and a full list of the available options.
     */
    OCTOPRINT_VIEWMODELS.push({
        construct: AutobimViewModel,
        // ViewModels your plugin depends on, e.g. loginStateViewModel, settingsViewModel, ...
        dependencies: [ "connectionViewModel", "settingsViewModel" ],
        // Elements to bind to, e.g. #settings_plugin_autobim, #tab_plugin_autobim, ...
        elements: [ "#navbar_plugin_autobim", "#settings_plugin_autobim" ]
    });
});
