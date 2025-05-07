// Copyright (c) 2015, Frappe Technologies Pvt. Ltd. and Contributors
// License: GNU General Public License v3. See license.txt

// eslint-disable-next-line
{% include 'erpnext/public/js/controllers/buying.js' %};

var SUB_TYPES_FOR_STW = ['Shipping', 'Special Order', 'Live Baking'];
frappe.ui.form.on('Material Request', {
	setup: function(frm) {
		frm.custom_make_buttons = {
			'Stock Entry': 'Issue Material',
			'Pick List': 'Pick List',
			'Purchase Order': 'Purchase Order',
			'Request for Quotation': 'Request for Quotation',
			'Supplier Quotation': 'Supplier Quotation',
			'Work Order': 'Work Order'
		};

		// formatter for material request item
		frm.set_indicator_formatter('item_code',
			function(doc) { return (doc.stock_qty<=doc.ordered_qty) ? "green" : "orange"; });

		frm.set_query("from_warehouse", "items", function(doc) {
			return {
				filters: {'company': doc.company}
			};
		});

	},

	// onload: function(frm) {
	// 	// add item, if previous view was item
	// 	erpnext.utils.add_item(frm);

	// 	// set schedule_date
	// 	set_schedule_date(frm);

	// 	frm.set_query("warehouse", "items", function(doc) {
	// 		return {
	// 			filters: {'company': doc.company}
	// 		};
	// 	});

	// 	frm.set_query("set_warehouse", function(doc){
	// 		return {
	// 			filters: {'company': doc.company}
	// 		};
	// 	});

	// 	frm.set_query("set_from_warehouse", function(doc){
	// 		return {
	// 			filters: {'company': doc.company}
	// 		};
	// 	});
		
	// 	if(frm.doc.material_request_type == "Purchase"){
	// 		frm.get_field("items").grid.toggle_enable("uom", 0);
	// 		frm.get_field("items").grid.toggle_enable("item_name", 0);
	// 		refresh_field("items");
	// 	}
	// },

	onload: function(frm, cdt, cdn) {
        if (frm.doc.docstatus != undefined && frm.doc.docstatus == 1){
            frm.set_df_property('schedule_date','read_only',1);
        }
		frm.set_query("item_code", "items", function() {
			if (frm.doc.material_request_type == "Customer Provided") {
				return{
					query: "erpnext.controllers.queries.item_query",
					filters:{ 'customer': frm.doc.customer }
				}
			} else if (frm.doc.material_request_type != "Manufacture" && frm.doc.material_request_type != "Material Transfer") {
				return{
					query: "erpnext.controllers.queries.item_query",
					filters: {'is_purchase_item': 1}
				}
			}
		});
	},

	material_request_type: function(frm) {
		if(frm.doc.material_request_type == "Purchase"){
			frm.get_field("items").grid.toggle_enable("uom", 0);
			frm.get_field("items").grid.toggle_enable("item_name", 0);
			refresh_field("items");
		}
	},

	company:function(frm){
		frm.set_value("items",[]);
		refresh_field("items");
		frappe.call({
			method:"nrp_manufacturing.modules.gourmet.material_request.material_request.delete_mr_items",
			args: {
				"data": frm.doc.name
			}
		});

		frappe.db.get_value("Company", {"name": frm.doc.company}, "abbr", (r) => {
	        if (r && r.abbr) {
	            let str = "%- " + r.abbr;

	            frm.set_query("sub_branch", function() {
	                return {
        				filters: {
        					name: ["like", str]
        				}
        			}
	            })

	        }
		})
		frm.set_value("sub_branch", null);
		refresh_field("sub_branch");
		
		frm.trigger("sub_branch");
		
		project_based_configurations(frm);
	},

	onload_post_render: function(frm) {
		frm.get_field("items").grid.set_multiple_add("item_code", "qty");
	},

	refresh: function(frm) {
		frm.events.make_custom_buttons(frm);
		frm.toggle_reqd('customer', frm.doc.material_request_type=="Customer Provided");

		if(frm.doc.material_request_type == "Purchase"){
			frm.get_field("items").grid.toggle_enable("uom", 0);
			frm.get_field("items").grid.toggle_enable("item_name", 0);
			refresh_field("items");
		}

		if (frm.doc.material_request_type == "Material Issue"){
            frm.get_field("items").grid.toggle_enable("expense_account", 0);
            refresh_field("items");
        }

		frm.set_query("sub_type", function() {
            let filters = {
                "parent_type": frm.doc.material_request_type
            }
            return {
                "filters": filters
            };
        });
        
        frm.refresh_field("items");
            
        if(frm.docstatus == 0)
        {
            frm.trigger("sub_type");
            frm.trigger("company");
        }
        
        if(frm.doc.material_request_type == 'Material Issue' ){
    	   frm.set_df_property("sub_branch", "reqd", 1);
    	   frm.set_df_property("cost_association", "reqd", 1);
	    }
    	else{
    	   frm.set_df_property("sub_branch", "reqd", 0);
    	   frm.set_df_property("cost_association", "reqd", 0);
    	}
    	
    	frm.set_query('warehouse', 'items', function(doc, cdt, cdn) {
			return {
				"filters": {
					"company": frm.doc.company,
				}
			};
		});
		
		if (frm.doc.material_request_type == "Purchase" && frm.doc.docstatus == 1) {
			frm.add_custom_button(__('Select Project'), function() {
				show_project_selection_modal(frm);
			});
		}

		project_based_configurations(frm);

	},

	make_custom_buttons: function(frm) {
		if (frm.doc.docstatus==0) {
			frm.add_custom_button(__("Bill of Materials"),
				() => frm.events.get_items_from_bom(frm), __("Get items from"));
		}

		if (frm.doc.docstatus == 1 && frm.doc.status != 'Stopped') {
			if (flt(frm.doc.per_ordered, 2) < 100) {
				let add_create_pick_list_button = () => {
					frm.add_custom_button(__('Pick List'),
						() => frm.events.create_pick_list(frm), __('Create'));
				}

				if (frm.doc.material_request_type === "Material Transfer") {
					add_create_pick_list_button();
					frm.add_custom_button(__("Transfer Material"),
						() => frm.events.make_stock_entry(frm), __('Create'));
				}

				if (frm.doc.material_request_type === "Material Issue") {
					frm.add_custom_button(__("Issue Material"),
						() => frm.events.make_stock_entry(frm), __('Create'));
				}

				if (frm.doc.material_request_type === "Customer Provided") {
					frm.add_custom_button(__("Material Receipt"),
						() => frm.events.make_stock_entry(frm), __('Create'));
				}

				if (frm.doc.material_request_type === "Purchase") {
					frm.add_custom_button(__('Purchase Order'),
						() => frm.events.make_purchase_order(frm), __('Create'));
				}

				if (frm.doc.material_request_type === "Purchase") {
					frm.add_custom_button(__("Request for Quotation"),
						() => frm.events.make_request_for_quotation(frm), __('Create'));
				}

				if (frm.doc.material_request_type === "Purchase") {
					frm.add_custom_button(__("Supplier Quotation"),
						() => frm.events.make_supplier_quotation(frm), __('Create'));
				}

				if (frm.doc.material_request_type === "Manufacture") {
					frm.add_custom_button(__("Work Order"),
						() => frm.events.raise_work_orders(frm), __('Create'));
				}

				frm.page.set_inner_btn_group_as_primary(__('Create'));

				// stop
				frm.add_custom_button(__('Stop'),
					() => frm.events.update_status(frm, 'Stopped'));

			}
		}

		if (frm.doc.docstatus===0) {
			frm.add_custom_button(__('Sales Order'), () => frm.events.get_items_from_sales_order(frm),
				__("Get items from"));
		}

		if (frm.doc.docstatus == 1 && frm.doc.status == 'Stopped') {
			frm.add_custom_button(__('Re-open'), () => frm.events.update_status(frm, 'Submitted'));
		}
	},

	update_status: function(frm, stop_status) {
		frappe.call({
			method: 'erpnext.stock.doctype.material_request.material_request.update_status',
			args: { name: frm.doc.name, status: stop_status },
			callback(r) {
				if (!r.exc) {
					frm.reload_doc();
				}
			}
		});
	},

	get_items_from_sales_order: function(frm) {
		erpnext.utils.map_current_doc({
			method: "erpnext.selling.doctype.sales_order.sales_order.make_material_request",
			source_doctype: "Sales Order",
			target: frm,
			setters: {
				company: frm.doc.company
			},
			get_query_filters: {
				docstatus: 1,
				status: ["not in", ["Closed", "On Hold"]],
				per_delivered: ["<", 99.99],
			}
		});
	},

	get_item_data: function(frm, item) {
		if (item && !item.item_code) { return; }

		frm.call({
			method: "erpnext.stock.get_item_details.get_item_details",
			child: item,
			args: {
				args: {
					item_code: item.item_code,
					warehouse: item.warehouse,
					doctype: frm.doc.doctype,
					buying_price_list: frappe.defaults.get_default('buying_price_list'),
					currency: frappe.defaults.get_default('Currency'),
					name: frm.doc.name,
					qty: item.qty || 1,
					stock_qty: item.stock_qty,
					company: frm.doc.company,
					conversion_rate: 1,
					material_request_type: frm.doc.material_request_type,
					plc_conversion_rate: 1,
					rate: item.rate,
					conversion_factor: item.conversion_factor
				}
			},
			callback: function(r) {
				const d = item;
				if(!r.exc) {
					$.each(r.message, function(k, v) {
						if(!d[k]) d[k] = v;
					});
				}
			}
		});
	},

	get_items_from_bom: function(frm) {
		var d = new frappe.ui.Dialog({
			title: __("Get Items from BOM"),
			fields: [
				{"fieldname":"bom", "fieldtype":"Link", "label":__("BOM"),
					options:"BOM", reqd: 1, get_query: function() {
						return {filters: { docstatus:1 , company:frm.doc.company, is_active:1}};
					}},

				{"fieldname":"qty", "fieldtype":"Float", "label":__("Quantity"),
					reqd: 1, "default": 1},
				{"fieldname":"fetch_exploded", "fieldtype":"Check",
					"label":__("Fetch exploded BOM (including sub-assemblies)"), "default":1},
				{fieldname:"fetch", "label":__("Get Items from BOM"), "fieldtype":"Button"}
			]
		});
		d.get_input("fetch").on("click", function() {
			var values = d.get_values();
			if(!values) return;
			values["company"] = frm.doc.company;
			if(!frm.doc.company) frappe.throw(__("Company field is required"));
			frappe.call({
				method: "erpnext.manufacturing.doctype.bom.bom.get_bom_items",
				args: values,
				callback: function(r) {
					if (!r.message) {
						frappe.throw(__("BOM does not contain any stock item"));
					} else {
						erpnext.utils.remove_empty_first_row(frm, "items");
						$.each(r.message, function(i, item) {
							var d = frappe.model.add_child(cur_frm.doc, "Material Request Item", "items");
							d.item_code = item.item_code;
							d.item_name = item.item_name;
							d.description = item.description;
							d.warehouse = item.default_warehouse;
							d.uom = item.stock_uom;
							d.stock_uom = item.stock_uom;
							d.conversion_factor = 1;
							d.qty = item.qty;
							d.project = item.project;
						});
					}
					d.hide();
					refresh_field("items");
				}
			});
		});
		d.show();
	},

	make_purchase_order: function(frm) {
		frappe.prompt(
			{
				label: __('For Default Supplier (Optional)'),
				fieldname:'default_supplier',
				fieldtype: 'Link',
				options: 'Supplier',
				description: __('Select a Supplier from the Default Supplier List of the items below.'),
				get_query: () => {
					return{
						query: "erpnext.stock.doctype.material_request.material_request.get_default_supplier_query",
						filters: {'doc': frm.doc.name}
					}
				}
			},
			(values) => {
				frappe.model.open_mapped_doc({
					method: "erpnext.stock.doctype.material_request.material_request.make_purchase_order",
					frm: frm,
					args: { default_supplier: values.default_supplier },
					run_link_triggers: true
				});
			},
			__('Enter Supplier')
		)
	},

	make_request_for_quotation: function(frm) {
		frappe.model.open_mapped_doc({
			method: "erpnext.stock.doctype.material_request.material_request.make_request_for_quotation",
			frm: frm,
			run_link_triggers: true
		});
	},

	make_supplier_quotation: function(frm) {
		frappe.model.open_mapped_doc({
			method: "erpnext.stock.doctype.material_request.material_request.make_supplier_quotation",
			frm: frm
		});
	},

	make_stock_entry: function(frm) {
		frappe.model.open_mapped_doc({
			method: "nrp_manufacturing.modules.gourmet.material_request.material_request.make_stock_entry",
			frm: frm
		});
	},

	create_pick_list: (frm) => {
		frappe.model.open_mapped_doc({
			method: "erpnext.stock.doctype.material_request.material_request.create_pick_list",
			frm: frm
		});
	},

	raise_work_orders: function(frm) {
		frappe.call({
			method:"erpnext.stock.doctype.material_request.material_request.raise_work_orders",
			args: {
				"material_request": frm.doc.name
			},
			callback: function(r) {
				if(r.message.length) {
					frm.reload_doc();
				}
			}
		});
	},
	material_request_type: function(frm) {
		frm.toggle_reqd('customer', frm.doc.material_request_type=="Customer Provided");
	},

	sub_type: function(frm) {
	    if( SUB_TYPES_FOR_STW.includes(frm.doc.sub_type) ){
	        let transit_warehouse = frappe.utils.get_config_by_name("COMPANY_TRANSIT_WAREHOUSE_MAP", {});
    		frm.set_value("transit_warehouse", transit_warehouse[frm.doc.company]);
    		frm.refresh_field("transit_warehouse");
	    }
	},

	material_request_type: function(frm) {
	    if( frm.doc.material_request_type ){
	        if(frm.doc.material_request_type == 'Material Issue' ){
    	        frm.set_df_property("sub_branch", "reqd", 1);
    	        frm.set_df_property("cost_association", "reqd", 1);
	        }else if(frm.doc.material_request_type == 'Material Transfer'){
	            frm.set_df_property('request_from','read_only',false);
	        }
    	    else{
    	        frm.set_df_property("sub_branch", "reqd", 0);
    	        frm.set_df_property("cost_association", "reqd", 0);
    	    }
	    }
	},

	for_warehouse: function(frm) {
	    let transaction_controller = new erpnext.TransactionController();
		transaction_controller.autofill_warehouse(frm.doc.items, "warehouse", frm.doc.for_warehouse);
		
	},

	cost_association: function(frm) {
	    if (frm.doc.material_request_type=='Material Issue' && frm.doc.cost_association && frm.doc.sub_branch){
            frappe.call({
    				method: 'nrp_manufacturing.utils.get_expense_account_from_cost_association',
    				args: {
    				    cost_association_account: frm.doc.cost_association,
    					sub_branch: frm.doc.sub_branch,
    					company: frm.doc.company
    				},
    				callback: function(data) {
                        if (data.message){
                            console.log(data);
                            let chart_of_account = data.message;
                            let transaction_controller = new erpnext.TransactionController();
                		    transaction_controller.autofill_warehouse(frm.doc.items, "expense_account", chart_of_account);
                        }
    				}
                })
    	}
	},

	sub_branch: function(frm) {
	    frm.set_query("cost_association", function() {
	                return {
	                    query: "nrp_manufacturing.utils.get_cost_associations",
        				filters: {
        					company: frm.doc.company,
        					sub_branch: frm.doc.sub_branch
        				}
        			}
	            })
	    frm.set_query("employee", function() {
	                return {
	                    filters: {
        					company: frm.doc.company,
        					sub_branch: frm.doc.sub_branch
        				}
        			}
	            })
	    frm.set_value("cost_association", null);
		refresh_field("cost_association");
		
		frm.set_value("employee", null);
		refresh_field("employee");
		if(frappe.utils.get_config_by_name("MATERIAL_ISSUE_SUB_BRANCH_PP_REQ").includes(frm.doc.sub_branch)){
		    var today = new Date();
		    frm.toggle_display("production_plan", 1);
            var fiveDay = new Date();
            var numberOfDaysToAdd = 6;
            fiveDay.setDate(fiveDay.getDate() + numberOfDaysToAdd); 
            console.log(today.toISOString().replace(/^(?<year>\d+)-(?<month>\d+)-(?<day>\d+)T.*$/,'$<year>-$<month>-$<day>'));
            console.log(fiveDay.toISOString().replace(/^(?<year>\d+)-(?<month>\d+)-(?<day>\d+)T.*$/,'$<year>-$<month>-$<day>'));
		    frm.set_df_property("production_plan", "reqd", 1);
            frm.set_query('production_plan',function(doc, cdt, cdn) {
    			return {
    				"filters": [
    					["planed_for",">=", today.toISOString().replace(/^(?<year>\d+)-(?<month>\d+)-(?<day>\d+)T.*$/,'$<year>-$<month>-$<day>')],
    					["planed_for", "<=", fiveDay.toISOString().replace(/^(?<year>\d+)-(?<month>\d+)-(?<day>\d+)T.*$/,'$<year>-$<month>-$<day>')]
    				]
    			};
    		});
		}else{
		    frm.toggle_display("production_plan", 0);
		    frm.set_df_property("production_plan", "reqd", 0);
		}
	},

	production_plan: function(frm){
		frappe.model.get_value('Production Plan', {'name': frm.doc.production_plan}, 'planed_for',
          function(d) {
              console.log('planed_for',d);
            frm.doc.schedule_date = d.planed_for;
            frm.set_df_property('schedule_date', "read_only", 1);
            refresh_field('schedule_date');
          })
        
    },	
	project_based: function(frm) {
		project_based_configurations(frm);
	},

	project: function(frm) {
		project_based_configurations(frm);
	},

});

