frappe.ui.form.on("Maintenance", {
  refresh: function (frm) {
    
    // Unplanned CIP if coming from work order
    if (frm.doc.work_order_id) {
      if (!frm.doc.cip_category){
      frm.doc.cip_category = "Unplanned CIP";
      }
      frm.set_df_property("cip_category", "read_only", 1);
      frm.set_df_property("work_order_id", "read_only", 1);
      frm.set_df_property("work_order_item", "read_only", 1);
      frm.set_df_property("company", "read_only", 1);

      hide_fields_for_general_cip(frm);
    } else if (frm.doc.cip_category === "Planned CIP") {
      // Planned cip is only scheduled from the cip schedule setup doctype
      planned_cip(frm);
    } else {
      // Creating document from new button
      create_cip_configuration(frm);
      hide_fields_for_general_cip(frm);
    }

    // Worflow setup
    // Check if the workflow_state has changed
    if (
      frm.doc.workflow_state === "CIP Inprogress" &&
      frm.doc.previous_workflow_state !== frm.doc.workflow_state
    ) {
      // Run your first frappe.call
      frappe.call({
        method: "mark_cip_inprogress",
        doc: frm.doc,
        freeze: true,
        freeze_message: __("Marking CIP in Progress. Please wait."),
        callback: function (r) {
          if (r.message === "CIP Inprogress") {
            frm.save().then(() => {
              // Only in case of unplanned CIP and specific CIP types
              if (
                frm.doc.cip_category === "Unplanned CIP" &&
                (frm.doc.cip_type === "Flavour Change" ||
                  frm.doc.cip_type === "Pack Change" ||
                  frm.doc.cip_type === "Flavor & Pack Change")
              ) {
                // Close work order after saving
                frappe.call({
                  method: "nrp_manufacturing.modules.gourmet.work_order.work_order.close_work_order",
                  args: {
                    work_order: frm.doc.work_order_id,
                    status: "Closed",
                  },
                  freeze: true,
                  freeze_message: __("Marking CIP Complete. Please wait."),
                  callback: function (r) {
                    if (r.message) {
                      let stock_entry = r.message;
                      if (isEmpty(stock_entry)) {
                        location.reload();
                      } else {
                        frappe.model.sync(stock_entry);
                        frappe.set_route("Form", stock_entry.doctype, stock_entry.name);
                      }
                    }
                  },
                });
              }
            }).catch((err) => {
              frappe.msgprint(__('Failed to save the document.'));
            });
          }else if(r.message === "Already in progress"){
            frm.set_value('workflow_state', "Not Initiated")
            frm.save();
          }
        },
      });
    }

    // For in progress and completed CIP make cip type and other fields read onlu
    if (frm.doc.workflow_state !== "Not Initiated") {
      frm.set_df_property("cip_type", "read_only", 1);
      frm.set_df_property("change_item_to", "read_only", 1);
      frm.set_df_property("section", "read_only", 1);
    }

    frm.page.menu.find('[data-label="Menu"],[data-label="Duplicate"]').parent().parent().remove();

    if (!frm.is_new()) {
      frm.set_df_property("company", "read_only", 1);
      frm.set_df_property("cost_center", "read_only", 1);
    }
  },

  onload: function (frm) {
    hide_fields_for_general_cip(frm);
    frm.set_df_property("task", "read_only", 1);
    frm.set_value("task", "CIP");

    if (frm.doc.work_order_item) {
      populate_change_item_from(frm);
    }
  },


  before_save: function(frm){
    if(frm.doc.cip_category === "Planned CIP" && frm.is_new()){
      frappe.throw("You cannot create planned CIP from here")
    }
  },

  cip_type: function (frm) {
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
  },
});

