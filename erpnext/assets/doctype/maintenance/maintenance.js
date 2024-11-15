
frappe.ui.form.on('Maintenance', {
	
    refresh: function(frm) {

        // Unplanned CIP if coming from work order
        if (frm.doc.work_order_id){
            // Set cip category to Planned CIP
            frm.doc.cip_category = "Unplanned CIP"
            frm.set_df_property("cip_category", "read_only", 1)
            frm.set_df_property("work_order_id", "read_only", 1)
            frm.set_df_property("work_order_item", "read_only", 1)
            
            hide_fields_for_general_cip(frm);
        }else{
            // Planned cip is only scheduled from the cip schedule setup doctype
            planned_cip(frm);
        }
        
        // Worflow setup
        // Check if the workflow_state has changed
        if (frm.doc.workflow_state === "CIP Inprogress" && frm.doc.previous_workflow_state !== frm.doc.workflow_state) {
            // Run your first frappe.call
            frappe.call({
                method: "mark_cip_inprogress",
                doc: frm.doc,
                callback: function(r) {
                    if (r.message === "CIP Inprogress") {
                        
						// Update previous workflow state to the current workflow_state
						frm.save();

                        // Only in case of planned cip
                        if (frm.doc.cip_category==="Unplanned CIP" && (frm.doc.cip_type === "Flavour Change" || frm.doc.cip_type === "Pack Change" || frm.doc.cip_type === "Flavor & Pack Change")) {
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

        
    },
    onload: function(frm) {
        hide_fields_for_general_cip(frm);
        frm.set_df_property('task', 'read_only', 1);
        frm.set_value('task', 'CIP');
    },

    cip_type: function (frm){
        hide_fields_for_general_cip(frm);
    },

    change_item_to: function (frm) {
        if (frm.doc.change_item_to) {
            populate_change_item_to(frm);
        }
    },

    work_order_item: function (frm) {
        if (frm.doc.work_order_item) {
            populate_change_item_from(frm);
        }
    }
});



function hide_fields_for_general_cip(frm){
    if (frm.doc.cip_type === "General") {
        frm.set_df_property("change_item_to", "hidden", 1);
        frm.set_df_property("flavour_change_to", "hidden", 1);
        frm.set_df_property("change_pack_to", "hidden", 1);
    }else{
        frm.set_df_property("change_item_to", "hidden", 0);
        frm.set_df_property("flavour_change_to", "hidden", 0);
        frm.set_df_property("change_pack_to", "hidden", 0);
    }

}




function unplanned_cip(frm){



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
                        if (frm.doc.cip_type === "Flavour Change" || frm.doc.cip_type === "Pack Change" || frm.doc.cip_type === "Flavor & Pack Change") {
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


function planned_cip(frm){
    frm.set_df_property("cip_type", "read_only", 1)
    frm.set_df_property("cip_category", "read_only", 1)

    frm.set_df_property("change_item_to", "hidden", 1);
    frm.set_df_property("flavour_change_to", "hidden", 1);
    frm.set_df_property("change_pack_to", "hidden", 1);
    frm.set_df_property("change_flavour_from", "hidden", 1);
    frm.set_df_property("change_pack_from", "hidden", 1);
    frm.set_df_property("change_pack_to", "hidden", 1);

    // frm.set_df_property("work_order_id", "hidden", 1)
    // frm.set_df_property("work_order_item", "hidden", 1)
    // frm.set_df_property("work_order_quantity", "hidden", 1)
    // frm.set_df_property("quantity_produced", "hidden", 1)
    // frm.set_df_property("remaining_quantity", "hidden", 1)

}

function populate_change_item_to(frm) {
    frappe.call({
        method: "get_flavour_and_pack_changes_for_change_to",
        doc: frm.doc,
        freeze: true,
        freeze_message: __("Fetching data. Please wait."),
        callback: function(r) {
            frm.refresh_field("flavour_change_to");
            frm.refresh_field("change_pack_to");
            frm.refresh_field("change_flavour_from");
            frm.refresh_field("change_pack_from");
        }
    });
}

function populate_change_item_from(frm) {
    frappe.call({
        method: "get_flavour_and_pack_changes_for_change_from",
        doc: frm.doc,
        freeze: true,
        freeze_message: __("Fetching data. Please wait."),
        callback: function(r) {
            frm.refresh_field("flavour_change_to");
            frm.refresh_field("change_pack_to");
            frm.refresh_field("change_flavour_from");
            frm.refresh_field("change_pack_from");
        }
    });
}