frappe.ui.form.on("Material Request Item", {
	qty: function (frm, doctype, name) {
		var d = locals[doctype][name];
		if (flt(d.qty) < flt(d.min_order_qty)) {
			frappe.msgprint(__("Warning: Material Requested Qty is less than Minimum Order Qty"));
		}

		const item = locals[doctype][name];
		frm.events.get_item_data(frm, item);
	},

	rate: function(frm, doctype, name) {
		const item = locals[doctype][name];
		frm.events.get_item_data(frm, item);
	},

	item_code: function(frm, doctype, name) {
		const item = locals[doctype][name];
		item.rate = 0;
		set_schedule_date(frm);
		frm.events.get_item_data(frm, item);

		if (frm.doc.material_request_type=='Material Issue' && frm.doc.cost_association && frm.doc.sub_branch){
            frm.trigger("cost_association");
	    }
	},

	schedule_date: function(frm, cdt, cdn) {
		var row = locals[cdt][cdn];
		if (row.schedule_date) {
			if(!frm.doc.schedule_date) {
				erpnext.utils.copy_value_in_all_rows(frm.doc, cdt, cdn, "items", "schedule_date");
			} else {
				set_schedule_date(frm);
			}
		}
	},

	form_render(frm, cdt, cdn){
		if (frm.doc.material_request_type == "Material Issue"){
			frm.get_field("items").grid.toggle_enable("expense_account", 0);
			refresh_field("items");
		}
	},

	expense_account: function(frm){
	    if (frm.doc.material_request_type=='Material Issue' && frm.doc.cost_association && frm.doc.sub_branch){
    	    frm.trigger("cost_association");
	    }
	}
	
});

