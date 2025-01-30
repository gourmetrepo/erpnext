frappe.listview_settings['Asset Maintenance'] = {
	get_indicator: function(doc) {
		var colors = {
			"Draft": "red",
			"Not Started": "yellow",
			"MR Generated": "orange",
			"In Process": "orange",
			"Completed": "green",
			"Stopped": "red",
			"Closed": "green",
			"Cancelled": "red"
		}
		return [__(doc.status), colors[doc.status], "status,=," + doc.status];
	},
	
};
