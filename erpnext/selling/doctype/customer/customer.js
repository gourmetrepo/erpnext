// Copyright (c) 2015, Frappe Technologies Pvt. Ltd. and Contributors
// License: GNU General Public License v3. See license.txt

frappe.ui.form.on("Customer", {
	setup: function(frm) {

		frm.make_methods = {
			'Quotation': () => frappe.model.open_mapped_doc({
				method: 'erpnext.selling.doctype.customer.customer.make_quotation',
				frm: cur_frm
			}),
			'Opportunity': () => frappe.model.open_mapped_doc({
				method: 'erpnext.selling.doctype.customer.customer.make_opportunity',
				frm: cur_frm
			})
		}

		frm.add_fetch('lead_name', 'company_name', 'customer_name');
		frm.add_fetch('default_sales_partner','commission_rate','default_commission_rate');
		frm.set_query('customer_group', {'is_group': 0});
		frm.set_query('default_price_list', { 'selling': 1});
		frm.set_query('account', 'accounts', function(doc, cdt, cdn) {
			var d  = locals[cdt][cdn];
			var filters = {
				'account_type': 'Receivable',
				'company': d.company,
				"is_group": 0
			};

			if(doc.party_account_currency) {
				$.extend(filters, {"account_currency": doc.party_account_currency});
			}
			return {
				filters: filters
			}
		});

		if (frm.doc.__islocal == 1) {
			frm.set_value("represents_company", "");
		}

		frm.set_query('customer_primary_contact', function(doc) {
			return {
				query: "erpnext.selling.doctype.customer.customer.get_customer_primary_contact",
				filters: {
					'customer': doc.name
				}
			}
		})
		frm.set_query('customer_primary_address', function(doc) {
			return {
				filters: {
					'link_doctype': 'Customer',
					'link_name': doc.name
				}
			}
		})

		frm.set_query('default_bank_account', function() {
			return {
				filters: {
					'is_company_account': 1
				}
			}
		});
	},
	customer_primary_address: function(frm){
		if(frm.doc.customer_primary_address){
			frappe.call({
				method: 'frappe.contacts.doctype.address.address.get_address_display',
				args: {
					"address_dict": frm.doc.customer_primary_address
				},
				callback: function(r) {
					frm.set_value("primary_address", r.message);
				}
			});
		}
		if(!frm.doc.customer_primary_address){
			frm.set_value("primary_address", "");
		}
	},

	is_internal_customer: function(frm) {
		if (frm.doc.is_internal_customer == 1) {
			frm.toggle_reqd("represents_company", true);
		}
		else {
			frm.toggle_reqd("represents_company", false);
		}
	},

	customer_primary_contact: function(frm){
		if(!frm.doc.customer_primary_contact){
			frm.set_value("mobile_no", "");
			frm.set_value("email_id", "");
		}
	},

	loyalty_program: function(frm) {
		if(frm.doc.loyalty_program) {
			frm.set_value('loyalty_program_tier', null);
		}
	},

	refresh: function(frm) {
		frappe.require("assets/nerp/js/jquery.maskedinput.min.js", () => {
            $.mask.definitions['3'] = null;
            $('input[data-fieldname="cnic"]').mask(frappe.utils.get_config_by_name('CNIC_MASK','99999-9999999-9'),{autoclear: false});
           // $('input[data-fieldname="phone_no"]').mask(frappe.utils.get_config_by_name('CELL_NUMBER_MASK','0399-9999999'),{autoclear: false});
        })

		if(frappe.defaults.get_default("cust_master_name")!="Naming Series") {
			frm.toggle_display("naming_series", false);
		} else {
			erpnext.toggle_naming_series();
		}

		frappe.dynamic_link = {doc: frm.doc, fieldname: 'name', doctype: 'Customer'}
		frm.toggle_display(['address_html','contact_html'], !frm.doc.__islocal);

		if(!frm.doc.__islocal) {
			frappe.contacts.render_address_and_contact(frm);

			// custom buttons
			frm.add_custom_button(__('Accounting Ledger'), function() {
				frappe.set_route('query-report', 'General Ledger',
					{party_type:'Customer', party:frm.doc.name});
			});

			frm.add_custom_button(__('Accounts Receivable'), function() {
				frappe.set_route('query-report', 'Accounts Receivable', {customer:frm.doc.name});
			});

			frm.add_custom_button(__('Pricing Rule'), function () {
				erpnext.utils.make_pricing_rule(frm.doc.doctype, frm.doc.name);
			}, __('Create'));

			// indicator
			erpnext.utils.set_party_dashboard_indicators(frm);

		} else {
			frappe.contacts.clear_address_and_contact(frm);
		}

		var grid = cur_frm.get_field("sales_team").grid;
		grid.set_column_disp("allocated_amount", false);
		grid.set_column_disp("incentives", false);

		if (frm.doc.customer_group == "CSD Distributors") {
            frappe.call({
                method: "erpnext.selling.doctype.customer.customer.get_distribution_geo",
                args: {
                    distribution_code: frm.doc.name
                },
                callback: function(r) {
                    if (r.message && r.message.length > 0) {
                        let data = r.message[0];

                        let html = `
							<style>
								.table-wrapper {
									overflow: auto;
									max-width: 100%;
									max-height: 600px;
									border: 1px solid #ccc;
								}

								.sticky-table {
									border-collapse: collapse;
									width: 100%;
								}

								/* Make all header cells sticky */
								.sticky-table th {
									position: sticky;
									top: 0;
									/* background: #fff; */
									z-index: 1;
									text-align: center;
									border: 1px solid #ccc;
								}

								/* Second header row is below the first, so higher top offset */
								.sticky-table tr:nth-child(2) th {
									top: 34px; /* Adjust based on your first row height */
								}

								/* First column (Date) – both th and td */
								.sticky-table th:first-child,
								.sticky-table td:first-child {
									position: sticky;
									left: 0;
									background: #f1f1f1;
									z-index: 2;
								}

								/* Corner cell (top-left "Date") – must be on top */
								.sticky-table tr:first-child th:first-child {
									z-index: 5;
								}

								table {
									width: 100%;
									border-collapse: collapse;
									background: white;
									float:left;
								}
								.table{
									margin:0px;
								}
								.tableviewmore th{
									border: 1px solid #000 !important;
								}
								th, td {
									border: 1px solid #000;
									padding: 8px;
									text-align: left;
								}
								th {
									background-color: #ddd;
								}
								.header {
									text-align: center;
									font-weight: bold;
									font-size: 18px;
									padding: 10px;
									background: #444;
									color: white;
									width:100%;
									float:left;
								}

								.sub-header {
									text-align: center;
									font-weight: bold;
									font-size: 14px;
									padding: 10px;
									background: #00b33c;
									color: white;
									width:100%;
									float:left;
								}
								div.wrapper{
									float:left;
									width:100%;
									overflow-y:auto;
									max-height: 800px;
									overflow-x: auto;
								}
								th{
									text-align: center;
								}
								td a{
									text-decoration: underline;
								}
								button.view_more{
									margin-top:2px;
									padding-top:0px;
									padding-bottom:0px;
								}
								.table-inner{
									margin:0;
								}
							</style>
                            <table>
								<tr>
									<th>Region</th>
									<th>Zone</th>
									<th>Area</th>
									<th>Territory</th>
									<th>Warehouse Latitude</th>
									<th>Warehouse Longitude</th>
									<th>Distribution Latitude</th>
									<th>Distribution Longitude</th>
								</tr>
								<tr>
									<td>${data.region}</td>
									<td>${data.zone}</td>
									<td>${data.area}</td>
									<td>${data.territory}</td>
									<td>${data.warehouseLatitude}</td>
									<td>${data.warehouseLongitude}</td>
									<td>${data.distributionLatitude}</td>
									<td>${data.distributionLongitude}</td>
								</tr>
                            </table>
                        `;

                        frm.fields_dict.distributor_details_html.$wrapper.html(html);
                    } else {
                        frm.fields_dict.distributor_details_html.$wrapper.html("<p>No distribution data found.</p>");
                    }
                }
            });
        }
	},
	validate: function(frm) {
		if(frm.doc.lead_name) frappe.model.clear_doc("Lead", frm.doc.lead_name);

	},
	onload: function(frm) {
        if (frm.doc.customer_group == "CSD Distributors") {
            frm.fields_dict.distributor_details_html.$wrapper.html(
                `<div style="padding:8px; background:#f9f9f9; border:1px solid #ddd; border-radius:5px;">
                    <b>Note:</b> Please make sure to fill in the <i>NTN</i>, <i>STRN</i> and <i>Credit Limit</i> fields in the 'More Information' section.
                </div>`
            );
        }
    }
});
