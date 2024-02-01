frappe.listview_settings['Work Order'] = {
	add_fields: ["bom_no", "status", "sales_order", "qty",
		"produced_qty", "expected_delivery_date", "planned_start_date", "planned_end_date"],
	//filters: [["status", "!=", "Stopped"]],
	get_indicator: function(doc) {
		if(doc.status==="Submitted") {
			return [__("Not Started"), "orange", "status,=,Submitted"];
		} else {
			return [__(doc.status), {
				"Draft": "red",
				"Stopped": "red",
				"Not Started": "red",
				"In Process": "orange",
				"Completed": "green",
				"Cancelled": "darkgrey"
			}[doc.status], "status,=," + doc.status];
		}
	},
	onload: function(frm) {
		console.log(frm.filters);
		frappe.route_options = {
			// "status":["!=","Stopped"],
			"company": frappe.get_cookie('company'),
			"creation": ["Between", [frappe.datetime.add_days(frappe.datetime.get_today(), -10), frappe.datetime.get_today()]],
		};
		if(frm.filters.length > 0){
		frm.filters.forEach(function(filter) {
			console.log(filter)
			frappe.route_options[filter[1]] = filter[3];
		});}
	},
};
