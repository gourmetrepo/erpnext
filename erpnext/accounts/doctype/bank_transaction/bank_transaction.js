// Copyright (c) 2018, Frappe Technologies Pvt. Ltd. and contributors
// For license information, please see license.txt

frappe.ui.form.on('Bank Transaction', {
	refresh: function(frm) {
		frm.set_query("company", function () {
			return {
				"filters": {
					"is_group": 0
				}
			};
		});
	},
	onload(frm) {
		frm.set_query('payment_document', 'payment_entries', function() {
			return {
				"filters": {
					"name": ["in", ["Payment Entry", "Journal Entry", "Sales Invoice", "Purchase Invoice", "Expense Claim"]]
				}
			};
		});
	},
	company: function (frm) {
		if (!frm.doc.company){
			frm.set_value("bank_account", "");
			frm.refresh_field("bank_account");
		}
		else{
			frm.set_query("bank_account", function () {
				return {
					"filters": {
						"is_group": 0,
						"company": frm.doc.company,
						"account_type": 'Bank'
					}
				};
			});
		}
	},
	bank_account: function (frm) {
		if (!frm.doc.company){
			frappe.msgprint(__('Please select company first.'));
			frm.set_value("bank_account", "");
			frm.refresh_field("bank_account");
		}
	}
});

frappe.ui.form.on('Bank Transaction Payments', {
	payment_entries_remove: function(frm, cdt, cdn) {
		update_clearance_date(frm, cdt, cdn);
	}
});

const update_clearance_date = (frm, cdt, cdn) => {
	if (frm.doc.docstatus === 1) {
		frappe.xcall('erpnext.accounts.doctype.bank_transaction.bank_transaction.unclear_reference_payment',
			{doctype: cdt, docname: cdn})
			.then(e => {
				if (e == "success") {
					frappe.show_alert({message:__("Document {0} successfully uncleared", [e]), indicator:'green'});
				}
			});
	}
};