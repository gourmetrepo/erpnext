
frappe.ui.form.on('Maintenance', {
	
    refresh: function(frm) {

        // Unplanned CIP if coming from work order
        if (frm.doc.work_order_id){
            // Set cip category to Planned CIP
            frm.doc.cip_category = "Unplanned CIP"
            frm.set_df_property("cip_category", "read_only", 1)
            hide_fields_for_general_cip(frm);
        }else{
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
						frm.set_value("previous_workflow_state", frm.doc.workflow_state);
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
    },

    cip_type: function (frm){
        hide_fields_for_general_cip(frm);
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
    // Set cip type to General and read only
    frm.doc.cip_type = "General"
    frm.set_df_property("cip_type", "read_only", 1)

    // Set cip category to Planned CIP
    frm.doc.cip_category = "Planned CIP"
    frm.set_df_property("cip_category", "read_only", 1)

    frm.set_df_property("change_item_to", "hidden", 1);
    frm.set_df_property("flavour_change_to", "hidden", 1);
    frm.set_df_property("change_pack_to", "hidden", 1);
    frm.set_df_property("change_flavour_from", "hidden", 1);
    frm.set_df_property("change_pack_from", "hidden", 1);
    frm.set_df_property("change_pack_to", "hidden", 1);

    frm.set_df_property("work_order_id", "hidden", 1)
    frm.set_df_property("work_order_item", "hidden", 1)
    frm.set_df_property("work_order_quantity", "hidden", 1)
    frm.set_df_property("quantity_produced", "hidden", 1)
    frm.set_df_property("remaining_quantity", "hidden", 1)

}