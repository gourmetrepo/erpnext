// Copyright (c) 2015, Frappe Technologies Pvt. Ltd. and Contributors
// License: GNU General Public License v3. See license.txt

cur_frm.cscript.tax_table = "Sales Taxes and Charges";

{% include "erpnext/public/js/controllers/accounts.js" %}

frappe.ui.form.on('Sales Taxes and Charges Template', {
	refresh(frm) {
// 		alert('here');
	}
});

frappe.ui.form.on('Sales Taxes and Charges', {
	charge_type: function(frm, cdt, cdn) {
	    let row = locals[cdt][cdn];
	    if(row.charge_type != "Actual"){
	        frappe.model.set_value(cdt,cdn,"tax_amount",0);
	    }else{
	        frappe.model.set_value(cdt,cdn,"rate",0);
	    }
		frm.trigger("add_deduct_tax");
	},
	add_deduct_tax: function (frm, cdt, cdn) {
		let row = locals[cdt][cdn];
        if(row.rate){
            update_values(frm, cdt, cdn);
        }else{
            update_values(frm, cdt, cdn,"tax_amount");
        }
	},
	tax_amount: function (frm, cdt, cdn) {
	    let row = locals[cdt][cdn];
		if(row.tax_amount){
		    update_values(frm, cdt, cdn,"tax_amount");
		}
	},
	rate: function (frm, cdt, cdn) {
        let row = locals[cdt][cdn];
        if(row.rate){
		    update_values(frm, cdt, cdn);
        }
	}
	
});

function update_values(frm,cdt, cdn,field="rate"){
    let row = locals[cdt][cdn];
	if (row[field]) {
	    if(row.add_deduct_tax == 'Add'){
	        if(row[field] < 0){
		        let rate = Math.abs(row[field]);
		        frappe.model.set_value(cdt,cdn,field,rate);
    			frm.refresh_field(field);
	        }
	    }
	    else if(row.add_deduct_tax == 'Deduct'){
	        if(row[field] > 0){
		        let rate = row[field] * -1;
		        frappe.model.set_value(cdt,cdn,field,rate);
    			frm.refresh_field(field);
	        }
	    }
	}
}
