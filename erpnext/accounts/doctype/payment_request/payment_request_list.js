frappe.listview_settings['Payment Request'] = {
	onload: function(me) {
		if (Object.values(frappe.route_options).length == 0){
			frappe.route_options = {
				"company": frappe.get_cookie('company') ,
				"creation":["Between",[frappe.datetime.add_days(frappe.datetime.get_today(), -10),frappe.datetime.get_today()]]
			};
		}
	},
	add_fields: ["status"],
	get_indicator: function(doc) {
		if(doc.status == "Draft") {
			return [__("Draft"), "darkgrey", "status,=,Draft"];
		}
		if(doc.status == "Requested") {
			return [__("Requested"), "green", "status,=,Requested"];
		}
		else if(doc.status == "Initiated") {
			return [__("Initiated"), "green", "status,=,Initiated"];
		}
		else if(doc.status == "Partially Paid") {
			return [__("Partially Paid"), "orange", "status,=,Partially Paid"];
		}
		else if(doc.status == "Paid") {
			return [__("Paid"), "blue", "status,=,Paid"];
		}
		else if(doc.status == "Cancelled") {
			return [__("Cancelled"), "red", "status,=,Cancelled"];
		}
	}	
}
