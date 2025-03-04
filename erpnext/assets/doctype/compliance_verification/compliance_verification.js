// Copyright (c) 2025, Frappe Technologies Pvt. Ltd. and contributors
// For license information, please see license.txt

frappe.ui.form.on('Compliance Verification', {
	refresh: function(frm) {
		if (frm.doc.docstatus == 0 && !frm.is_new()){
			frm.add_custom_button(__('Fetch Data'), function () {
				frappe.call({
					freeze: true,
					doc: frm.doc,
					method: 'fetch_data',
					callback: function() {
						frm.dirty()
						frm.save()
					}
				});
			});
		}
		frm.set_query("area_incharge", function() {
            if(!frm.doc.parameter_setup){
                frappe.msgprint("Please select Parameter first.");
            }
            return {
                "filters": {
					"company": frm.doc.company,
					"department": frm.doc.department
				}
            };
        });
	},
	onload: function(frm) {
		if (frm.is_new()) {
			frappe.db.get_value('Employee', {'user_id': frappe.session.user}, 'employee', (r) => {
				if (r && r.employee) {
					frm.set_value('inspector', r.employee);
				}
			});
		}
		if (frm.doc.compliance_verification_item.length){
			frappe.call({
				method: "erpnext.assets.doctype.compliance_verification.compliance_verification.get_rank_options",
				args: {
					compliance_verification_items: frm.doc.compliance_verification_item
				},
				callback: function(r) {
					let data = r.message;
					frm.doc.compliance_verification_item.forEach(function(row) {
						let options = data[row.parameter];
						if (options) {
							frappe.meta.get_docfield('Compliance Verification Item', 'ranking', row.name).options = [''].concat(options);
						}
					});
					frm.refresh_field('compliance_verification_item');
				}
			});
		}
	},
	after_save: function(frm) {
		//To load LOVs in the child table
		frm.reload_doc();
	}
});