erpnext.buying.MaterialRequestController = erpnext.buying.BuyingController.extend({
	tc_name: function() {
		this.get_terms();
	},

	item_code: function() {
		// to override item code trigger from transaction.js
	},

	validate_company_and_party: function() {
		return true;
	},

	calculate_taxes_and_totals: function() {
		return;
	},

	validate: function() {
		set_schedule_date(this.frm);
	},

	// onload: function(doc, cdt, cdn) {
	// 	this.frm.set_query("item_code", "items", function() {
	// 		if (doc.material_request_type == "Customer Provided") {
	// 			return{
	// 				query: "erpnext.controllers.queries.item_query",
	// 				filters:{ 'customer': me.frm.doc.customer }
	// 			}
	// 		} else if (doc.material_request_type != "Manufacture") {
	// 			return{
	// 				query: "erpnext.controllers.queries.item_query",
	// 				filters: {'is_purchase_item': 1}
	// 			}
	// 		}
	// 	});
		
	// 	if(this.frm.doc.material_request_type == "Purchase"){
	// 		this.frm.get_field("items").grid.toggle_enable("uom", 0);
	// 		this.frm.get_field("items").grid.toggle_enable("item_name", 0);
	// 		refresh_field("items");
	// 	}
	// },

	items_add: function(doc, cdt, cdn) {
		var row = frappe.get_doc(cdt, cdn);
		if(doc.schedule_date) {
			row.schedule_date = doc.schedule_date;
			refresh_field("schedule_date", cdn, "items");
		} else {
			this.frm.script_manager.copy_from_first_row("items", row, ["schedule_date"]);
		}
	},

	items_on_form_rendered: function() {
		set_schedule_date(this.frm);
	},

	schedule_date: function() {
		set_schedule_date(this.frm);
	}
});

