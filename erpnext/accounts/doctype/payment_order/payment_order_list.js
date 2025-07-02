frappe.listview_settings['Payment Order'] = {
	onload: function(me) {
		if (Object.values(frappe.route_options).length == 0){
			frappe.route_options = {
				"creation":["Between",[frappe.datetime.add_days(frappe.datetime.get_today(), -20),frappe.datetime.get_today()]]
			};
		}
	}
};
