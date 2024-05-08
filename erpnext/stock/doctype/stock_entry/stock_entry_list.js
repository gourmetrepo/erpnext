frappe.listview_settings['Stock Entry'] = {
	onload: function(me) {
		if (Object.values(frappe.route_options).length == 0){
			frappe.route_options = {
				"company": frappe.get_cookie('company') ,
				"creation":["Between",[frappe.datetime.add_days(frappe.datetime.get_today(), - 10),frappe.datetime.get_today()]]
			};
		}
	},
	add_fields: ["`tabStock Entry`.`from_warehouse`", "`tabStock Entry`.`to_warehouse`",
		"`tabStock Entry`.`purpose`", "`tabStock Entry`.`work_order`", "`tabStock Entry`.`bom_no`"],
	get_indicator: function (doc) {
		if (doc.docstatus === 0) {
			return [__("Draft"), "red", "docstatus,=,0"];

		} else if (doc.purpose === 'Send to Warehouse' && doc.per_transferred < 100) {
			// not delivered & overdue
			return [__("Goods In Transit"), "grey", "per_transferred,<,100"];

		} else if (doc.purpose === 'Send to Warehouse' && doc.per_transferred === 100) {
			return [__("Goods Transferred"), "green", "per_transferred,=,100"];
		} else if (doc.docstatus === 2) {
			return [__("Canceled"), "red", "docstatus,=,2"];
		} else {
			return [__("Submitted"), "blue", "docstatus,=,1"];
		}
	},
	column_render: {
		"from_warehouse": function(doc) {
			var html = "";
			if(doc.from_warehouse) {
				html += '<span class="filterable h6"\
					data-filter="from_warehouse,=,'+doc.from_warehouse+'">'
						+doc.from_warehouse+' </span>';
			}
			// if(doc.from_warehouse || doc.to_warehouse) {
			// 	html += '<i class="fa fa-arrow-right text-muted"></i> ';
			// }
			if(doc.to_warehouse) {
				html += '<span class="filterable h6"\
				data-filter="to_warehouse,=,'+doc.to_warehouse+'">'+doc.to_warehouse+'</span>';
			}
			return html;
		}
	}
};
