// Copyright (c) 2016, Frappe Technologies Pvt. Ltd. and contributors
// For license information, please see license.txt
/* eslint-disable */

frappe.query_reports["Work Order Tracking"] = {
	"filters": [
		{
			"fieldname": "company",
			"label": __("Company"),
			"fieldtype": "Select",
			"options": "ALL\nUnit 5\nUnit 8\nUnit 11",
			"reqd": 1
		},
		{
			"fieldname": "from_date",
			"label": __("From Date"),
			"fieldtype": "Date",
			"reqd": 1
		},
		{
			"fieldname": "to_date",
			"label": __("To Date"),
			"fieldtype": "Date",
			"reqd": 1
		},
		{
			"fieldname": "item_category",
			"label": __("Item Category"),
			"fieldtype": "Select",
			"options": "ALL\nFinished Good\nSemi Finished Good",
			"default": "Finished Good",
			"reqd": 1
		},
		{
			"fieldname": "work_order_status",
			"label": __("Work Order Status"),
			"fieldtype": "Select",
			"options": "ALL\nOpen\nClosed",
			"default": "ALL",
			"reqd": 1
		},
	]
};
