// Copyright (c) 2015, Frappe Technologies Pvt. Ltd. and Contributors
// License: GNU General Public License v3. See license.txt

frappe.ui.form.on('Shipping Rule', {
	refresh: function(frm) {
		frm.trigger('toggle_reqd');
	},
	calculate_based_on: function(frm) {
		frm.trigger('toggle_reqd');
	},
	toggle_reqd: function(frm) {
		frm.toggle_reqd("shipping_amount", frm.doc.calculate_based_on === 'Fixed');
		frm.toggle_reqd("conditions", frm.doc.calculate_based_on !== 'Fixed');
	},
	before_save: function(frm) {
	    if(frm.doc.calculate_based_on == "Quantity"){
            frm.toggle_reqd("conditions", false);    
	    }
	},
	company: function(frm) {
	    frm.doc.account = null;
	    frm.doc.cost_center = null;
	    frm.refresh_fields('account');
	    frm.refresh_fields('cost_center');
		frm.set_query("account", () => {
			return {
				filters: [
					["Account", "is_group", "=", "0"],
					["Account", "company", "=", frm.doc.company]
				]
			}
		});
		frm.set_query("cost_center", () => {
			return {
				filters: [
					["Cost Center", "is_group", "=", "0"],
					["Cost Center", "company", "=", frm.doc.company]
				]
			}
		});
	}
});