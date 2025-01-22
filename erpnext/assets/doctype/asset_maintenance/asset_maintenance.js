// Copyright (c) 2017, Frappe Technologies Pvt. Ltd. and contributors
// For license information, please see license.txt

frappe.ui.form.on('Asset Maintenance', {
	setup: (frm) => {
		debugger
		frm.set_indicator_formatter('status',
			function(doc) {
				let indicator = 'red'
				if (doc.status == 'MR Generated') {
					indicator = 'orange';
				}
				return indicator;
			}
		);


		frm.set_query('project', function() {
            return {
                filters: {
                    status: 'Open'
                }
            };
        });

		manage_workflow_buttons(frm);
	},

	refresh: (frm) => {
		if(!frm.is_new()) {
			frm.trigger('make_dashboard');
		}
		make_bill_of_material_cdt_read_only(frm);
		manage_workflow_buttons(frm);
		set_indicator(frm);
	},

	onload: (frm) => {
		manage_workflow_buttons(frm);
		set_indicator(frm);
		// Hide Bill of Material child tables when loading the Asset Maintenance document
		frm.set_df_property('bill_of_material_and_services', 'hidden', 1);
		frm.set_df_property('consumed_items', 'hidden', 1);
		frm.set_df_property('return_items', 'hidden', 1);
		frm.set_df_property('issue_material', 'hidden', 1);
		frm.set_df_property('charge_consumption', 'hidden', 1);
		frm.set_df_property('return_item', 'hidden', 1);

		// Collect unique MR references from the child table
        const mr_references = Array.from(new Set(
            frm.doc.bill_of_material_and_services
                .filter(row => row.mr_reference)
                .map(row => row.mr_reference)
        ));

        if (mr_references.length === 0) return;

		// Fetch all relevant Material Request Item records in a single API call
		frappe.call({
			method: 'erpnext.assets.doctype.asset_maintenance.asset_maintenance.get_received_qty_from_material_request',
			freeze: true,
			freeze_message: __("Retrieving Received Qty from Material Request"),
			args: {
				mr_references: JSON.stringify(mr_references)
			},
			callback: function(response) {
				if (response.message) {
					const mr_items = response.message;

					// Create a mapping of (MR name -> Item Code -> Qty)
					const mr_items_map = {};
					mr_items.forEach(item => {
						if (!mr_items_map[item.parent]) {
							mr_items_map[item.parent] = {};
						}
						mr_items_map[item.parent][item.item_code] = item.qty;
					});

					// Populate received_qty for each row in the child table if value is 0
					frm.doc.bill_of_material_and_services.forEach(row => {
						if (row.received_qty === 0 || row.received_qty === undefined) {
							if (row.mr_reference && mr_items_map[row.mr_reference]) {
								// Update received_qty
								row.received_qty = mr_items_map[row.mr_reference][row.item]; 
							}
						} 
					});

					frm.refresh_field('bill_of_material_and_services');
				}
			}
		});
	},

	project: function(frm) {
        if (frm.doc.project) {

            frappe.call({
                method: 'frappe.client.get_list',
                args: {
                    doctype: 'Task',
                    filters: {
                        project: frm.doc.project,
                        status: 'Open'
                    },
                    fields: "*"
                },
                callback: function(response) {
                    if (response.message) {
                        const tasks = response.message;
						frm.clear_table('asset_maintenance_tasks');
                        tasks.forEach(task => {
							const child = frm.add_child('asset_maintenance_tasks');
                            if (child) {
                                child.maintenance_task = task.name || "";
								child.assign_to = task.completed_by
                            }
                        });

                        frm.refresh_field('asset_maintenance_tasks');
                    } else {
                        console.error("No tasks found for project:", frm.doc.project);
                    }
                }
            });
        }
    },

	make_dashboard: (frm) => {
		if(!frm.is_new()) {
			frappe.call({
				method: 'erpnext.assets.doctype.asset_maintenance.asset_maintenance.get_maintenance_log',
				args: {asset_name: frm.doc.asset_name},
				callback: (r) => {
					if(!r.message) {
						return;
					}
					var section = frm.dashboard.add_section(`<h5 style="margin-top: 0px;">
						${ __("Maintenance Log") }</a></h5>`);
					var rows = $('<div></div>').appendTo(section);
					// show
					(r.message || []).forEach(function(d) {
						$(`<div class='row' style='margin-bottom: 10px;'>
							<div class='col-sm-3 small'>
								<a onclick="frappe.set_route('List', 'Asset Maintenance Log', 
									{'asset_name': '${d.asset_name}','maintenance_status': '${d.maintenance_status}' });">
									${d.maintenance_status} <span class="badge">${d.count}</span>
								</a>
							</div>
						</div>`).appendTo(rows);
					});
					frm.dashboard.show();
				}
			});
		}
	}
});

