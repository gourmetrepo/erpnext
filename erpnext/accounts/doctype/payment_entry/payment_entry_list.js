frappe.listview_settings['Payment Entry'] = {

	onload: function(listview) {
		if (listview.filter_area.filter_list.filters.length == 0){
			frappe.route_options = {
				"company": frappe.get_cookie('company') ,
				"creation":["Between",[frappe.datetime.add_days(frappe.datetime.get_today(), -10),frappe.datetime.get_today()]]
			};
		}
		if (listview.page.fields_dict.party_type) {
			listview.page.fields_dict.party_type.get_query = function() {
				return {
					"filters": {
						"name": ["in", Object.keys(frappe.boot.party_account_types)],
					}
				};
			};
		}
	}
};
