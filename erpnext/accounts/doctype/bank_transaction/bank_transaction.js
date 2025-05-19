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
					"name": ["in", ["GL Entry"]]
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
	},
	form_rendered: function(frm) {
		// Setup filter when form is rendered
		setup_dynamic_link_query(frm);
	},
	payment_entries_add: function(frm, cdt, cdn) {
		// Setup filter again on row add
		setup_dynamic_link_query(frm);
	},
	type: function(frm, cdt, cdn) {
		// Re-apply filter on type change
		setup_dynamic_link_query(frm);
	},
	payment_entry: function(frm, cdt, cdn) {
		let row = locals[cdt][cdn];
		if (!row.payment_entry) return;

		frappe.db.get_value('GL Entry', row.payment_entry, ['credit', 'debit'])
			.then(r => {
				let data = r.message;
				if (!data) return;

				if (data.credit > 0) {
					row.allocated_amount = data.credit;
				} else if (data.debit > 0) {
					row.allocated_amount = data.debit;
				} else {
					row.allocated_amount = 0;
				}
				frm.refresh_field('payment_entries');
			});
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

function setup_dynamic_link_query(frm) {
	frm.fields_dict['payment_entries'].grid.get_field('payment_entry').get_query = function(doc, cdt, cdn) {
		let row = locals[cdt][cdn];
		if (!row || !row.type) return;

		return {
			query: "erpnext.accounts.doctype.bank_transaction.bank_transaction.get_payment_documents",
			filters: {
				type: row.type,
				account: frm.doc.bank_account
			}
		};
	};
}
