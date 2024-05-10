frappe.listview_settings['Item Tax Template'] = {

	onload: function(listview) {
			if (Object.values(frappe.route_options).length == 0){
			frappe.route_options = {
				"creation":["Between",[frappe.datetime.add_days(frappe.datetime.get_today(), -30),frappe.datetime.get_today()]]
			};
		}
	}
};
