frappe.listview_settings['Quality Inspection'] = {
	onload: function(me) {
		if (Object.values(frappe.route_options).length == 0){
			frappe.route_options = {
					"docstatus":"0",
				"creation":["Between",[frappe.datetime.add_days(frappe.datetime.get_today(), -20),frappe.datetime.get_today()]]
			};
		}
	}
};
