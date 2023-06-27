// Copyright (c) 2018, Frappe Technologies Pvt. Ltd. and contributors
// For license information, please see license.txt

frappe.ui.form.on('Payment Order', {
	setup: function(frm) {
		frm.set_query("company_bank_account", function() {
			return {
				filters: {
					"is_company_account":1
				}
			}
		});
	},
	refresh: function(frm) {
		if (frm.doc.docstatus == 0) {
			frm.add_custom_button(__('Payment Request'), function() {
				frm.trigger("get_from_payment_request");
			}, __("Get Payments from"));

			frm.add_custom_button(__('Payment Entry'), function() {
				frm.trigger("get_from_payment_entry");
			}, __("Get Payments from"));

			frm.trigger('remove_button');
		}

		// payment Entry
		if (frm.doc.docstatus===1 && frm.doc.payment_order_type==='Payment Request') {
			frm.add_custom_button(__('Create Payment Entries'), function() {
				frm.trigger("make_payment_records");
			});
			frm.add_custom_button(__('Create Payment Entry With Single Cheque'), function() {
				frappe.call({
					method: "erpnext.accounts.doctype.payment_order.payment_order.make_payment_with_single_cheque",
					args: {
						"name": frm.doc.name,
					},
					freeze: true,
					callback: function(r) {
						frm.refresh();
					}
				})
				setTimeout(() => {
					frm.remove_custom_button('Create Payment Entry With Single Cheque','Create');

				}, 100);
			},('Create'));
			frm.add_custom_button(__('Create Payment Entry For All Suppliers'), function() {
				frappe.call({
					method: "erpnext.accounts.doctype.payment_order.payment_order.make_payment_entry_on_single_click",
					args: {
						"name": frm.doc.name,
					},
					freeze: true,
					callback: function(r) {
						frm.refresh();
					}
				})
			},('Create'));
		}
		console.log(frm.doc)
			if ( frm.doc.__unsaved){
				console.log("Unsaved Document")
			}else{
			if (frm.doc.docstatus == 0 && frm.doc.docstatus != 1 ){
			setTimeout(function() {
				frm.trigger("balances_dashboard");
			}, 100);}}
	},

	remove_row_if_empty: function(frm) {
		// remove if first row is empty
		if (frm.doc.references.length > 0 && !frm.doc.references[0].reference_name) {
			frm.doc.references = [];
		}
	},

	remove_button: function(frm) {
		// remove custom button of order type that is not imported

		let label = ["Payment Request", "Payment Entry"];

		if (frm.doc.references.length > 0 && frm.doc.payment_order_type) {
			label = label.reduce(x => {
				x!= frm.doc.payment_order_type;
				return x;
			});
			frm.remove_custom_button(label, "Get from");
		}
	},

	get_from_payment_entry: function(frm) {
		frm.trigger("remove_row_if_empty");
		erpnext.utils.map_current_doc({
			method: "erpnext.accounts.doctype.payment_entry.payment_entry.make_payment_order",
			source_doctype: "Payment Entry",
			target: frm,
			date_field: "posting_date",
			setters: {
				party: frm.doc.supplier || ""
			},
			get_query_filters: {
				bank: frm.doc.bank,
				docstatus: 1,
				payment_type: ["!=", "Receive"],
				bank_account: frm.doc.company_bank_account,
				paid_from: frm.doc.account,
				payment_order_status: ["=", "Initiated"]
			}
		});
	},

	get_from_payment_request: function(frm) {
		frm.trigger("remove_row_if_empty");
		erpnext.utils.map_current_doc({
			method: "erpnext.accounts.doctype.payment_request.payment_request.make_payment_order",
			source_doctype: "Payment Request",
			target: frm,
			setters: {
				party: frm.doc.supplier || ""
			},
			get_query_filters: {
				bank: frm.doc.bank,
				docstatus: 1,
				status: ["=", "Initiated"],
			}
		});
	},

	make_payment_records: function(frm){
		var dialog = new frappe.ui.Dialog({
			title: __("For Supplier"),
			fields: [
				{"fieldtype": "Link", "label": __("Supplier"), "fieldname": "supplier", "options":"Supplier",
					"get_query": function () {
						return {
							query:"erpnext.accounts.doctype.payment_order.payment_order.get_supplier_query",
							filters: {'parent': frm.doc.name}
						}
					}, "reqd": 1
				},

				{"fieldtype": "Link", "label": __("Mode of Payment"), "fieldname": "mode_of_payment", "options":"Mode of Payment",
					"get_query": function () {
						return {
							query:"erpnext.accounts.doctype.payment_order.payment_order.get_mop_query",
							filters: {'parent': frm.doc.name}
						}
					}
				}
			]
		});

		dialog.set_primary_action(__("Submit"), function() {
			var args = dialog.get_values();
			if(!args) return;

			return frappe.call({
				method: "erpnext.accounts.doctype.payment_order.payment_order.make_payment_records",
				args: {
					"name": me.frm.doc.name,
					"supplier": args.supplier,
					"mode_of_payment": me.mode_of_payment
				},
				freeze: true,
				callback: function(r) {
					dialog.hide();
					frm.refresh();
				}
			})
		})

		dialog.show();
	},


	balances_dashboard: function(frm) {
		console.log("pmo triggered")
		let balances;
		if (frm.doc) {
			frappe.call({
				method: "nrp_manufacturing.modules.gourmet.payment_order.payment_order.get_pmo_dashboard_balances", 
				async: false,
				args: {
					data: frm.doc.name
				},
				callback: function(r) {
					console.log(r.message)
					if (r.message) {
						balances = r.message;
					}
				}
			});
	

			var myvar_pmo ='{% if balances %}' +
			'{% if balances["mode_of_payment"] == "Cash" %}' +
			'<div id="missing" style="position: relative; right: 18px;" class="container missing">' +
			'<div class="row">' +
			'<div class="col-md-6">' +
			'<div class="field">' +
			'<h6 style="display: inline;">Cash Balance before payment:</h6>&nbsp;&nbsp;&nbsp;&nbsp' +
			'<p style="display: inline;">Rs: {{ balances["balance_before_payment"] }}</p>' +
			'</div>' +
			'</div>' +
			'<div class="col-md-6">' +
			'<div class="field">' +
			'<h6 style="display: inline;">Cash Payment:</h6>&nbsp;&nbsp;&nbsp;&nbsp' +
			'<p style="display: inline;">Rs: {{ balances["payment"] }}</p>' +
			'</div>' +
			'</div>' +
			'</div>' +
			'<div class="row">' +
			'<div class="col-md-6">' +
			'<div class="field">' +
			'<h6 style="display: inline;">Cash Balance after Payment:</h6>&nbsp;&nbsp;&nbsp;&nbsp' +
			'<p style="display: inline;">Rs: {{ balances["balance_after_payment"] }}</p>' +
			'</div>' +
			'</div>' +
			'<div class="col-md-6">' +
			'<div class="field">' +
			'<h6 style="display: inline;">Consumed Cash Balance:</h6>&nbsp;&nbsp;&nbsp;&nbsp' +
			'<p style="display: inline;">Rs: {{ balances["consumed_amount"] }}</p>' +
			'</div>' +
			'</div>' +
			'</div>' +
			'</div>' +
			'{% endif %}' +
			'{% if balances["mode_of_payment"] == "BANK" || balances["mode_of_payment"] == "Cheque" %}' +
			'<div id="missing" style="position: relative; right: 18px;" class="container missing">' +
			'<div class="row">' +
			'<div class="col-md-6">' +
			'<div class="field">' +
			'<h6 style="display: inline;">Bank Balance before payment:</h6>&nbsp;&nbsp;&nbsp;&nbsp;' +
			'<p style="display: inline;">Rs: {{ balances["balance_before_payment"] }}</p>' +
			'</div>' +
			'</div>' +
			'<div class="col-md-6">' +
			'<div class="field">' +
			'<h6 style="display: inline;">Bank Payment:</h6>&nbsp;&nbsp;&nbsp;&nbsp;' +
			'<p style="display: inline;">Rs: {{ balances["payment"] }}</p>' +
			'</div>' +
			'</div>' +
			'</div>' +
			'<div class="row">' +
			'<div class="col-md-6">' +
			'<div class="field">' +
			'<h6 style="display: inline;">Bank Balance after payment:</h6>&nbsp;&nbsp;&nbsp;&nbsp;' +
			'<p style="display: inline;">Rs: {{ balances["balance_after_payment"] }}</p>' +
			'</div>' +
			'</div>' +
			'<div class="col-md-6">' +
			'<div class="field">' +
			'<h6 style="display: inline;">Consumed Bank Balance:</h6>&nbsp;&nbsp;&nbsp;&nbsp;' +
			'<p style="display: inline;">Rs: {{ balances["consumed_amount"] }}</p>' +
			'</div>' +
			'</div>' +
			'</div>' +
			'</div>' +
			'{% endif %}' +
			'{% if balances["mode_of_payment"] == null %}' +
			'<div id="missing" style="position: relative; right: 18px;" class="container missing">'+
			'<h6 style="margin-top: 20px; display: inline;">There is some issue in Payment Order</h6>'+
			'</div>'+
			'{% endif %}'+
			'{% endif %}';			
			

			
		


			$("div").remove(".pmo_dashboard");
			console.log(balances)
			frm.dashboard.add_section(
				frappe.render_template(myvar_pmo, {
					balances: balances
				},"pmo_dashboard")
			);
			$(".form-dashboard").append( $(".pmo_dashboard") );
			// frm.dashboard.show();
		}
	}
});