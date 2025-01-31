// Copyright (c) 2018, Frappe Technologies Pvt. Ltd. and contributors
// For license information, please see license.txt
cur_frm.add_fetch('employee', 'company', 'company');

frappe.ui.form.on('Attendance Request', {

	setup: function(frm) {
		if(!(frappe.user.has_role(frappe.utils.get_config_by_name("ATTENDANCE_REQUEST_RESTRICTION_EXCLUDED_ROLES",["HR Manager"])))){
            frappe.db.get_list("Employee", {
				filters: { 'user_id': frappe.session.user},
				fields: ["department"]
			}).then((data) => {
				if(data.length > 0){
					var departments = frappe.utils.get_config_by_name("ATTENDANCE_REQUEST_RESTRICTED_DEPARTMENTS", []);
					var allowed_reasons = frappe.utils.get_config_by_name("ALLOWED_ATTENDANCE_REQUEST_REASONS_FOR_RESTRICTED_DEPARTMENTS", []);
					if( departments.indexOf(data[0].department) > -1 ) {
						frm.set_df_property('reason', 'options', allowed_reasons);
					}
				}
			});
        }
	},
	refresh(frm) {
		if(!(frappe.user.has_role(frappe.utils.get_config_by_name("ATTENDANCE_REQUEST_RESTRICTION_EXCLUDED_ROLES",["HR Manager"])))){
	        frappe.db.get_list("Employee", {
				filters: { 'user_id': frappe.session.user},
				fields: ["department"]
			}).then((data) => {
				if(data.length > 0){
					var departments = frappe.utils.get_config_by_name("ATTENDANCE_REQUEST_RESTRICTED_DEPARTMENTS", []);
					var allowed_reasons = frappe.utils.get_config_by_name("ALLOWED_ATTENDANCE_REQUEST_REASONS_FOR_RESTRICTED_DEPARTMENTS", []);
					if( departments.indexOf(data[0].department) > -1 ) {
						frm.set_df_property('reason', 'options', allowed_reasons);
					}
				}
			});
	    }
	},
	half_day: function(frm) {
		if(frm.doc.half_day == 1){
			frm.set_df_property('half_day_date', 'reqd', true);
		}
		else{
			frm.set_df_property('half_day_date', 'reqd', false);
		}
	}
});
