// Copyright (c) 2017, Frappe Technologies Pvt. Ltd. and contributors
// For license information, please see license.txt

var qty_manufactured = 0;
frappe.ui.form.on("Work Order", {
	setup: function(frm) {
		frm.custom_make_buttons = {
			'Stock Entry': 'Start',
			'Pick List': 'Create Pick List',
			'Job Card': 'Create Job Card'
		};

		// Set query for warehouses
		frm.set_query("wip_warehouse", function() {
			return {
				filters: {
					'company': frm.doc.company,
				}
			};
		});

		frm.set_query("source_warehouse", function() {
			return {
				filters: {
					'company': frm.doc.company,
				}
			};
		});

		frm.set_query("source_warehouse", "required_items", function() {
			return {
				filters: {
					'company': frm.doc.company,
				}
			};
		});

		frm.set_query("sales_order", function() {
			return {
				filters: {
					"status": ["not in", ["Closed", "On Hold"]]
				}
			};
		});

		frm.set_query("fg_warehouse", function() {
			return {
				filters: {
					'company': frm.doc.company,
					'is_group': 0
				}
			};
		});

		frm.set_query("scrap_warehouse", function() {
			return {
				filters: {
					'company': frm.doc.company,
					'is_group': 0
				}
			};
		});

		// Set query for BOM
		frm.set_query("bom_no", function() {
			if (frm.doc.production_item) {
				return {
					query: "erpnext.controllers.queries.bom",
					filters: {item: cstr(frm.doc.production_item)}
				};
			} else {
				frappe.msgprint(__("Please enter Production Item first"));
			}
		});

		// Set query for FG Item
		frm.set_query("production_item", function() {
			return {
				query: "erpnext.controllers.queries.item_query",
				filters:[
					['is_stock_item', '=',1],
					['default_bom', '!=', '']
				]
			};
		});

		// Set query for FG Item
		frm.set_query("project", function() {
			return{
				filters:[
					['Project', 'status', 'not in', 'Completed, Cancelled']
				]
			};
		});

		frm.set_query("operation", "required_items", function() {
			return {
				query: "erpnext.manufacturing.doctype.work_order.work_order.get_bom_operations",
				filters: {
					'parent': frm.doc.bom_no,
					'parenttype': 'BOM'
				}
			};
		});

		// formatter for work order operation
		frm.set_indicator_formatter('operation',
			function(doc) { return (frm.doc.qty==doc.completed_qty) ? "green" : "orange"; });
	},

	onload: function(frm) {
		if (!frm.doc.status)
			frm.doc.status = 'Draft';

		frm.add_fetch("sales_order", "project", "project");

		if(frm.doc.__islocal) {
			frm.set_value({
				"actual_start_date": "",
				"actual_end_date": ""
			});
			erpnext.work_order.set_default_warehouse(frm);
		}

		frm.set_df_property("required_items", "read_only", 1);
	    refresh_field("required_items");
		//samad added due to pp checks
		if(frm.doc.production_plan){
				frm.set_df_property("production_item", "read_only", 1);
				frm.set_df_property("bom_no", "read_only", 1);
				frm.set_df_property("item_section", "read_only", 1);
				frm.set_df_property("item_section", "read_only", 1);
				frm.set_df_property("uom", "read_only", 1);
			
			}
		// Set query for BOM
		frm.set_query("bom_no", function() {
			if (frm.doc.production_item && frm.doc.company) {
				return {
					query: "erpnext.controllers.queries.bom",
					filters: {item: cstr(frm.doc.production_item),company: cstr(frm.doc.company)}
				};
			} else {
				if(!frm.doc.production_item)
					frappe.msgprint(__("Please enter Production Item first"));
				if(!frm.doc.company)
					frappe.msgprint(__("Please enter Company first"));

			}
		});
		// 15-10-2021 - Ticket No(937) ===Ticket-937=== - Work order qty to manufacture issue
		qty_manufactured = frm.doc.qty;
	},

	source_warehouse: function(frm) {
		let transaction_controller = new erpnext.TransactionController();
		transaction_controller.autofill_warehouse(frm.doc.required_items, "source_warehouse", frm.doc.source_warehouse);
	},

	refresh: function(frm) {
		erpnext.toggle_naming_series();
		erpnext.work_order.set_custom_buttons(frm);
		frm.set_intro("");

		if (frm.doc.docstatus === 0 && !frm.doc.__islocal) {
			frm.set_intro(__("Submit this Work Order for further processing."));
		}

		if (frm.doc.docstatus===1) {
			frm.trigger('show_progress_for_items');
			frm.trigger('show_progress_for_operations');
		}

		if (frm.doc.docstatus === 1
			&& frm.doc.operations && frm.doc.operations.length
			&& frm.doc.qty != frm.doc.produced_qty) {

			const not_completed = frm.doc.operations.filter(d => {
				if(d.status != 'Completed') {
					return true;
				}
			});

			if(not_completed && not_completed.length) {
				frm.add_custom_button(__('Create Job Card'), () => {
					frm.trigger("make_job_card");
				}).addClass('btn-primary');
			}
		}

		if(frm.doc.required_items && frm.doc.allow_alternative_item) {
			const has_alternative = frm.doc.required_items.find(i => i.allow_alternative_item === 1);
			if (frm.doc.docstatus == 0 && has_alternative) {
				frm.add_custom_button(__('Alternate Item'), () => {
					erpnext.utils.select_alternate_items({
						frm: frm,
						child_docname: "required_items",
						warehouse_field: "source_warehouse",
						child_doctype: "Work Order Item",
						original_item_field: "original_item",
						condition: (d) => {
							if (d.allow_alternative_item) {return true;}
						}
					});
				});
			}
		}

		if (frm.doc.status == "Completed" &&
			frm.doc.__onload.backflush_raw_materials_based_on == "Material Transferred for Manufacture") {
			frm.add_custom_button(__('Create BOM'), () => {
				frm.trigger("make_bom");
			});
		}

		// Close button code in Custom Script moved here. Stop showing Close button in Work Order if CIP is in progress on the Cost Center/ Production Line
		if((frm.doc.status == 'Completed' || frm.doc.status == 'Stopped') && frm.doc.closed != 1 ){
			frappe.call({
				method: 'frappe.client.get_list',
				args: {
					doctype: 'Maintenance',
					field: ['name'],
					filters: {
						workflow_state: 'CIP Inprogress',
						cost_center: frm.doc.production_line,
						company: frm.doc.company
					}
				},
				callback: function(r) {
					if (r.message) {
						const csd_companies = ['Unit 5', 'Unit 8', 'Unit 11'];
						let remove_close_button_due_to_cip = false;

						if (r.message.length > 0 && csd_companies.includes(frm.doc.company)) {
							remove_close_button_due_to_cip = true;
						}

						if (!remove_close_button_due_to_cip) {
							frm.add_custom_button(__("Close"), function() {
								frappe.call({
									method: "nrp_manufacturing.modules.gourmet.work_order.work_order.close_work_order",
									args: {
										work_order: frm.doc.name,
										status : frm.doc.status
									},
									callback: function(r) {
										if(r.message) {
											let stock_entry = r.message;
											if(isEmpty(stock_entry)){
											location.reload()
											}else{
												frappe.model.sync(stock_entry);
												frappe.set_route('Form', stock_entry.doctype, stock_entry.name);
											}
										}
									}
								});
							}).addClass("btn-primary");
						}
					}
				}
			});
        }

		frm.set_df_property("required_items", "read_only", 1);
	    refresh_field("required_items");

		if(frm.doc.closed == 1){
            frm.remove_custom_button("Re-open","Status");
            frm.remove_custom_button("Returnable Transfer");
        }

		if((frm.doc.status == 'Completed' || frm.doc.status == 'Stopped') && frm.doc.closed != 1 ){
            frm.add_custom_button(__("Close"), function() {
                frappe.call({
        			method: "nrp_manufacturing.modules.gourmet.work_order.work_order.close_work_order",
        			args: {
        				work_order: frm.doc.name,
        				status : frm.doc.status
        			},
        			callback: function(r) {
        				if(r.message) {
        				    let stock_entry = r.message;
        				    if(isEmpty(stock_entry)){
            				   location.reload()
        				    }else{
        				        frappe.model.sync(stock_entry);
    				            frappe.set_route('Form', stock_entry.doctype, stock_entry.name);
        				    }
        				}
        			}
        		});
            }).addClass("btn-primary");
        }

		if((frm.doc.status == 'Completed' || frm.doc.status == 'Stopped') && frm.doc.has_returnable && frm.doc.production_return != 1 &&  frm.doc.closed != 1 ){
            frm.add_custom_button(__("Returnable Transfer"), function() {
                frappe.call({
        			method: "nrp_manufacturing.modules.gourmet.work_order.work_order.returnable_transfer_entry",
        			args: {
        				work_order: frm.doc.name
        			},
        			callback: function(r) {
        				if(r.message) {
        				    let stock_entry = r.message;
        				    if(isEmpty(stock_entry)){
            				   location.reload()
        				    }else{
        				        frappe.model.sync(stock_entry);
    				            frappe.set_route('Form', stock_entry.doctype, stock_entry.name);
        				    }
        				}
        			}
        		});
            }).addClass("btn-primary");
        }

		if((frm.doc.status == 'Completed' || frm.doc.status == 'Stopped') && frm.doc.has_returnable && frm.doc.production_return == 1 && frm.doc.waste_return != 1 &&  frm.doc.closed != 1 ){
            frm.add_custom_button(__("Returnable Wastage"), function() {
                frappe.call({
        			method: "nrp_manufacturing.modules.gourmet.work_order.work_order.returnable_transfer_entry",
        			args: {
        				work_order: frm.doc.name,
        				status : 1
        			},
        			callback: function(r) {
        				if(r.message) {
        				    let stock_entry = r.message;
        				    if(isEmpty(stock_entry)){
            				   location.reload()
        				    }else{
        				        frappe.model.sync(stock_entry);
    				            frappe.set_route('Form', stock_entry.doctype, stock_entry.name);
        				    }
        				}
        			}
        		});
            }).addClass("btn-primary");
        }

	},
	// ===Ticket-937===
	item_section: function(frm){
		if(frm.doc.item_section){
		   // frm.set_value("for_warehouse", "");
			frappe.db.get_doc("Section", frm.doc.item_section)
			.then(doc => {
				if(doc){
					doc.section_warehouse.forEach(function(element){
						if(element.company == frm.doc.company){
							frm.set_value("wip_warehouse", element.wip_warehouse);
							frm.refresh_field("wip_warehouse");
							
							frm.set_value("fg_warehouse", element.finished_goods_warehouse);
							frm.refresh_field("fg_warehouse");
							
							frm.set_value("scrap_warehouse", element.scrap_warehouse);
							frm.refresh_field("scrap_warehouse");
						} 
					});
				}
			});
		}

		let item_sections = ["FG CSD","FG Juices","FG RGB","FG Water", "FG Bulk Water", "SF Juices", "SF Syrup","FG Husky"];
		if (item_sections.includes(frm.doc.item_section)) {
			frm.toggle_display("production_line",true);
			frm.toggle_display("production_line", true);

			// Fetch Cost Center names where is_parent_asset = 1 and company = frm.doc.company
			if (frm.doc.company) {
				frappe.call({
					method: "frappe.client.get_list",
					args: {
						doctype: "Cost Center",
						filters: {
							is_parent_asset: 1,
							company: frm.doc.company
						},
						fields: ["name"]
					},
					callback: function(r) {
						if (r.message) {
							// Extract the names from the response
							let options = r.message.map(row => row.name);
	
							// Update the options for the production_line field
							frm.set_df_property("production_line", "options", options.join("\n"));
						}
					}
				});
			} else {
				// Clear options if company is not set
				frm.set_df_property("production_line", "options", "");
			}
		}
		else{
			frm.doc.production_line = '';
			frm.refresh_field('production_line');
			frm.set_df_property("production_line", "reqd", 0);
			frm.toggle_display("production_line",false);
			frm.refresh_field('production_line');
		}

	},
	production_item: function(frm) {
		if (frm.doc.production_item) {
			frappe.call({
				method: "erpnext.manufacturing.doctype.work_order.work_order.get_item_details",
				args: {
					item: frm.doc.production_item,
					project: frm.doc.project,
					company: frm.doc.company
				},
				freeze: true,
				callback: function(r) {
					if(r.message) {
						frm.set_value('sales_order', "");
						frm.trigger('set_sales_order');
						erpnext.in_production_item_onchange = true;

						$.each(["description", "stock_uom", "project", "bom_no", "allow_alternative_item",
							"transfer_material_against", "item_name"], function(i, field) {
							frm.set_value(field, r.message[field]);
						});

						if(r.message["set_scrap_wh_mandatory"]){
							frm.toggle_reqd("scrap_warehouse", true);
						}
						erpnext.in_production_item_onchange = false;
					}
				}
			});
		}
	},
	make_job_card: function(frm) {
		let qty = 0;
		let operations_data = [];

		const dialog = frappe.prompt({fieldname: 'operations', fieldtype: 'Table', label: __('Operations'),
			fields: [
				{
					fieldtype:'Link',
					fieldname:'operation',
					label: __('Operation'),
					read_only:1,
					in_list_view:1
				},
				{
					fieldtype:'Link',
					fieldname:'workstation',
					label: __('Workstation'),
					read_only:1,
					in_list_view:1
				},
				{
					fieldtype:'Data',
					fieldname:'name',
					label: __('Operation Id')
				},
				{
					fieldtype:'Float',
					fieldname:'pending_qty',
					label: __('Pending Qty'),
				},
				{
					fieldtype:'Float',
					fieldname:'qty',
					label: __('Quantity to Manufacture'),
					read_only:0,
					in_list_view:1,
				},
			],
			data: operations_data,
			in_place_edit: true,
			get_data: function() {
				return operations_data;
			}
		}, function(data) {
			frappe.call({
				method: "erpnext.manufacturing.doctype.work_order.work_order.make_job_card",
				args: {
					work_order: frm.doc.name,
					operations: data.operations,
				}
			});
		}, __("Job Card"), __("Create"));

		dialog.fields_dict["operations"].grid.wrapper.find('.grid-add-row').hide();

		var pending_qty = 0;
		frm.doc.operations.forEach(data => {
			if(data.completed_qty != frm.doc.qty) {
				pending_qty = frm.doc.qty - flt(data.completed_qty);

				dialog.fields_dict.operations.df.data.push({
					'name': data.name,
					'operation': data.operation,
					'workstation': data.workstation,
					'qty': pending_qty,
					'pending_qty': pending_qty,
				});
			}
		});
		dialog.fields_dict.operations.grid.refresh();
	},

	make_bom: function(frm) {
		frappe.call({
			method: "make_bom",
			doc: frm.doc,
			callback: function(r){
				if (r.message) {
					var doc = frappe.model.sync(r.message)[0];
					frappe.set_route("Form", doc.doctype, doc.name);
				}
			}
		});
	},

	show_progress_for_items: function(frm) {
		var bars = [];
		var message = '';
		var added_min = false;

		// produced qty
		var title = __('{0} items produced', [frm.doc.produced_qty]);
		bars.push({
			'title': title,
			'width': (frm.doc.produced_qty / frm.doc.qty * 100) + '%',
			'progress_class': 'progress-bar-success'
		});
		if (bars[0].width == '0%') {
			bars[0].width = '0.5%';
			added_min = 0.5;
		}
		message = title;
		// pending qty
		if(!frm.doc.skip_transfer){
			var pending_complete = frm.doc.material_transferred_for_manufacturing - frm.doc.produced_qty;
			if(pending_complete) {
				var width = ((pending_complete / frm.doc.qty * 100) - added_min);
				title = __('{0} items in progress', [pending_complete]);
				bars.push({
					'title': title,
					'width': (width > 100 ? "99.5" : width)  + '%',
					'progress_class': 'progress-bar-warning'
				});
				message = message + '. ' + title;
			}
		}
		frm.dashboard.add_progress(__('Status'), bars, message);
	},

	show_progress_for_operations: function(frm) {
		if (frm.doc.operations && frm.doc.operations.length) {

			let progress_class = {
				"Work in Progress": "progress-bar-warning",
				"Completed": "progress-bar-success"
			};

			let bars = [];
			let message = '';
			let title = '';
			let status_wise_oprtation_data = {};
			let total_completed_qty = frm.doc.qty * frm.doc.operations.length;

			frm.doc.operations.forEach(d => {
				if (!status_wise_oprtation_data[d.status]) {
					status_wise_oprtation_data[d.status] = [d.completed_qty, d.operation];
				} else {
					status_wise_oprtation_data[d.status][0] += d.completed_qty;
					status_wise_oprtation_data[d.status][1] += ', ' + d.operation;
				}
			});

			for (let key in status_wise_oprtation_data) {
				title = __("{0} Operations: {1}", [key, status_wise_oprtation_data[key][1].bold()]);
				bars.push({
					'title': title,
					'width': status_wise_oprtation_data[key][0] / total_completed_qty * 100  + '%',
					'progress_class': progress_class[key]
				});

				message += title + '. ';
			}

			frm.dashboard.add_progress(__('Status'), bars, message);
		}
	},

	production_item: function(frm) {
		if (frm.doc.production_item) {
			frappe.call({
				method: "erpnext.manufacturing.doctype.work_order.work_order.get_item_details",
				args: {
					item: frm.doc.production_item,
					project: frm.doc.project,
					company: frm.doc.company
				},
				freeze: true,
				callback: function(r) {
					if(r.message) {
						frm.set_value('sales_order', "");
						frm.trigger('set_sales_order');
						erpnext.in_production_item_onchange = true;

						$.each(["description", "stock_uom", "project", "bom_no", "allow_alternative_item",
							"transfer_material_against", "item_name"], function(i, field) {
							frm.set_value(field, r.message[field]);
						});

						if(r.message["set_scrap_wh_mandatory"]){
							frm.toggle_reqd("scrap_warehouse", true);
						}
						erpnext.in_production_item_onchange = false;
					}
				}
			});
		}
	},

	project: function(frm) {
		if(!erpnext.in_production_item_onchange && !frm.doc.bom_no) {
			frm.trigger("production_item");
		}
	},

	bom_no: function(frm) {
		return frm.call({
			doc: frm.doc,
			method: "get_items_and_operations_from_bom",
			freeze: true,
			callback: function(r) {
				if(r.message["set_scrap_wh_mandatory"]){
					frm.toggle_reqd("scrap_warehouse", true);
				}
			}
		});
	},

	use_multi_level_bom: function(frm) {
		if(frm.doc.bom_no) {
			frm.trigger("bom_no");
		}
	},


	qty: function(frm){
		//frm.trigger('bom_no');
	    if(frm.doc.qty > qty_manufactured){
	        frm.doc.qty = qty_manufactured;
	        frappe.msgprint(__("You cannot exceeds qty more then "+qty_manufactured))
	        refresh_field('qty')
	    }
	    console.log(frm.doc.production_plan);
	    if(frm.doc.production_plan !== ''){
	        console.log(frm.doc.planned_start_date);
	        if(frm.doc.planned_start_date === ''){
	            frm.doc.push('planned_start_date',frm.doc.creation);
	        }
	        console.log(frm.doc.planned_start_date);
	    }
	    frm.trigger('bom_no');
	},

	before_submit: function(frm) {
		frm.toggle_reqd(["fg_warehouse", "wip_warehouse"], true);
		frm.fields_dict.required_items.grid.toggle_reqd("source_warehouse", true);
		frm.toggle_reqd("transfer_material_against",
			frm.doc.operations && frm.doc.operations.length > 0);
		frm.fields_dict.operations.grid.toggle_reqd("workstation", frm.doc.operations);
	},

	company: function(frm) {
		// CIP QA Sheet - Point 23
		const csd_companies = ['Unit 5', 'Unit 8', 'Unit 11'];
		if (csd_companies.includes(frm.doc.company)) {
			if (frm.doc.company) {
				frappe.call({
					method: "frappe.client.get_list",
					args: {
						doctype: "Cost Center",
						filters: {
							is_parent_asset: 1,
							company: frm.doc.company
						},
						fields: ["name"]
					},
					callback: function(r) {
						if (r.message) {
							let options = r.message.map(row => row.name);
							frm.set_df_property("production_line", "options", options.join("\n"));
						}
					}
				});
			}
		}
	},

	before_save: function(frm) {
		// CIP QA Sheet - Point 23
		const csd_companies = ['Unit 5', 'Unit 8', 'Unit 11'];
		const item_sections = ["FG CSD","FG Juices","FG RGB","FG Water", "FG Bulk Water", "SF Juices", "SF Syrup","FG Husky"];
		if (csd_companies.includes(frm.doc.company)) {
			if ((!frm.doc.production_line || frm.doc.production_line.length < 1 ) && item_sections.includes(frm.doc.item_section)) {
				frappe.throw(__("Production Line is Mandatory"))
			}
		}
	},

	set_sales_order: function(frm) {
		if(frm.doc.production_item) {
			frappe.call({
				method: "erpnext.manufacturing.doctype.work_order.work_order.query_sales_order",
				args: { production_item: frm.doc.production_item },
				callback: function(r) {
					frm.set_query("sales_order", function() {
						erpnext.in_production_item_onchange = true;
						return {
							filters: [
								["Sales Order","name", "in", r.message]
							]
						};
					});
				}
			});
		}
	},

	additional_operating_cost: function(frm) {
		erpnext.work_order.calculate_cost(frm.doc);
		erpnext.work_order.calculate_total_cost(frm);
	}
});

