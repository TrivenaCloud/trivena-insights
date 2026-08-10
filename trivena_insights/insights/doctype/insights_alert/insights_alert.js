// Copyright (c) 2023, Frappe Technologies Pvt. Ltd. and contributors
// For license information, please see license.txt

trivena.ui.form.on("Insights Alert", {
	refresh: function (frm) {
		frm.add_custom_button(__("Send Alert"), function () {
			trivena.dom.freeze(__("Sending Alert..."));
			frm.call("send_alert")
				.then(() => {
					trivena.dom.unfreeze();
					trivena.show_alert({
						message: __("Alert sent"),
						indicator: "green",
					});
				})
				.catch(() => {
					trivena.dom.unfreeze();
				});
		});
	},
});
