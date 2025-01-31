// Copyright (c) 2025, Frappe Technologies Pvt. Ltd. and contributors
// For license information, please see license.txt

frappe.ui.form.on('Compliance Verification', {
	refresh: function(frm) {
		// frm.set_query("inspector", function() {
        //     if(!frm.doc.company){
        //         frappe.msgprint("Please select Company first.");
        //     }
        //     return {
        //         "filters": {"company": frm.doc.company}
        //     };
        // });

		// frm.set_query("area_incharge", function() {
        //     if(!frm.doc.company){
        //         frappe.msgprint("Please select Company first.");
        //     }
        //     return {
        //         "filters": {"company": frm.doc.company}
        //     };
        // });

		// frm.set_query("cost_center", function() {
        //     if(!frm.doc.company){
        //         frappe.msgprint("Please select Company first.");
        //     }
        //     return {
        //         "filters": {"company": frm.doc.company}
        //     };
        // });

		// frm.set_query("parameter_setup", function() {
        //     if(!frm.doc.company){
        //         frappe.msgprint("Please select Company first.");
        //     }
		// 	if(!frm.doc.location){
        //         frappe.msgprint("Please select Location first.");
        //     }
		// 	if(!frm.doc.cost_center){
        //         frappe.msgprint("Please select Cost Center first.");
        //     }
        //     return {
        //         "filters": {
		// 			"company": frm.doc.company,
		// 			"location": frm.doc.location,
		// 			"cost_center": frm.doc.cost_center
		// 		}
        //     };
        // });
	},
	onload: function(frm) {
		if (frm.doc.compliance_verification_item.length){
			frappe.call({
				method: "erpnext.assets.doctype.compliance_verification.compliance_verification.get_rank_options",
				args: {
					compliance_verification_items: frm.doc.compliance_verification_item
				},
				callback: function(r) {
					let data = r.message;
					frm.doc.compliance_verification_item.forEach(function(row) {
						let options = data[row.parameter];
						if (options) {
							frm.fields_dict.compliance_verification_item.grid.update_docfield_property(
								'ranking',
								'options',
								[''].concat(options));
						}
					});
					frm.refresh_field('compliance_verification_item');
				}
			});
		}
	}
});
