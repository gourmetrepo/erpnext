frappe.listview_settings['Stock Ledger Entry'] = {
	onload: function(me) {
		if (Object.values(frappe.route_options).length == 0){
			frappe.route_options = {
				// "status": "Draft",
				"creation":["Between",[frappe.datetime.add_days(frappe.datetime.get_today(), -1),frappe.datetime.get_today()]]
			};
		}
	}
	
};
