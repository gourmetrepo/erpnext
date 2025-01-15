// Copyright (c) 2018, Frappe Technologies Pvt. Ltd. and contributors
// For license information, please see license.txt

frappe.ui.form.on('Shift Request', {
    setup: function(frm) {
		frappe.db.get_list("Employee", {
			filters: { 'user_id': frappe.session.user},
			fields: ["department"]
		}).then((data) => {
			if(data.length > 0){																																								
				var departments = frappe.utils.get_config_by_name("SHIFT_REQUEST_RESTRICTED_DEPARTMENTS", []);
				var allowed_shifts = frappe.utils.get_config_by_name("ALLOWED_SHIFT_REQUEST_FOR_RESTRICTED_DEPARTMENTS", []);
				if( departments.indexOf(data[0].department) > -1 ) {
					frm.set_query("shift_type", function() {
						return {
							filters: {
								name: ["in", allowed_shifts.toString()]
							}
						};
					});
				}
			}
		});
	},
	refresh(frm) {
		// your code here
	}
});