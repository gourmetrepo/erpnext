frappe.listview_settings['Employee Checkin'] = {
	onload: function(me) {
		if (Object.values(frappe.route_options).length == 0){
			frappe.route_options = {
				// "status": "Draft",
				"employee": frappe.get_cookie("user_id") ,
				"creation":["Between",[frappe.datetime.add_days(frappe.datetime.get_today(), -5),frappe.datetime.get_today()]]
			};
		}
	}
	
};
