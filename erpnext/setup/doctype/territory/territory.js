// Copyright (c) 2015, Frappe Technologies Pvt. Ltd. and Contributors
// License: GNU General Public License v3. See license.txt

frappe.ui.form.on("Territory", {
	setup: function(frm) {
		frm.fields_dict["targets"].grid.get_field("distribution_id").get_query = function(doc, cdt, cdn){
			var row = locals[cdt][cdn];
			return {
				filters: {
					'fiscal_year': row.fiscal_year
				}
			}
		};
	},
	refresh(frm) {
	    frm.set_query("customer", function() {
            let filters = {
                "is_internal_customer": 1
            }
            return {
                "filters": filters
            };
        });
		frm.trigger("territory_type");
	},
	
	territory_type:function(frm){
        if(frm.doc.territory_type == "Internal"){
            frm.toggle_reqd("warehouse",true);
            frm.toggle_reqd("customer",false);
        }else if(frm.doc.territory_type == "Customer"){
            frm.toggle_reqd("customer",true);
            frm.toggle_reqd("warehouse",false);
        }
    }
});

cur_frm.cscript.refresh = function(doc, cdt, cdn) {
	cur_frm.cscript.set_root_readonly(doc);
}

cur_frm.cscript.set_root_readonly = function(doc) {
	// read-only for root territory
	if(!doc.parent_territory && !doc.__islocal) {
		cur_frm.set_read_only();
		cur_frm.set_intro(__("This is a root territory and cannot be edited."));
	} else {
		cur_frm.set_intro(null);
	}
}

//get query select territory
cur_frm.fields_dict['parent_territory'].get_query = function(doc,cdt,cdn) {
	return{
		filters:[
			['Territory', 'is_group', '=', 1],
			['Territory', 'name', '!=', doc.territory_name]
		]
	}
}