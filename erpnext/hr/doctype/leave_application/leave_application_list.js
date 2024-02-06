frappe.listview_settings['Leave Application'] = {
	add_fields: ["leave_type", "employee", "employee_name", "total_leave_days", "from_date", "to_date"],
	get_indicator: function (doc) {
		if (doc.status === "Approved") {
			return [__("Approved"), "green", "status,=,Approved"];
		} else if (doc.status === "Rejected") {
			return [__("Rejected"), "red", "status,=,Rejected"];
		} else {
			return [__("Open"), "red", "status,=,Open"];
		}
	},
	onload: function(me) {
		if (Object.values(frappe.route_options).length == 0){
			frappe.route_options = {
				"employee_name":frappe.session.user_fullname,
				"creation":["Between",[frappe.datetime.add_days(frappe.datetime.get_today(), -30),frappe.datetime.get_today()]]
			};
		}
	}
};
