// Copyright (c) 2017, Frappe Technologies Pvt. Ltd. and contributors
// For license information, please see license.txt

frappe.ui.form.on('Asset Maintenance Team', {
	refresh: function(frm) {
		frm.fields_dict['maintenance_team_members'].grid.get_field("team_member").get_query = function() {
			return {
				filters: {
					company: frm.doc.company
				}
			}
		}
	}
});
