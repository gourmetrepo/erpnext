// Copyright (c) 2025, Shahzad Naser and contributors
// For license information, please see license.txt

frappe.ui.form.on('Job Opening', {
	job_requisition_id: (frm) => {
		frappe.call({
			"method": "frappe.client.get",
			args: {
				doctype: "Job Requisition",
				name: frm.doc.job_requisition_id
			},
			callback: function (r) {
				frm.set_value("required_to_work_in_shifts", r.message.required_to_work_in_shifts);
				frm.refresh_field("required_to_work_in_shifts");
				frm.set_value("required_to_travel", r.message.required_to_travel);
				frm.refresh_field("required_to_travel");
			}
		});
	},

	position: (frm) => {
		frappe.call({
			"method": "frappe.client.get",
			args: {
				doctype: "Position",
				name: frm.doc.position
			},
			callback: function (r) {
				frm.set_value("required_background_check", r.message.required_background_check);
				frm.refresh_field("required_background_check");
			}
		});
	}
});