frappe.ui.form.on('Asset Maintenance Task', {
	start_date: (frm, cdt, cdn)  => {
		get_next_due_date(frm, cdt, cdn);
	},
	periodicity: (frm, cdt, cdn)  => {
		get_next_due_date(frm, cdt, cdn);
	},
	last_completion_date: (frm, cdt, cdn)  => {
		get_next_due_date(frm, cdt, cdn);
	},
	end_date: (frm, cdt, cdn)  => {
		get_next_due_date(frm, cdt, cdn);
	}
});

var get_next_due_date = function (frm, cdt, cdn) {
	var d = locals[cdt][cdn];
	if (d.start_date && d.periodicity) {
		return frappe.call({
			method: 'erpnext.assets.doctype.asset_maintenance.asset_maintenance.calculate_next_due_date',
			args: {
				start_date: d.start_date,
				periodicity: d.periodicity,
				end_date: d.end_date,
				last_completion_date: d.last_completion_date,
				next_due_date: d.next_due_date
			},
			callback: function(r) {
				if (r.message) {
					frappe.model.set_value(cdt, cdn, "next_due_date", r.message);
				}
				else {
					frappe.model.set_value(cdt, cdn, "next_due_date", "");
				}
			}
		});
	}
};

var make_bill_of_material_cdt_read_only = function (frm) {
	if (frm.fields_dict['bill_of_material_and_services'].df.hidden === 0) {
		frm.doc.bill_of_material_and_services.forEach(row => {
			if (row.mr_reference) {
				const grid_row = frm.fields_dict['bill_of_material_and_services'].grid.grid_rows_by_docname[row.name];
				if (grid_row) {
					grid_row.docfields.forEach(field => {
						field.read_only = 1;
					});
				}
			}
		});
	};
	frm.refresh_field('bill_of_material_and_services');
}

// Code by Moeiz
frappe.ui.form.on('Bill of Material and Services', {
    item: function(frm, cdt, cdn) {
        // Get the current child row data
        let row = locals[cdt][cdn];

        if (frm.doc.company) {
            // Run server-side code to get stock available for the selected item
            frappe.call({
                method: 'erpnext.assets.doctype.asset_maintenance.asset_maintenance.get_available_stock_for_bill_and_services',
                args: {
                    'item_code': row.item,  // Verify the field name here
                    'company': frm.doc.company
                },
				freeze: true, // Freeze the UI during the request
                freeze_message: __("Calculating Stock for this Item"), // Display message
                callback: function(response) {
                    let total_qty = response.message ? response.message : 0;
                    
                    // Set the stock available in the child table's field
                    frappe.model.set_value(cdt, cdn, 'stock_available', total_qty);
					collect_items_and_update_field(frm)
                    
                    // Refresh the field if necessary
                    frm.refresh_field('bill_of_material_and_services');
                }
            });
        } else {
            frappe.throw("Please select Company first");
        }

		// if (frm.doc.bill_of_material_and_services) {
		// 	let items_list = frm.doc.bill_of_material_and_services.map(row => row.item);
		// 	 frm.fields_dict['asset_maintenance_tasks'].grid.get_field('item_used').get_query = function () {
		// 		return {
		// 			"filters": {
		// 				"item_used": ['in', items_list]
		// 			},
		// 		};
		// 	};
		// }
		function collect_items_and_update_field(frm) {
			let item_list = [];
		
			frm.doc.bill_of_material_and_services.forEach(row => {
				if (row.item) {
					item_list.push(row.item);
				}
			});

			frm.fields_dict['asset_maintenance_tasks'].grid.get_field('item_used').get_query = function(doc, cdt, cdn) {
				return {
					filters: {
						name: ['in', item_list]
					}
				};
			};
		
			frm.refresh_field('item_used');
		}
    },
	
});


function manage_workflow_buttons(frm){
	let status = frm.doc.status
	if (status == "MR Generated"){
		frm.add_custom_button(__('Not Started'), function() {
			console.log("Not Started function called")
		});
	}
}

