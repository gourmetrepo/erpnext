frappe.listview_settings['Employee Checkin'] = {
	onload: function(me) {
		if (Object.values(frappe.route_options).length == 0){
			frappe.route_options = {
				// "status": "Draft",
				"employee_name": frappe.get_cookie('full_name'),
				"creation":["Between",[frappe.datetime.add_days(frappe.datetime.get_today(), -5),frappe.datetime.get_today()]]
			};
		}
	}
	
};
