// Copyright (c) 2015, Frappe Technologies Pvt. Ltd. and Contributors
// License: GNU General Public License v3. See license.txt

cur_frm.cscript.refresh = cur_frm.cscript.inspection_type;

frappe.ui.form.on("Quality Inspection", {
	onload: function (frm, cdt, cdn) {	
		var df = frappe.meta.get_docfield("Quality Inspection", "wariety", frm.doc.name);
		df.options = frappe.utils.get_config_by_name("CANE_WARIETY");
		frappe.call({
            method: "nerp.utils.get_ip",
            callback: function(r) {
                if(r.message) {
					let restricted_ips = frappe.utils.get_config_by_name("SUGAR_MILL_WHITELISTED_IPS");
					
					if (restricted_ips.lab_recovery != r.message){
						frm.toggle_display('brix_value', false);
						frm.toggle_display('pol_value', false);
						frm.toggle_display('cake_weight', false);	
					}
                }
            }
        });
	},
	item_code: function(frm) {
		if (frm.doc.item_code) {
			return frm.call({
				method: "get_quality_inspection_template",
				doc: frm.doc,
				callback: function() {
					refresh_field(['quality_inspection_template', 'readings']);
				}
			});
		}
	},

	quality_inspection_template: function(frm) {
		if (frm.doc.quality_inspection_template) {
			return frm.call({
				method: "get_item_specification_details",
				doc: frm.doc,
				callback: function() {
					refresh_field('readings');
				}
			});
		}
	},
	before_submit(frm) {
		if(! cur_frm.doc.quality_inspection_template)
		{
		    frappe.throw(__('Please seclect Quality Inspection Template before submiting document'))
		}
	},

	brix_value:function(frm,cdt, cdn) {
		var child = locals[cdt][cdn];
		frappe.call({
	        method: 'nrp_manufacturing.modules.gourmet.quality_inspection.quality_inspection.get_brix_value',
	        args: {
			    self: frm.doc
    		},
		    callback: function(data) {
		          if(isNaN(data.message) || data.message == "" || data.message == null || data.message <= 0.0  ){
		        data.message =0.00
		        }
		            frappe.model.set_value(frm.doc.readings[0].doctype, frm.doc.readings[0].name, "reading_1", parseFloat(data.message).toFixed(3));
           var child = locals[cdt][cdn];
             frappe.model.set_value(frm.doc.readings[0].doctype, frm.doc.readings[2].name, "reading_1", parseFloat(((parseFloat(child.readings[1].reading_1)*0.26)/parseFloat(frappe.utils.get_config_by_name("SPECIFIC_GRAVITY")))).toFixed(3));
             frappe.model.set_value(frm.doc.readings[0].doctype, frm.doc.readings[3].name, "reading_1", parseFloat(((parseFloat(child.readings[2].reading_1)/parseFloat(child.readings[0].reading_1))*parseFloat(100).toFixed(3))));
             frappe.model.set_value(frm.doc.readings[0].doctype, frm.doc.readings[6].name, "reading_1", parseFloat(((parseFloat(500)-parseFloat(child.readings[4].reading_1))/parseFloat(500).toFixed(3))));
             frappe.model.set_value(frm.doc.readings[0].doctype, frm.doc.readings[7].name, "reading_1", parseFloat( (parseFloat( parseFloat(frappe.utils.get_config_by_name("SUGAR_PURITY") )*( parseFloat(child.readings[3].reading_1) - parseFloat(frappe.utils.get_config_by_name("FINAL_MOLASSES"))) )) / (parseFloat(child.readings[3].reading_1) * ( parseFloat(frappe.utils.get_config_by_name("SUGAR_PURITY") ) -  parseFloat(frappe.utils.get_config_by_name("FINAL_MOLASSES"))))).toFixed(3));
            frappe.model.set_value(frm.doc.readings[0].doctype, frm.doc.readings[5].name, "reading_1", parseFloat(((parseFloat(child.readings[2].reading_1)*parseFloat(child.readings[7].reading_1)*parseFloat(child.readings[6].reading_1)*parseFloat(frappe.utils.get_config_by_name("LIQUIDATION_FACTOR"))*parseFloat(frappe.utils.get_config_by_name("BHE")).toFixed(3)))));
                 
               
                }
        });
        
	},

	pol_value:function(frm,cdt, cdn) {
		var child = locals[cdt][cdn];
		frappe.call({
	        method: 'nrp_manufacturing.modules.gourmet.quality_inspection.quality_inspection.get_poles_value',
	        args: {
			    self: frm.doc
    		},
		    callback: function(data) {
		        if(isNaN(data.message) || data.message == "" || data.message == null || data.message <= 0.0  ){
		        data.message =0.00
		        }
		       frappe.model.set_value(frm.doc.readings[0].doctype, frm.doc.readings[1].name, "reading_1", parseFloat(data.message).toFixed(3));
            var child = locals[cdt][cdn];
             frappe.model.set_value(frm.doc.readings[0].doctype, frm.doc.readings[2].name, "reading_1", parseFloat(((parseFloat(child.readings[1].reading_1)*0.26)/parseFloat(frappe.utils.get_config_by_name("SPECIFIC_GRAVITY")))).toFixed(3));
             frappe.model.set_value(frm.doc.readings[0].doctype, frm.doc.readings[3].name, "reading_1", parseFloat(((parseFloat(child.readings[2].reading_1)/parseFloat(child.readings[0].reading_1))*parseFloat(100).toFixed(3))));
             frappe.model.set_value(frm.doc.readings[0].doctype, frm.doc.readings[6].name, "reading_1", parseFloat(((parseFloat(500)-parseFloat(child.readings[4].reading_1))/parseFloat(500).toFixed(3))));
             frappe.model.set_value(frm.doc.readings[0].doctype, frm.doc.readings[7].name, "reading_1", parseFloat( (parseFloat( parseFloat(frappe.utils.get_config_by_name("SUGAR_PURITY") )*( parseFloat(child.readings[3].reading_1) - parseFloat(frappe.utils.get_config_by_name("FINAL_MOLASSES"))) )) / (parseFloat(child.readings[3].reading_1) * ( parseFloat(frappe.utils.get_config_by_name("SUGAR_PURITY") ) -  parseFloat(frappe.utils.get_config_by_name("FINAL_MOLASSES"))))).toFixed(3));
            frappe.model.set_value(frm.doc.readings[0].doctype, frm.doc.readings[5].name, "reading_1", parseFloat(((parseFloat(child.readings[2].reading_1)*parseFloat(child.readings[7].reading_1)*parseFloat(child.readings[6].reading_1)*parseFloat(frappe.utils.get_config_by_name("LIQUIDATION_FACTOR"))*parseFloat(frappe.utils.get_config_by_name("BHE")).toFixed(3)))));
               }
        });
                             
	},

	cake_weight:function(frm,cdt, cdn) {
		var child = locals[cdt][cdn];
		frappe.call({
	        method: 'nrp_manufacturing.modules.gourmet.quality_inspection.quality_inspection.cake_weight_value',
	        args: {
			    self: frm.doc
    		},
		    callback: function(data) {
		            if(isNaN(data.message) || data.message == "" || data.message == null || data.message <= 0.0  ){
		        data.message =0.00
		        }
		            frappe.model.set_value(frm.doc.readings[0].doctype, frm.doc.readings[4].name, "reading_1", parseFloat(data.message).toFixed(3));
              var child = locals[cdt][cdn];
             frappe.model.set_value(frm.doc.readings[0].doctype, frm.doc.readings[2].name, "reading_1", parseFloat(((parseFloat(child.readings[1].reading_1)*0.26)/parseFloat(frappe.utils.get_config_by_name("SPECIFIC_GRAVITY")))).toFixed(3));
             frappe.model.set_value(frm.doc.readings[0].doctype, frm.doc.readings[3].name, "reading_1", parseFloat(((parseFloat(child.readings[2].reading_1)/parseFloat(child.readings[0].reading_1))*parseFloat(100).toFixed(3))));
             frappe.model.set_value(frm.doc.readings[0].doctype, frm.doc.readings[6].name, "reading_1", parseFloat(((parseFloat(500)-parseFloat(child.readings[4].reading_1))/parseFloat(500).toFixed(3))));
             frappe.model.set_value(frm.doc.readings[0].doctype, frm.doc.readings[7].name, "reading_1", parseFloat( (parseFloat( parseFloat(frappe.utils.get_config_by_name("SUGAR_PURITY") )*( parseFloat(child.readings[3].reading_1) - parseFloat(frappe.utils.get_config_by_name("FINAL_MOLASSES"))) )) / (parseFloat(child.readings[3].reading_1) * ( parseFloat(frappe.utils.get_config_by_name("SUGAR_PURITY") ) -  parseFloat(frappe.utils.get_config_by_name("FINAL_MOLASSES"))))).toFixed(3));
            frappe.model.set_value(frm.doc.readings[0].doctype, frm.doc.readings[5].name, "reading_1", parseFloat(((parseFloat(child.readings[2].reading_1)*parseFloat(child.readings[7].reading_1)*parseFloat(child.readings[6].reading_1)*parseFloat(frappe.utils.get_config_by_name("LIQUIDATION_FACTOR"))*parseFloat(frappe.utils.get_config_by_name("BHE")).toFixed(3)))));
              
                }
        });
	}


})

// item code based on GRN/DN
cur_frm.fields_dict['item_code'].get_query = function(doc, cdt, cdn) {
	const doctype = (doc.reference_type == "Stock Entry") ?
		"Stock Entry Detail" : doc.reference_type + " Item";

	if (doc.reference_type && doc.reference_name) {
		return {
			query: "erpnext.stock.doctype.quality_inspection.quality_inspection.item_query",
			filters: {
				"from": doctype,
				"parent": doc.reference_name,
				"inspection_type": doc.inspection_type
			}
		};
	}
},

// Serial No based on item_code
cur_frm.fields_dict['item_serial_no'].get_query = function(doc, cdt, cdn) {
	var filters = {};
	if (doc.item_code) {
		filters = {
			'item_code': doc.item_code
		}
	}
	return { filters: filters }
}

cur_frm.set_query("batch_no", function(doc) {
	return {
		filters: {
			"item": doc.item_code
		}
	}
})

cur_frm.add_fetch('item_code', 'item_name', 'item_name');
cur_frm.add_fetch('item_code', 'description', 'description');