// for backward compatibility: combine new and previous states
$.extend(cur_frm.cscript, new erpnext.buying.MaterialRequestController({frm: cur_frm}));

function set_schedule_date(frm) {
	if(frm.doc.schedule_date){
		erpnext.utils.copy_value_in_all_rows(frm.doc, frm.doc.doctype, frm.doc.name, "items", "schedule_date");
	}
}
function show_project_selection_modal(frm) {
    let dialog = new frappe.ui.Dialog({
        title: __("Select Project"),
        fields: [
            {
                fieldtype: "Link",
                label: __("Select Project"),
                fieldname: "selected_project",
                options: "Project",
                reqd: 1,
                get_query: function () {
                    return {
                        filters: {
                            company: frm.doc.company
                        }
                    };
                }
            }
        ],
        primary_action_label: __("Select"),
        primary_action: function () {
            let selected_project = dialog.get_value("selected_project");

            if (!selected_project) {
                frappe.msgprint(__('Please select a project.'));
                return;
            }

            // Fetch project details
            frappe.call({
                method: "frappe.client.get",
                args: {
                    doctype: "Project",
                    name: selected_project
                },
                callback: function (response) {
                    if (response.message) {
                        let project_id = response.message.name;
                        let project_name = response.message.project_name;

                        frappe.confirm(
                            `Do you want to add project <b>${project_name} (${project_id})</b> to the items?`,
                            function () {
                                frappe.call({
                                    method: "erpnext.stock.doctype.material_request.material_request.update_project_reference",
                                    args: {
                                        project_id: project_id,
                                        docname: frm.doc.name
                                    },
                                    callback: function (res) {
                                        if (res.message.status === "success") {
                                            frappe.msgprint(__("Project updated successfully!"));
                                            frm.refresh();
                                            let items_list = res.message.material_request_items.map(item =>
                                                `Item: ${item.item_code} - ${item.item_name} (Qty: ${item.qty} ${item.stock_uom})`
                                            ).join("<br>");

                                            frappe.msgprint({
                                                title: __("Material Request Items"),
                                                message: items_list || __("No items found."),
                                                indicator: "blue"
                                            });
                                        } else {
                                            frappe.msgprint(__("Failed to update project."));
                                        }
                                    }
                                });

                                dialog.hide();
                            },
                            function () {
                                dialog.hide();
                            }
                        );
                    }
                }
            });
        }
    });

    dialog.show();
}


