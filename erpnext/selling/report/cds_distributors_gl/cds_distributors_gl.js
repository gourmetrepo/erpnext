// Copyright (c) 2016, Frappe Technologies Pvt. Ltd. and contributors
// For license information, please see license.txt
/* eslint-disable */

frappe.query_reports["CDS Distributors GL"] = {
	"filters": [
		{
			"fieldname": "company",
			"label": __("Company"),
			"fieldtype": "Link",
			"options": "Company",
			"reqd": 1,
			"width": "80",
			"on_change": function () {
				frappe.query_report.get_filter("customer").set_value("");
			}

		},
		{
			"fieldname": "customer",
			"label": __("Customer"),
			"fieldtype": "Link",
			"options": "Customer",
			"width": "80",
			"get_query": function () {
				let company = frappe.query_report.get_filter_value("company");
				return {
					filters: {
						primary_company: company
					}
				};
			}
		},
		{
			"fieldname": "active",
			"label": __("Active"),
			"fieldtype": "Check",
			"default": 1,
			"width": "80"
		}

	]
};
