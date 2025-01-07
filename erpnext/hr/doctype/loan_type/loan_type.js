// Copyright (c) 2016, Frappe Technologies Pvt. Ltd. and contributors
// For license information, please see license.txt

frappe.ui.form.on('Loan Type', {
	refresh(frm) {
		frm.set_query("loan_account", "accounts", function(doc, cdt, cdn) {
			var d = locals[cdt][cdn];
			return {
				filters: {
					"is_group": 0,
					"company": d.company
				}
			};
		});
		frm.set_query("interest_account", "accounts", function(doc, cdt, cdn) {
			var d = locals[cdt][cdn];
			return {
				filters: {
					"is_group": 0,
					"company": d.company
				}
			};
		});
	}
});
