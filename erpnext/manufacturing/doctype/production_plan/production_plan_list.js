frappe.listview_settings['Production Plan'] = {
	add_fields: ["status"],
	//filters: [["status", "!=", "Stopped"]],
	get_indicator: function(doc) {
		if(doc.status==="Submitted") {
			return [__("Not Started"), "orange", "status,=,Submitted"];
		} else {
			return [__(doc.status), {
				"Draft": "red",
				"In Process": "orange",
				"Completed": "green",
				"Material Requested": "darkgrey",
				"Cancelled": "darkgrey"
			}[doc.status], "status,=," + doc.status];
		}
	},
		onload: function(me) {
		if (Object.values(frappe.route_options).length == 0){
			frappe.route_options = {
				"company": frappe.get_cookie('company') ,
				"creation":["Between",[frappe.datetime.add_days(frappe.datetime.get_today(), -10),frappe.datetime.add_days(frappe.datetime.get_today(), +10)]]
			};
		}
	},
};