frappe.ui.form.on("Work Order Item", {
	source_warehouse: function(frm, cdt, cdn) {
		var row = locals[cdt][cdn];
		if(!row.item_code) {
			frappe.throw(__("Please set the Item Code first"));
		} else if(row.source_warehouse) {
			frappe.call({
				"method": "erpnext.stock.utils.get_latest_stock_qty",
				args: {
					item_code: row.item_code,
					warehouse: row.source_warehouse
				},
				callback: function (r) {
					frappe.model.set_value(row.doctype, row.name,
						"available_qty_at_source_warehouse", r.message);
				}
			});
		}
	}
});

frappe.ui.form.on("Work Order Operation", {
	workstation: function(frm, cdt, cdn) {
		var d = locals[cdt][cdn];
		if (d.workstation) {
			frappe.call({
				"method": "frappe.client.get",
				args: {
					doctype: "Workstation",
					name: d.workstation
				},
				callback: function (data) {
					frappe.model.set_value(d.doctype, d.name, "hour_rate", data.message.hour_rate);
					erpnext.work_order.calculate_cost(frm.doc);
					erpnext.work_order.calculate_total_cost(frm);
				}
			});
		}
	},
	time_in_mins: function(frm, cdt, cdn) {
		erpnext.work_order.calculate_cost(frm.doc);
		erpnext.work_order.calculate_total_cost(frm);
	},
});

