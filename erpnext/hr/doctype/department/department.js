// Copyright (c) 2016, Frappe Technologies Pvt. Ltd. and contributors
// For license information, please see license.txt

frappe.ui.form.on('Department', {
	refresh: function(frm) {
		// read-only for root department
		if(!frm.doc.parent_department && !frm.is_new()) {
			frm.set_read_only();
			frm.set_intro(__("This is a root department and cannot be edited."));
		}
		frm.set_query("expense_account", function() {
            if(!frm.doc.company){
                frappe.msgprint("Please select Company first");
            }
            return {
                "filters": {
                    "company": frm.doc.company,
                    "root_type": "Expense",
                    "is_group": 0
                }
            };
        });
        frm.set_query("gratuity_expense_account", function() {
            return {
                filters: {
                    is_gratuity_expense_account: 1,
                }
            }
        });
        frm.set_query("gratuity_account", function() {
            return {
                filters: {
                    is_gratuity_account: 1,
                }
            }
        });
	},

	validate: function(frm) {
		if(frm.doc.name=="All Departments") {
			frappe.throw(__("You cannot edit root node."));
		}
	}
});
