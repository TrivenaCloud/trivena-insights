// Copyright (c) 2026, Frappe Technologies Pvt. Ltd. and contributors
// For license information, please see license.txt

trivena.ui.form.on("Insights Table Import Job", {
	refresh(frm) {
		frm.add_custom_button(__("Enqueue"), () => {
			frm.call("enqueue");
		});

		frm.add_custom_button(__("Bulk Enqueue"), () => {
			trivena.prompt(
				{
					fieldname: "run_count",
					fieldtype: "Int",
					label: "Number of Runs",
					reqd: 1,
					default: 1,
				},
				(values) => {
					frm.call("bulk_enqueue", { run_count: values.run_count });

					// Show progress indicator
					trivena.show_progress(
						__("Bulk Enqueue Progress"),
						0,
						values.run_count,
						__("Starting..."),
					);

					// Listen for realtime progress updates
					trivena.realtime.on("bulk_enqueue_progress", (data) => {
						if (data.job === frm.doc.name) {
							trivena.show_progress(
								__("Bulk Enqueue Progress"),
								data.current,
								data.total,
								__("Run {0} of {1}", [
									data.current,
									data.total,
								]),
							);
							if (data.current === data.total) {
								setTimeout(() => trivena.hide_progress(), 1000);
								frm.reload_doc();
							}
						}
					});
				},
				__("Bulk Enqueue Import Job"),
			);
		});
	},
});