// Code by Moeiz
function project_based_configurations(frm){
	const project_based_applicable_companies = ["Unit 5", "Unit 5B", "Unit 5C", "Unit 5D", "Unit 8", "Unit 11", "Unit 17", "Unit 17B", "Unit 17C", "QuinTech Centre of Applied Sciences (Pvt.) Ltd."]
	if (project_based_applicable_companies.includes(frm.doc.company)){
		frm.set_df_property('project_based', 'hidden', 0);
	}else{
		frm.set_df_property('project_based', 'hidden', 1);
		frm.set_value('project_based', 0);
	}

	if(frm.doc.project_based){
		frm.set_df_property('project', 'reqd', 1);
		frm.set_df_property('project', 'hidden', 0);
		frm.set_df_property('project', 'read_only', 0);
	}else{
		frm.set_df_property('project', 'reqd', 0);
		frm.set_df_property('project', 'hidden', 1);
		frm.set_df_property('project', 'read_only', 1);
	}

	frm.set_query("project", function() {
		return {
			filters: {
				"is_group": 0,
				"company": frm.doc.company
			}
		};
	});


	if (frm.doc.project_based){
		// Project field in items child table would be read only if project based MR
		frm.get_field("items").grid.toggle_enable("project", 0);
		if(!frm.doc.project || frm.doc.project == "") {
			frm.set_df_property('items', 'cannot_add_rows', true);
			frm.set_df_property('items', 'cannot_delete_rows', true);
			frm.set_df_property('items', 'cannot_delete_all_rows', true);
			frm.fields_dict['items'].grid.wrapper.find('.grid-remove-rows').hide();
		}else{
			frm.set_df_property('items', 'cannot_add_rows', false);
			frm.set_df_property('items', 'cannot_delete_rows', false);
			frm.set_df_property('items', 'cannot_delete_all_rows', false);
			frm.fields_dict['items'].grid.wrapper.find('.grid-remove-rows').show();
		}
	}else{
		frm.get_field("items").grid.toggle_enable("project", 1);
	}

	frm.refresh_field('items');
}