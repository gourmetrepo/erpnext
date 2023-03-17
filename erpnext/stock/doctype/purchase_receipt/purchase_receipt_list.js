frappe.listview_settings['Purchase Receipt'] = {
	onload: function(me) {
		if (Object.values(frappe.route_options).length == 0){
		frappe.route_options = {
			// "status": "Draft",
			"creation":["Between",[frappe.datetime.add_days(frappe.datetime.get_today(), - 15),frappe.datetime.get_today()]]
		};
		}
	},
	add_fields: ["supplier", "supplier_name", "base_grand_total", "is_subcontracted",
		"transporter_name", "is_return", "status", "per_billed", "currency"],
	get_indicator: function(doc) {
		if(cint(doc.is_return)==1) {
			return [__("Return"), "darkgrey", "is_return,=,Yes"];
		} else if (doc.status === "Closed") {
			return [__("Closed"), "green", "status,=,Closed"];
		} else if (flt(doc.grand_total) !== 0 && flt(doc.per_billed, 2) < 100) {
			return [__("To Bill"), "orange", "per_billed,<,100"];
		} else if (flt(doc.grand_total) === 0 || flt(doc.per_billed, 2) == 100) {
			return [__("Completed"), "green", "per_billed,=,100"];
		}
	}
};
