frappe.listview_settings['Asset Maintenance'] = {
	add_fields: ['status'],
	get_indicator: function(doc) {
		if (doc.status === "Completed" || doc.status === "Closed" || doc.status === "Finished") {
			return [__(doc.status), "green", "status,=," + doc.status];
		} else if(doc.status === "In Process"){
			return [__(doc.status), "orange", "status,=," + doc.status];
		}else{
			return [__(doc.status), "red", "status,=," + doc.status];
		}
	},
	
};
