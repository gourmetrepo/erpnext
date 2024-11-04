// Copyright (c) 2024, Frappe Technologies Pvt. Ltd. and contributors
// For license information, please see license.txt

frappe.ui.form.on('Maintenance', {
	// refresh: function(frm) {

	// }


	// workflow_state: function(frm){
	// 	debugger;
	// 	if (frm.doc.workflow_state == "CIP InProgress") {
	// 		mark_cip_inprogress(frm);
	// 	}else if (frm.doc.workflow_state == "CIP Finished") {
	// 		mark_cip_finished(frm);
	// 	}
	// },

	// mark_cip_inprogress: function(frm) {
	// 	frappe.call({
	// 		method: "mark_cip_inprogress",
	// 		callback: function(r) {
	// 			if(r.message) {
	// 				frm.set_value("status", r.message);
	// 				frm.reload_doc();
	// 			}
	// 		}
	// 	});
	// },

	// mark_cip_finished: function(frm) {
	// 	frappe.call({
	// 		method: "mark_cip_finished",
	// 		callback: function(r) {
	// 			if(r.message) {
	// 				frm.set_value("status", r.message);
	// 				frm.reload_doc();
	// 			}
	// 		}
	// 	});
	// }
});
