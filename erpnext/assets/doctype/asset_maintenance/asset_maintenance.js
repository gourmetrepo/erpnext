// Copyright (c) 2017, Frappe Technologies Pvt. Ltd. and contributors
// For license information, please see license.txt

frappe.ui.form.on('Asset Maintenance', {
	setup: (frm) => {

		
		frm.set_query('project', function() {
            return {
                filters: {
                    status: 'Open',
					company: frm.doc.company
                }
            };
        });

		frm.set_query('cost_center', function() {
            return {
                filters: {
                    company: frm.doc.company,
					is_parent_asset: 1
                }
            };
        });

		frm.set_indicator_formatter('status',
			function(doc) {
				if (doc.status === "Completed" || doc.status === "Closed" || doc.status === "Finished") {
					return "green";
		
				}else if(doc.status === "In Process"){
					return "orange";
				}else{
					return "red";
				}
			})
		
	},

	refresh: (frm) => {
		frm.page.set_primary_action(__('Save'), () => {
            frm.save();
        });
      	
		if(!frm.is_new()) {
			frm.trigger('make_dashboard');
		}
		make_bill_of_material_cdt_read_only(frm);
		erpnext.asset_maintenance.manage_workflow_buttons(frm);
		project_frm_configuration(frm);

		if (frm.page.sidebar.find('.form-assignments').length) {
            frm.page.sidebar.find('.form-assignments').hide();
        }
	},

	onload: (frm) => {
		erpnext.asset_maintenance.manage_workflow_buttons(frm);
		project_frm_configuration(frm);

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

	project_based: function(frm){
		project_frm_configuration(frm)
	},

	project: function(frm){
		if(frm.doc.project_based === "Yes"){
			if(frm.doc.project){
				frm.set_df_property('project', 'read_only', 1);
				frm.set_df_property('project_based', 'read_only', 1);
			}else{
				frm.set_df_property('project', 'read_only', 0);
				frm.set_df_property('project_based', 'read_only', 0);
			}
		}
	},
	
	company: (frm) => {
		frm.set_query('cost_center', function() {
            return {
                filters: {
                    company: frm.doc.company,
					is_parent_asset: 1
                }
            };
        });

		frm.set_query('asset_name', function() {
            return {
                filters: {
                    company: frm.doc.company
                }
            };
        });
	},

	cost_center: (frm) => {
		load_assets(frm);
		frm.set_value('plant_maintenance_assets', []);
		if(frm.doc.cost_center){
			frm.set_df_property('plant_maintenance_assets', 'cannot_add_rows', true);
		}else{
			frm.set_df_property('plant_maintenance_assets', 'cannot_add_rows', false);
		}
	},

	issue_material: (frm) => {
		if (!frm.doc.company){
			frappe.throw("Select company first")
		}

		if (!frm.doc.wip_warehouse){
			frappe.throw("WIP Warehouse is missing. Please fetch it for this section, as it may not be assigned in the section master data")
		}

		if (frm.is_dirty()) {
			frappe.throw(__(`Save document before issuing Material Request`));
		}
		
		frm.doc.bill_of_material_and_services.forEach(function(bill, index) {
			if (!bill.item || !bill.demand_qty) {
				frappe.throw(__(`Row ${index + 1}: Kindly provide item with demand quantity to issue material`));
			}
		});
		

		frappe.call({
			method: 'issue_mr_for_bill_of_material_and_services',
			doc: frm.doc,
			freeze: true,
			freeze_message: "Creating Material Request",
			callback: (r) => {
				if (!r.message || !r.message.mr_reference) {
					return;
				}
				
				// Extract the MR reference from the response
				const mr_reference = r.message.mr_reference;

				if (frm.doc.bill_of_material_and_services) {
					frm.doc.bill_of_material_and_services.forEach(row => {
						if (!row.mr_reference) { // Check if mr_reference is not set
							row.mr_reference = mr_reference; // Update the cell
							frappe.model.set_value(row.doctype, row.name, 'mr_reference', row.mr_reference);
						}
					});

					// Refresh the field to reflect changes in the UI
					frm.refresh_field('bill_of_material_and_services');
				}

				frm.save(); // populate received_qty in after_save

				make_bill_of_material_cdt_read_only(frm);
	
				// Show a message with a clickable link to the Material Request
				frappe.msgprint({
					message: __('Material Request Created: <a href="#Form/Material Request/' + mr_reference + '" target="_blank">' + mr_reference + '</a>'),
					title: __('Success'),
					indicator: 'green'
				});
			}
		});
	},

	get_project_tasks: (frm) => {


		if (frm.is_dirty()) {
			frappe.throw(__(`Save document before fetching project tasks`));
		}

		if (!frm.doc.project){
			frappe.throw("Select project first")
		}


		frappe.call({
			method: 'load_tasks',
			doc: frm.doc,
			freeze: true,
			freeze_message: "Fetching Project Tasks",
			callback: (r) => {
				if (!r.message || !r.message.tasks) {
					return;
				}
				
				// Tasks mapped against this project
				const tasks = r.message.tasks;

				for(let i = 0; i < tasks.length; i++) {
					frm.add_child('asset_maintenance_tasks', {
						maintenance_task: tasks[i]['name'],
						start_date: tasks[i]['exp_start_date'],
						assigned_users: tasks[i]['assigned_users']
					})
				}
				frm.refresh_field('asset_maintenance_tasks');
				frm.save(); 
			}
		});
	},


	maintenance_team: (frm, cdt, cdn) => {
		if (frm.doc.maintenance_team && frm.doc.maintenance_team.length > 0) {
			const maintenanceTeamNames = frm.doc.maintenance_team.map(team => team.maintenance_team_name);
			console.log("Maintenance Team Names:", maintenanceTeamNames);
	
			if (maintenanceTeamNames.length > 0) {
				frappe.call({
					method: 'erpnext.assets.doctype.asset_maintenance.asset_maintenance.get_team_members',
					args: {
						maintenance_teams: maintenanceTeamNames
					},
					callback: function(response) {
						if (response.message) {
							const teamMembers = response.message;
	
							frm.fields_dict['asset_maintenance_tasks'].grid.get_field('assign_to').get_query = function(doc, cdt, cdn) {
								return {
									filters: {
										name: ['in', teamMembers]
									}
								};
							};
						} else {
							frappe.msgprint(__('No team members found for the selected maintenance teams.'));
						}
					},
					error: function(error) {
						console.error("Error fetching team members:", error);
						frappe.msgprint(__('There was an error fetching the team members.'));
					}
				});
			} else {
				frappe.msgprint(__('No maintenance team names found.'));
			}
		} else {
			frappe.msgprint(__('No maintenance teams selected.'));
		}
	},	
	bill_of_material_and_services: function(frm, cdt, cdn) {
        console.log("bill_of_material_and_services_add");
    },
	
	work_order_id: (frm) => {
		if (!frm.doc.work_order_id) {
            frm.set_value("order_item", null)
			frm.set_df_property('order_item', 'hidden', 1);
            frm.set_value("total_quantity", null)
            frm.set_df_property('total_quantity', 'hidden', 1);
            frm.set_value("quantity_produced", null)
            frm.set_df_property('quantity_produced', 'hidden', 1);
            frm.set_value("remaining_quantity", null)
            frm.set_df_property('remaining_quantity', 'hidden', 1);
        }

		if (frm.doc.total_quantity !== undefined && frm.doc.total_quantity !== undefined){
			frm.set_value("remaining_quantity", (frm.doc.total_quantity - frm.doc.quantity_produced));
		}
	},
	

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
	},
	maintenance_team: (frm, cdt, cdn) => {
		let row = locals[cdt][cdn];
		let maintenance_team_value = row.maintenance_team;  
	
		if (maintenance_team_value) {
			frappe.call({
				method: 'frappe.client.get_list',
				args: {
					doctype: 'Maintenance Team Member',
					filters: {
						"parent": maintenance_team_value 
					},
					fields: ['team_member']
				},
				callback: function(r) {
					if (r.message) {
						let team_members = r.message.map(member => member.team_member);
						console.log("Filtered team members: ", team_members);
	
						frm.set_query('assign_to', function() {
							return {
								filters: {
									'name': ['in', team_members]
								}
							};
						});
					} else {						
						frm.set_query('assign_to', function() {
							return {};
						});
					}
				},
				error: function(err) {
					console.error("Permission error or other issue: ", err);
					frappe.msgprint(__('You do not have permission to access this Maintenance Team Member record.'));
				}
			});
		} else {	
			frm.set_query('assign_to', function() {
				return {};
			});
		}	
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

        if (frm.doc.company && row.item) {
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
            frappe.throw("Please select Company and item code first");
        }

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


erpnext.asset_maintenance = {
	// Function to make material consumption stock entry
	make_material_consumption_stock_entry: async function(frm) {
		try {
			// Call the server-side function directly using frappe.call
			const r = await frappe.call({
				method: 'erpnext.assets.doctype.asset_maintenance.asset_maintenance.make_material_consumption_stock_entry',
				freeze: true,
				freeze_message: __("Creating Material Consumption Stock Entry"),
				args: {
					'asset_maintenance_doc_ref': frm.doc.name
				}
			});
	
			if (r && r.message) {
				// Sync the returned stock entry with the local model
				frappe.model.sync(r.message);
				// Open the form for the newly created stock entry
				frappe.set_route('Form', r.message.doctype, r.message.name);
			}
		} catch (error) {
			console.error('Error making material consumption stock entry:', error);
			// Optionally handle error display or recovery
		}
	},


	complete_asset_maintenance: async function(frm) {
		try {
			let not_completed = false
			for (let i = 0; i < frm.doc.asset_maintenance_tasks.length; i++) {
				if (frm.doc.asset_maintenance_tasks[i].maintenance_status !== 'Completed') {
					not_completed = true
					break
				}
			}
			if (not_completed){
				frappe.throw("All tasks must be completed before completing the maintenance")
			}else{
				// Logging the completion time
				frm.set_value('completion_time', frappe.datetime.now_datetime());
				frm.set_value('status', 'Completed');
				frm.save();
			}		
		} catch (error) {
			console.error('Error completing asset maintenance:', error);
		}
	},
	
	make_return_stock_entry: async function(frm) {
		try {
			// Call the server-side function directly using frappe.call
			const r = await frappe.call({
				method: 'erpnext.assets.doctype.asset_maintenance.asset_maintenance.make_return_stock_entry',
				freeze: true,
				freeze_message: __("Closing the Maintenance Document"),
				args: {
					'asset_maintenance_doc_ref': frm.doc.name
				}
			});
	
			if (r && r.message) {
				// If return stock entry flag is true, open the form for the newly created stock entry
				// Otherwise, close the plant maintenance document
				let return_stock_entry_flag = r.message.return_stock_entry_flag
				if (return_stock_entry_flag === true){
					let stock_entry = r.message.stock_entry;
					frappe.model.sync(stock_entry);
					frappe.set_route('Form', stock_entry.doctype, stock_entry.name);
				}else{
					frm.reload_doc();
				}
				
			}
		} catch (error) {
			console.error('Error making material consumption stock entry:', error);
			// Optionally handle error display or recovery
		}
	},

	// Function to manage workflow buttons dynamically
	manage_workflow_buttons: function(frm) {
		let status = frm.doc.status;

		if (status === "Not Started") {
			frm.add_custom_button(__('Start'), function () {
				in_process_validations(frm);
			}).addClass('btn-danger');
		} else if (status === "In Process") {
			frm.add_custom_button(__('Consumption'), function () {
				erpnext.asset_maintenance.make_material_consumption_stock_entry(frm);
			}).addClass('btn-primary');
			
			frm.add_custom_button(__('Complete'), function () {
				erpnext.asset_maintenance.complete_asset_maintenance(frm);
			}).addClass('btn-success');
			
			frm.add_custom_button('On Hold', function () {
				frm.set_value('status', 'Stopped');
				frm.save();
			}).addClass('btn-danger');

		} else if (status === "Completed") {
			frm.add_custom_button(__('Close'), function () {
				erpnext.asset_maintenance.make_return_stock_entry(frm);
			}).addClass('btn-danger');

		} else if (status === "Closed"){
			const buttons_to_remove = ['Start', 'Consumption', 'Completed']
			for (var i = 0; i < buttons_to_remove.length; i++) {
				this.frm.remove_custom_button(buttons_to_remove[i], __('Create'));
			}
		} else if (status === "Stopped") {	
			frm.add_custom_button(__('Resume'), function () {
				frm.set_value('status', 'In Process');
				frm.save();
			}).addClass('btn-danger');
			frm.add_custom_button(__('Close'), function () {
				erpnext.asset_maintenance.make_return_stock_entry(frm);
			}).addClass('btn-danger');

		}

	}
};

// Function to configure project-based fields
function project_frm_configuration(frm) {
	hide_add_rows(frm, 'consumed_items', true);	
	if (frm.doc.project_based === "Yes") {
		frm.toggle_display('get_project_tasks', 1);
		if (frm.doc.project){
			frm.set_df_property('project', 'read_only', 1);
		}else{
			frm.set_df_property('project', 'read_only', 0);
		}
		frm.set_df_property('project', 'reqd', 1);
		frm.set_df_property('project', 'hidden', 0);
		hide_add_rows(frm, 'asset_maintenance_tasks', true);
		
	} else {
		frm.set_df_property('project_based', 'read_only', 1);
		frm.toggle_display('get_project_tasks', 0);
		frm.set_df_property('project', 'read_only', 1);
		frm.set_df_property('project', 'reqd', 0);
		hide_add_rows(frm, 'asset_maintenance_tasks', false);
	}

	if (frm.doc.task){
		frm.set_df_property('task', 'read_only', 1);
	}
	if (frm.doc.maintenance_category){
		frm.set_df_property('maintenance_category', 'read_only', 1);
	}
	if (frm.doc.maintenance_type){
		frm.set_df_property('maintenance_type', 'read_only', 1);
	}

	/* In case of assets are fetched from Cost Centers, then user can not add assets, only he will be able 
	to delete assets from the child table. In case of assets are not fetched from Cost Centers, 
	then user can add or remove assets in child table, plant maintenance status is in progress.*/

	if(frm.doc.cost_center){
		frm.set_df_property('plant_maintenance_assets', 'cannot_add_rows', true);
	}else{
		frm.set_df_property('plant_maintenance_assets', 'cannot_add_rows', false);
	}

}


// Function to load assets based on cost center
function load_assets(frm) {
	if (!frm.doc.company) {
		frappe.throw("Select company first")
	}
	if (frm.doc.cost_center) {
		frappe.call({
			method: "erpnext.assets.doctype.asset_maintenance.asset_maintenance.get_assets",
			args: {
				company: frm.doc.company,
				cost_center: frm.doc.cost_center
			},
			freeze: true,
			freeze_message: __("Loading Assets"),
			callback: function (r) {
				
				if (r && r.message) {
					let assets = r.message
					frm.set_value('plant_maintenance_assets', []);
					for(let i = 0; i < assets.length; i++) {
						frm.add_child('plant_maintenance_assets', {
							asset: assets[i]['name'],
							asset_name: assets[i]['asset_name'],
							total_repair_count: assets[i]['repair_count'],
							cost_center: assets[i]['cost_center']
						})
					}
					frm.refresh_field('plant_maintenance_assets');

				}
			}
		});
	}
}

function hide_add_rows(frm, field, is_hide){
	if (is_hide) {
	frm.set_df_property(field, 'cannot_add_rows', is_hide);
	frm.set_df_property(field, 'cannot_delete_rows', is_hide);
	frm.set_df_property(field, 'cannot_delete_all_rows', is_hide);
	frm.fields_dict[field].grid.wrapper.find('.grid-remove-rows').hide();
	}else{
	frm.set_df_property(field, 'cannot_add_rows', is_hide);
	frm.set_df_property(field, 'cannot_delete_rows', is_hide);
	frm.set_df_property(field, 'cannot_delete_all_rows', is_hide);
	frm.fields_dict[field].grid.wrapper.find('.grid-remove-rows').show();
	}
}


function in_process_validations(frm){
	// Tasks cannot be empty when moving from Not Started to In Process
	if (frm.doc.asset_maintenance_tasks.length === 0) {
		frappe.throw(__('Please add maintenance tasks before starting the plant maintenance'));
	}

	// Assets cannot be empty when moving from Not Started to In Process
	if (frm.doc.plant_maintenance_assets.length === 0) {
		frappe.throw(__('Please add assets before starting the plant maintenance'));
	}
	// Logging the starting time
	if (frm.doc.status === "Not Started") {
		frm.set_value('starting_time', frappe.datetime.now_datetime());
	}
	frm.set_value('status', 'In Process');
	frm.save();
}