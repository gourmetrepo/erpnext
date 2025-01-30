// Copyright (c) 2025, Frappe Technologies Pvt. Ltd. and contributors
// For license information, please see license.txt

frappe.ui.form.on('Parameter Setup', {
	refresh: function(frm) {
		frm.set_query("cost_center", function() {
            if(!frm.doc.company){
                frappe.msgprint("Please select Company first");
            }
            let filters = {"company": frm.doc.company};
            return {
                "filters": filters
            };
        });
	}
});
