// Copyright (c) 2025, Frappe Technologies Pvt. Ltd. and contributors
// For license information, please see license.txt

frappe.ui.form.on('Ranking Setup', {
	// refresh: function(frm) {

	// }
});

frappe.ui.form.on('Ranking Setup Item', {
	range_slab_start: function(frm, cdt, cdn){
		let range_val = locals[cdt][cdn];
		if (range_val.range_slab_start < 0 || range_val.range_slab_start > 100){
			frappe.msgprint(__("Please select a valid Number i.e. 0 - 100"));
			frappe.model.set_value(cdt,cdn, "range_slab_start", "");
		}
	},

	range_slab_end: function(frm, cdt, cdn){
		let range_val = locals[cdt][cdn];
		if (range_val.range_slab_end < 0 || range_val.range_slab_end > 100){
			frappe.msgprint(__("Please select a valid Number i.e. 0 - 100"));
			frappe.model.set_value(cdt,cdn, "range_slab_end", "");
		}
	}
});