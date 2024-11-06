// // Copyright (c) 2024, Frappe Technologies Pvt. Ltd. and contributors
// // For license information, please see license.txt

// frappe.ui.form.on('Maintenance', {



// 	validate: function(frm) {
// 		debugger;
		
// 		if (frm.doc.workflow_state == "CIP Inprogress"){
// 		// First frappe.call
// 		frappe.call({
// 			method: "mark_cip_inprogress",
// 			doc: frm.doc,
// 			callback: function(r) {
// 				if (r.message == "CIP Inprogress") {
// 					console.log("Work Order Stopped");
	
// 					// Second frappe.call nested inside the first
// 					if (frm.doc.cip_type == "Flavour Change") {
// 						frappe.call({
// 							method: "nrp_manufacturing.modules.gourmet.work_order.work_order.close_work_order",
// 							args: {
// 								work_order: frm.doc.work_order_id,
// 								status: "Closed"
// 							},
// 							callback: function(r) {
// 								if (r.message) {
// 									let stock_entry = r.message;
// 									if (isEmpty(stock_entry)) {
// 										location.reload();
// 									} else {
// 										frappe.model.sync(stock_entry);
// 										frappe.set_route('Form', stock_entry.doctype, stock_entry.name);
// 									}
// 								}
// 							}
// 						});
// 					}
// 				}
// 			}
// 		});
// 	}

// 	}
	


// 	// refresh: function(frm) {

// 	// }


// 	// workflow_state: function(frm){
// 	// 	debugger;
// 	// 	console.log("Workflow state changed", frm.doc.workflow_state)
// 	// },

// 	// mark_cip_inprogress: function(frm) {
// 	// 	frappe.call({
// 	// 		method: "mark_cip_inprogress",
// 	// 		callback: function(r) {
// 	// 			if(r.message) {
// 	// 				frm.set_value("status", r.message);
// 	// 				frm.reload_doc();
// 	// 			}
// 	// 		}
// 	// 	});
// 	// },

// 	// mark_cip_finished: function(frm) {
// 	// 	frappe.call({
// 	// 		method: "mark_cip_finished",
// 	// 		callback: function(r) {
// 	// 			if(r.message) {
// 	// 				frm.set_value("status", r.message);
// 	// 				frm.reload_doc();
// 	// 			}
// 	// 		}
// 	// 	});
// 	// }
// });

frappe.ui.form.on('Maintenance', {
	
    refresh: function(frm) {
        // Check if the workflow_state has changed
        if (frm.doc.workflow_state === "CIP Inprogress" && frm.doc.previous_workflow_state !== frm.doc.workflow_state) {
            // Run your first frappe.call
            frappe.call({
                method: "mark_cip_inprogress",
                doc: frm.doc,
                callback: function(r) {
                    if (r.message === "CIP Inprogress") {
                        
						// Update previous workflow state to the current workflow_state
						frm.set_value("previous_workflow_state", frm.doc.workflow_state);
						frm.save();
                        if (frm.doc.cip_type === "Flavour Change" || frm.doc.cip_type === "Pack Change") {
                            frappe.call({
                                method: "nrp_manufacturing.modules.gourmet.work_order.work_order.close_work_order",
                                args: {
                                    work_order: frm.doc.work_order_id,
                                    status: "Closed"
                                },
                                callback: function(r) {
                                    if (r.message) {
                                        let stock_entry = r.message;
                                        if (isEmpty(stock_entry)) {
                                            location.reload();
                                        } else {
                                            frappe.model.sync(stock_entry);
                                            frappe.set_route('Form', stock_entry.doctype, stock_entry.name);
                                        }
                                    }
                                }
                            });
                        }
                    }
                }
            });


        }
    }
});