function hide_fields_for_general_cip(frm) {
  if (frm.doc.cip_type === "General") {
    frm.set_df_property("change_item_to", "hidden", 1);
    frm.set_df_property("flavour_change_to", "hidden", 1);
    frm.set_df_property("change_pack_to", "hidden", 1);
    frm.set_df_property("change_item_to", "reqd", 0);
    frm.set_value("change_item_to", null);
  } else {
    frm.set_df_property("change_item_to", "hidden", 0);
    frm.set_df_property("flavour_change_to", "hidden", 0);
    frm.set_df_property("change_pack_to", "hidden", 0);
    frm.set_df_property("change_item_to", "reqd", 1);

    // Show only fg csd items in item to field
    frm.set_query("change_item_to", function (doc) {
      return {
        filters: {
          item_section: "FG CSD",
          name: ["!=", doc.work_order_item] // Use an array for "!="
        },
      };
    });
  }

  if (!frm.doc.change_item_to) {
    frm.set_value("flavour_change_to", null);
    frm.set_value("change_pack_to", null);
    frm.set_value("change_item_to_name", null);
  }
}

function unplanned_cip(frm) {
  // Check if the workflow_state has changed
  if (
    frm.doc.workflow_state === "CIP Inprogress" &&
    frm.doc.previous_workflow_state !== frm.doc.workflow_state
  ) {
    // Run your first frappe.call
    frappe.call({
      method: "mark_cip_inprogress",
      doc: frm.doc,
      freeze: true,
      freeze_message: __("Marking CIP in Progress. Please wait."),
      callback: function (r) {
        if (r.message === "CIP Inprogress") {
          // Update previous workflow state to the current workflow_state
          frm.set_value("previous_workflow_state", frm.doc.workflow_state);
          frm.save();
          if (
            frm.doc.cip_type === "Flavour Change" ||
            frm.doc.cip_type === "Pack Change" ||
            frm.doc.cip_type === "Flavor & Pack Change"
          ) {
            frappe.call({
              method:
                "nrp_manufacturing.modules.gourmet.work_order.work_order.close_work_order",
              args: {
                work_order: frm.doc.work_order_id,
                status: "Closed",
              },
              freeze: true,
              freeze_message: __("Marking CIP Complete. Please wait."),
              callback: function (r) {
                if (r.message) {
                  let stock_entry = r.message;
                  if (isEmpty(stock_entry)) {
                    location.reload();
                  } else {
                    frappe.model.sync(stock_entry);
                    frappe.set_route(
                      "Form",
                      stock_entry.doctype,
                      stock_entry.name
                    );
                  }
                }
              },
            });
          }
        }
      },
    });
  }
}

function planned_cip(frm) {
  frm.set_df_property("cip_type", "read_only", 1);
  frm.set_df_property("cip_category", "read_only", 1);

  frm.set_df_property("change_item_to", "hidden", 1);
  frm.set_df_property("flavour_change_to", "hidden", 1);
  frm.set_df_property("change_pack_to", "hidden", 1);
  frm.set_df_property("change_flavour_from", "hidden", 1);
  frm.set_df_property("change_pack_from", "hidden", 1);
  frm.set_df_property("change_pack_to", "hidden", 1);
  frm.set_df_property("company", "read_only", 1);
}

function populate_change_item_to(frm) {
  frappe.call({
    method: "get_flavour_and_pack_changes_for_change_to",
    doc: frm.doc,
    freeze: true,
    freeze_message: __("Fetching data. Please wait."),
    callback: function (r) {
      frm.refresh_field("flavour_change_to");
      frm.refresh_field("change_pack_to");
    },
  });
}

function populate_change_item_from(frm) {
  frappe.call({
    method: "get_flavour_and_pack_changes_for_change_from",
    doc: frm.doc,
    freeze: true,
    freeze_message: __("Fetching data. Please wait."),
    callback: function (r) {
      frm.refresh_field("change_flavour_from");
      frm.refresh_field("change_pack_from");
    },
  });
}

function create_cip_configuration(frm) {
  frm.set_value("cip_category", "Unplanned CIP");
  frm.set_df_property("cip_category", "read_only", 1);

  frm.set_value("cip_type", "General");
  frm.set_df_property("cip_type", "read_only", 1);

  frm.set_df_property("company", "reqd", 1);

  frm.set_df_property("cost_center", "reqd", 1);
  frm.set_df_property("cost_center", "read_only", 0);
  frm.set_df_property("cost_center", "hidden", 0);

  // Show only parent asset marked cost centers for selected company
  frm.set_query("cost_center", function (doc) {
    return {
      filters: {
        is_parent_asset: 1,
        company: doc.company,
      },
    };
  });
}
