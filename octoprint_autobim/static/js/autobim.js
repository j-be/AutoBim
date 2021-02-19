/*
 * View model for AutoBim
 *
 * Author: Juri Berlanda
 * License: AGPLv3
 */
$(function () {
    function AutobimViewModel(parameters) {
        var self = this;
        self.settings = parameters[0];

        console.log("AutoBim *ring-ring*");

        self.startAutoBim = function () {
            console.log("AutoBim starting");
            $.ajax({
                url: API_BASEURL + "plugin/autobim",
                type: "POST",
                dataType: "json",
                data: JSON.stringify({
                    command: "start"
                }),
                contentType: "application/json; charset=UTF-8",
                error: function (data, status) {
                    var options = {
                        title: "Autobim failed.",
                        text: data.responseText,
                        hide: true,
                        buttons: {
                            sticker: false,
                            closer: true
                        },
                        type: "error"
                    };

                    new PNotify(options);
                }
            });
        };

        self.onBeforeBinding = function () {
            let autoBimButton = $('#autoBimButton')[0];
            autoBimButton.onclick = self.startAutoBim;
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
