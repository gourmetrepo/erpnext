frappe.listview_settings['Leave Ledger Entry'] = {
	onload: function(me) {
		if (Object.values(frappe.route_options).length == 0){
			frappe.route_options = {
				"employee_name":frappe.session.user_fullname,
				"creation":["Between",[frappe.datetime.add_days(frappe.datetime.get_today(), -30),frappe.datetime.get_today()]]
			};
		}
	}
};