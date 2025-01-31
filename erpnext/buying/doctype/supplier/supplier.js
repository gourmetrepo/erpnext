// Copyright (c) 2015, Frappe Technologies Pvt. Ltd. and Contributors
// License: GNU General Public License v3. See license.txt

frappe.ui.form.on("Supplier", {
	setup: function (frm) {
		frm.set_query('default_price_list', { 'buying': 1 });
		if (frm.doc.__islocal == 1) {
			frm.set_value("represents_company", "");
		}
		frm.set_query('account', 'accounts', function (doc, cdt, cdn) {
			var d = locals[cdt][cdn];
			return {
				filters: {
					'account_type': 'Payable',
					'company': d.company,
					"is_group": 0
				}
			}
		});
		frm.set_query("default_bank_account", function() {
			return {
				filters: {
					"is_company_account":1
				}
			}
		});
	},
	refresh: function (frm) {
		frappe.dynamic_link = { doc: frm.doc, fieldname: 'name', doctype: 'Supplier' }

		if (frappe.defaults.get_default("supp_master_name") != "Naming Series") {
			frm.toggle_display("naming_series", false);
		} else {
			erpnext.toggle_naming_series();
		}

		if (frm.doc.__islocal) {
			hide_field(['address_html','contact_html']);
			frappe.contacts.clear_address_and_contact(frm);
		}
		else {
			unhide_field(['address_html','contact_html']);
			frappe.contacts.render_address_and_contact(frm);

			// custom buttons
			frm.add_custom_button(__('Accounting Ledger'), function () {
				frappe.set_route('query-report', 'General Ledger',
					{ party_type: 'Supplier', party: frm.doc.name });
			}, __("View"));

			frm.add_custom_button(__('Accounts Payable'), function () {
				frappe.set_route('query-report', 'Accounts Payable', { supplier: frm.doc.name });
			}, __("View"));

			frm.add_custom_button(__('Bank Account'), function () {
				erpnext.utils.make_bank_account(frm.doc.doctype, frm.doc.name);
			}, __('Create'));

			frm.add_custom_button(__('Pricing Rule'), function () {
				erpnext.utils.make_pricing_rule(frm.doc.doctype, frm.doc.name);
			}, __('Create'));

			// indicators
			erpnext.utils.set_party_dashboard_indicators(frm);
		}

		frappe.require("assets/nerp/js/jquery.maskedinput.min.js", () => {
            $.mask.definitions['3'] = null;
            $('input[data-fieldname="cnic"]').mask(frappe.utils.get_config_by_name('CNIC_MASK','99999-9999999-9'),{autoclear: false});
        })
	},

	is_internal_supplier: function(frm) {
		if (frm.doc.is_internal_supplier == 1) {
			frm.toggle_reqd("represents_company", true);
		}
		else {
			frm.toggle_reqd("represents_company", false);
		}
	},
	onload: function(frm) {
        frm.fields_dict['grower_location'].grid.get_field('location').get_query = "sugar_mill.sugar_mill.doctype.supplier_location_information.supplier_location_information.get_location";
    },
	supplier_type: function(frm) {
		frm.toggle_reqd('cnic',frm.doc.supplier_type === 'Grower');
		frm.toggle_reqd('father_name',frm.doc.supplier_type === 'Grower');
		if(frm.doc.supplier_type == 'Grower'){
		    frm.set_value('naming_series', 'GWR-.YY.-.######');
		    refresh_field('naming_series')
		}
	},
	naming_series: function(frm){
		if(frm.doc.supplier_type == 'Grower'){
			frm.set_value('naming_series','GWR-.YY.-.######');
			refresh_field('naming_series');
		}  
	},
});

// Child table Grower Location
frappe.ui.form.on('Supplier Location Information',{
    location:function(frm,cdt,cdn){
        let row = frappe.get_doc(cdt,cdn);
		frappe.call({
		    doc:row,
			method: "get_grower_information",
			callback: function(r) {
				refresh_field('grower_location');
			}
		});
    }
})