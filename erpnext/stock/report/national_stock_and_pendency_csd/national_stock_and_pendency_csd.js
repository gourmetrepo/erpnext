// Copyright (c) 2016, GICOH and contributors
// For license information, please see license.txt
/* eslint-disable */

frappe.query_reports["National Stock and Pendency CSD"] = {
	"filters": [
		{
			"fieldname": "from_date",
			"label": __("From Date"),
			"fieldtype": "Date",
			"default": frappe.datetime.get_today(),
			"reqd": 1
		},
		{
			"fieldname": "to_date",
			"label": __("To Date"),
			"fieldtype": "Date",
			"default": frappe.datetime.get_today(),
			"reqd": 1
		},
		{
			"fieldname": "company",
			"label": __("Company"),
			"fieldtype": "Select",
			"options": "ALL\nUnit 5\nUnit 8\nUnit 11",
			"reqd": 1,
			"on_change" : function(){
				frappe.query_report.get_filter("warehouse").value = "";
				frappe.query_report.get_filter('warehouse').refresh();
				frappe.query_report.refresh();
			}
		},
		{
			"fieldname": "warehouse",
			"label": __("Warehouse"),
			"fieldtype": "MultiSelectList",
			"get_data": function(txt) {
				if (frappe.query_report.get_filter_value("company") != "ALL") {
					return frappe.db.get_link_options('Warehouse', txt, {
							"company" : frappe.query_report.get_filter_value("company")
						});
				}else{
					return frappe.db.get_link_options('Warehouse', txt, {
						"company" : ["in", ["Unit 5", "Unit 8", "Unit 11"]]
					});
				}
			},
			"reqd": 1
		}
	],
	"onload": function(report) {
				var styleElement = document.createElement('style');
				var cssStyles = '.dt-instance-1 .dt-cell--col-1 {position: sticky; left: 30px; z-index: 1 !important;}'+
								'.dt-instance-1 .dt-cell--col-0 {position: sticky; left: 0px; z-index: 1 !important;}';
		
				styleElement.innerHTML = cssStyles;
				document.head.appendChild(styleElement);
			},
	"formatter": function (value, row, column, data, default_formatter) {
		value = default_formatter(value, row, column, data);

		if (column.fieldname == "stock_unit_5" || column.fieldname == "pending_unit_5" || column.fieldname == "net_stock_unit_5" || column.fieldname == "dn_unit_5" || column.fieldname == "sor_unit_5") {
			let $value = $(value).css("background-color", "#ccffdd");
			value = $value.wrap("<p></p>").parent().html();
		}
		else if (column.fieldname == "stock_unit_8" || column.fieldname == "pending_unit_8" || column.fieldname == "net_stock_unit_8" || column.fieldname == "dn_unit_8" || column.fieldname == "sor_unit_8") {
			let $value = $(value).css("background-color", "#ffffb3");
			value = $value.wrap("<p></p>").parent().html();
		}
		else if (column.fieldname == "stock_unit_11" || column.fieldname == "pending_unit_11" || column.fieldname == "net_stock_unit_11" || column.fieldname == "dn_unit_11" || column.fieldname == "sor_unit_11") {
			let $value = $(value).css("background-color", "#d9b3ff");
			value = $value.wrap("<p></p>").parent().html();
		}

		return value;
	},
	"treeView": true,
	"name_field": "item_section",
	"parent_field": "parent_item_section",
	"initial_depth": 0
};
