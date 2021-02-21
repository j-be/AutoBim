/*
 * View model for AutoBim
 *
 * Author: Juri Berlanda
 * License: AGPLv3
 */
$(function () {
    function AutobimViewModel(parameters) {
        let self = this;
        self.settings = parameters[0];
        self.startButton = null;
        self.abortButton = null;

        console.log("AutoBim *ring-ring*");

        self.startAutoBim = function () {
            console.log("AutoBim starting");
            self.startButton.addClass('hidden');

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
            console.log("Aborting AutoBim");
            self.abortButton.addClass('hidden');

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
                self.abortButton.removeClass('hidden');
            } else if (data.type === "aborted") {
                new PNotify({
                    title: "AutoBim aborted",
                    text: data.message,
                    type: "error",
                });
                self.startButton.removeClass('hidden');
            } else if (data.type === "completed") {
                new PNotify({
                    title: "AutoBim completed",
                    text: "Bed should be horizontal now",
                    type: "success",
                });
                self.startButton.removeClass('hidden');
                self.abortButton.addClass('hidden');
            }
        }

        self.onBeforeBinding = function () {
            self.startButton = $('#startAutoBimButton');
            self.startButton.click(self.startAutoBim);
            self.abortButton = $('#abortAutoBimButton');
            self.abortButton.click(self.abortAutoBim);

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
                    if (data.running)
                        self.abortButton.removeClass('hidden');
                    else
                        self.startButton.removeClass('hidden');
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
        dependencies: [ /* "loginStateViewModel", "settingsViewModel" */],
        // Elements to bind to, e.g. #settings_plugin_autobim, #tab_plugin_autobim, ...
        elements: [ /* ... */]
    });
});
