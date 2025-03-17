// Copyright (c) 2018, Frappe Technologies Pvt. Ltd. and contributors
// For license information, please see license.txt

frappe.ui.form.on('Shift Assignment', {
	refresh: function(frm) {
        frm.set_query("employee", function() {
            return {
                filters: {
                    status: ["!=", "Left"]
                }
            };
        });
    }
});