erpnext.work_order = {
	set_custom_buttons: function(frm) {
		var doc = frm.doc;
		if (doc.docstatus === 1) {
			if (doc.status != 'Stopped' && doc.status != 'Completed') {
				frm.add_custom_button(__('Stop'), function() {
					erpnext.work_order.stop_work_order(frm, "Stopped");
				}, __("Status"));
			} else if (doc.status == 'Stopped') {
				frm.add_custom_button(__('Re-open'), function() {
					erpnext.work_order.stop_work_order(frm, "Resumed");
				}, __("Status"));
			}

			let csd_company_list = ['Unit 11','Unit 8','Unit 5'];
			let company = frm.doc.company;

			if (csd_company_list.includes(company)) {
				var work_activity_report = frm.add_custom_button(__('Work Order Activity Report'), function() {
					const work_order_name = frm.doc.name;
					window.open(`/desk#query-report/CSD%20Work%20Order%20Activity%20Report?work_order_id=${encodeURIComponent(work_order_name)}`, '_blank');
				});
				work_activity_report.addClass('btn-secondary');
			}

			const show_start_btn = (frm.doc.skip_transfer
				|| frm.doc.transfer_material_against == 'Job Card') ? 0 : 1;

			if (show_start_btn) {
				if ((flt(doc.material_transferred_for_manufacturing) < flt(doc.qty))
					&& frm.doc.status != 'Stopped' && frm.doc.status != 'Completed') {
					frm.has_start_btn = true;
					frm.add_custom_button(__('Create Pick List'), function() {
						erpnext.work_order.create_pick_list(frm);
					});
					var start_btn = frm.add_custom_button(__('Start'), function() {
						const csd_companies = ['Unit 5', 'Unit 8', 'Unit 11'];
						if (csd_companies.includes(frm.doc.company)) {
							frappe.call({
								method: 'frappe.client.get_list',
								args: {
									doctype: 'Maintenance',
									field: ['name'],
									filters: {
										workflow_state: 'CIP Inprogress',
										cost_center: frm.doc.production_line
									}
								},
								callback: function(r) {
									if (r.message && r.message.length > 0) {
										frappe.throw(__(`Can not start a Work Order on line ${frm.doc.production_line} as CIP is in progress`));
									} else {
										erpnext.work_order.make_se(frm, 'Material Transfer for Manufacture');
									}
								}
							});
						} else {
							erpnext.work_order.make_se(frm, 'Material Transfer for Manufacture');
						}
					});
					start_btn.addClass('btn-primary');
				}
			}

			if(!frm.doc.skip_transfer){
				// If "Material Consumption is check in Manufacturing Settings, allow Material Consumption
				if ((flt(doc.produced_qty) < flt(doc.material_transferred_for_manufacturing))
				&& frm.doc.status != 'Stopped' && frm.doc.status != 'Completed') {
					frm.has_finish_btn = true;

					if (frm.doc.__onload && frm.doc.__onload.material_consumption == 1) {
						// Only show "Material Consumption" when required_qty > consumed_qty
						var counter = 0;
						var tbl = frm.doc.required_items || [];
						var tbl_lenght = tbl.length;
						for (var i = 0, len = tbl_lenght; i < len; i++) {
							let wo_item_qty = frm.doc.required_items[i].transferred_qty || frm.doc.required_items[i].required_qty;
							if (flt(wo_item_qty) > flt(frm.doc.required_items[i].consumed_qty)) {
								counter += 1;
							}
						}
						if (counter > 0) {
							var consumption_btn = frm.add_custom_button(__('Material Consumption'), function() {
								const backflush_raw_materials_based_on = frm.doc.__onload.backflush_raw_materials_based_on;
								erpnext.work_order.make_consumption_se(frm, backflush_raw_materials_based_on);
							});
							consumption_btn.addClass('btn-primary');
						}
					}

					let companies_list = ['Unit 11','Unit 8','Unit 5'];
					let company = frm.doc.company

						if (companies_list.includes(company)){
							var damage_return_btn = frm.add_custom_button(__('Return WIP Damage'), function() {
								erpnext.work_order.make_damage_return_se(frm);
							});
							damage_return_btn.addClass('btn-secondary');	
						}
					
					// Code by Moeiz to allow maintenance CIP button for CSD
					let maintenance_allowed_companies = ['Unit 5', 'Unit 8', 'Unit 11'];
					if (maintenance_allowed_companies.includes(company)){
						var maintenance_btn = frm.add_custom_button(__('Downtime'), function() {
							erpnext.work_order.make_cip_maintenance_document(frm);
						});
						maintenance_btn.addClass('btn-secondary');
					}


					var finish_btn = frm.add_custom_button(__('Finish'), function() {
						erpnext.work_order.make_se(frm, 'Manufacture');
					});

					if(doc.material_transferred_for_manufacturing>=doc.qty) {
						// all materials transferred for manufacturing, make this primary
						finish_btn.addClass('btn-primary');
					}
				}
			} else {
				if ((flt(doc.produced_qty) < flt(doc.qty)) && frm.doc.status != 'Stopped') {

					let companies_list = ['Unit 11','Unit 8','Unit 5'];
					let company = frm.doc.company
					if (companies_list.includes(company)){
						var damage_return_btn = frm.add_custom_button(__('Return WIP Damage'), function() {
							erpnext.work_order.make_damage_return_se(frm);
						});
						damage_return_btn.addClass('btn-secondary');	
					}

					// Code by Moeiz to allow maintenance CIP button for CSD
					let maintenance_allowed_companies = ['Unit 5', 'Unit 8', 'Unit 11'];
					if (maintenance_allowed_companies.includes(company)){
						var maintenance_btn = frm.add_custom_button(__('Downtime'), function() {
							erpnext.work_order.make_cip_maintenance_document(frm);
						});
						maintenance_btn.addClass('btn-secondary');
					}
					
					var finish_btn = frm.add_custom_button(__('Finish'), function() {
						erpnext.work_order.make_se(frm, 'Manufacture');
					});
					finish_btn.addClass('btn-primary');
				}
			}
		}

	},
	calculate_cost: function(doc) {
		if (doc.operations){
			var op = doc.operations;
			doc.planned_operating_cost = 0.0;
			for(var i=0;i<op.length;i++) {
				var planned_operating_cost = flt(flt(op[i].hour_rate) * flt(op[i].time_in_mins) / 60, 2);
				frappe.model.set_value('Work Order Operation', op[i].name,
					"planned_operating_cost", planned_operating_cost);
				doc.planned_operating_cost += planned_operating_cost;
			}
			refresh_field('planned_operating_cost');
		}
	},

	calculate_total_cost: function(frm) {
		let variable_cost = flt(frm.doc.actual_operating_cost) || flt(frm.doc.planned_operating_cost);
		frm.set_value("total_operating_cost", (flt(frm.doc.additional_operating_cost) + variable_cost));
	},

	set_default_warehouse: function(frm) {
		if (!(frm.doc.wip_warehouse || frm.doc.fg_warehouse)) {
			frappe.call({
				method: "erpnext.manufacturing.doctype.work_order.work_order.get_default_warehouse",
				callback: function(r) {
					if (!r.exe) {
						frm.set_value("wip_warehouse", r.message.wip_warehouse);
						frm.set_value("fg_warehouse", r.message.fg_warehouse);
					}
				}
			});
		}
	},

	get_max_transferable_qty: (frm, purpose) => {
		let max = 0;
		if (frm.doc.skip_transfer) {
			max = flt(frm.doc.qty) - flt(frm.doc.produced_qty);
		} else {
			if (purpose === 'Manufacture') {
				max = flt(frm.doc.material_transferred_for_manufacturing) - flt(frm.doc.produced_qty);
			} else {
				max = flt(frm.doc.qty) - flt(frm.doc.material_transferred_for_manufacturing);
			}
		}
		return flt(max, precision('qty'));
	},

	show_prompt_for_qty_input: function(frm, purpose) {
		let max = this.get_max_transferable_qty(frm, purpose);
		return new Promise((resolve, reject) => {
			frappe.prompt({
				fieldtype: 'Float',
				label: __('Qty for {0}', [purpose]),
				fieldname: 'qty',
				description: __('Max: {0}', [max]),
				default: max
			}, data => {
				max += (frm.doc.qty * (frm.doc.__onload.overproduction_percentage || 0.0)) / 100;

				if (data.qty > max) {
					frappe.msgprint(__('Quantity must not be more than {0}', [max]));
					reject();
				}
				data.purpose = purpose;
				resolve(data);
			}, __('Select Quantity'), __('Create'));
		});
	},

	make_se: function(frm, purpose) {
		this.show_prompt_for_qty_input(frm, purpose)
			.then(data => {
				return frappe.xcall('erpnext.manufacturing.doctype.work_order.work_order.make_stock_entry', {
					'work_order_id': frm.doc.name,
					'purpose': purpose,
					'qty': data.qty
				});
			}).then(stock_entry => {
				frappe.model.sync(stock_entry);
				frappe.set_route('Form', stock_entry.doctype, stock_entry.name);
			});

	},

	make_damage_return_se: async function(frm) {
		try {
			// Call the server-side function directly using frappe.call
			const r = await frappe.call({
				method: 'nrp_manufacturing.modules.gourmet.work_order.work_order.create_damage_stock_entry',
				args: {
					'work_order': frm.doc.name
				}
			});
	
			if (r && r.message) {
				// Sync the returned stock entry with the local model
				frappe.model.sync(r.message);
				// Open the form for the newly created stock entry
				frappe.set_route('Form', r.message.doctype, r.message.name);
			}
		} catch (error) {
			console.error('Error making damage return stock entry:', error);
			// Optionally handle error display or recovery
		}
	},

	make_cip_maintenance_document: async function(frm) {
		try {
			// Call the server-side function directly using frappe.call
			const r = await frappe.call({
				method: 'nrp_manufacturing.modules.gourmet.work_order.work_order.create_cip_maintenance_document',
				args: {
					'work_order': frm.doc.name
				}
			});
	
			if (r && r.message) {
				frappe.model.sync(r.message);
				frappe.set_route('Form', r.message.doctype, r.message.name);
			}
		} catch (error) {
			console.error('Error making cip maintenance document:', error);
		}
	},

	create_pick_list: function(frm, purpose='Material Transfer for Manufacture') {
		this.show_prompt_for_qty_input(frm, purpose)
			.then(data => {
				return frappe.xcall('erpnext.manufacturing.doctype.work_order.work_order.create_pick_list', {
					'source_name': frm.doc.name,
					'for_qty': data.qty
				});
			}).then(pick_list => {
				frappe.model.sync(pick_list);
				frappe.set_route('Form', pick_list.doctype, pick_list.name);
			});
	},

	make_consumption_se: function(frm, backflush_raw_materials_based_on) {
		if(!frm.doc.skip_transfer){
			var max = (backflush_raw_materials_based_on === "Material Transferred for Manufacture") ?
				flt(frm.doc.material_transferred_for_manufacturing) - flt(frm.doc.produced_qty) :
				flt(frm.doc.qty) - flt(frm.doc.produced_qty);
				// flt(frm.doc.qty) - flt(frm.doc.material_transferred_for_manufacturing);
		} else {
			var max = flt(frm.doc.qty) - flt(frm.doc.produced_qty);
		}

		frappe.call({
			method:"erpnext.manufacturing.doctype.work_order.work_order.make_stock_entry",
			args: {
				"work_order_id": frm.doc.name,
				"purpose": "Material Consumption for Manufacture",
				"qty": max
			},
			callback: function(r) {
				var doclist = frappe.model.sync(r.message);
				frappe.set_route("Form", doclist[0].doctype, doclist[0].name);
			}
		});
	},

	stop_work_order: function(frm, status) {
		frappe.call({
			method: "erpnext.manufacturing.doctype.work_order.work_order.stop_unstop",
			args: {
				work_order: frm.doc.name,
				status: status
			},
			callback: function(r) {
				if(r.message) {
					frm.set_value("status", r.message);
					frm.reload_doc();
				}
			}
		});
	}
};


// Utility function to check if an object is empty
function isEmpty(obj) {
    return Object.keys(obj).length === 0;
}
