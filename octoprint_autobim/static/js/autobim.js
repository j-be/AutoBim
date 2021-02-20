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
            self.abortButton.removeClass('hidden');

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
                        buttons: {
                            sticker: false,
                            closer: true
                        },
                        type: "error"
                    });
                }
            });
        };

        self.abortAutoBim = function () {
            console.log("Aborting AutoBim");
            self.startButton.removeClass('hidden');
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
                        hide: true,
                        buttons: {
                            sticker: false,
                            closer: true
                        },
                        type: "error"
                    });
                }
            });
        };

        self.onBeforeBinding = function () {
            self.startButton = $('#startAutoBimButton');
            self.startButton.click(self.startAutoBim);
            self.abortButton = $('#abortAutoBimButton');
            self.abortButton.click(self.abortAutoBim);
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
