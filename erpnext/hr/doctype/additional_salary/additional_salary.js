// Copyright (c) 2018, Frappe Technologies Pvt. Ltd. and contributors
// For license information, please see license.txt

frappe.ui.form.on('Additional Salary', {
	refresh(frm) {
		if (frm.doc.salary_component != frappe.utils.get_config_by_name("SALARY_COMPONENT_FOR_SHOP_INCENTIVE", "Sales Incentives")){
			frm.doc.incentive_date = "";
		}
		frm.set_query("employee", function() {
			return {
				filters: {
					company: frm.doc.company
				}
			};
		});
	 },
	setup: function(frm) {
		frm.add_fetch("salary_component", "deduct_full_tax_on_selected_payroll_date", "deduct_full_tax_on_selected_payroll_date");

		frm.set_query("employee", function() {
			return {
				filters: {
					company: frm.doc.company,
					status:  "Active"
				}
			};
		});
	}
});
