frappe.listview_settings['Asset Maintenance'] = {
	get_indicator: function(doc) {
		if(doc.status==="MR Generated") {
			return [__("MR Generated"), "orange", "status,=,MR Generated"];
		}
	}
	
};
