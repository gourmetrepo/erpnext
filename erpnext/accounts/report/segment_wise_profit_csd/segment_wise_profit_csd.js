// Copyright (c) 2016, Frappe Technologies Pvt. Ltd. and contributors
// For license information, please see license.txt
/* eslint-disable */

frappe.query_reports["Segment Wise Profit CSD"] = {
	"filters": [
		{
			fieldname:"from_date",
			reqd: 1,
			label: __("From Date"),
			fieldtype: "Date",
			default: frappe.datetime.get_today(),
			
		},
		{
			fieldname:"to_date",
			reqd: 1,
			default: frappe.datetime.add_days(frappe.datetime.get_today(), 10),
			label: __("To Date"),
			fieldtype: "Date",
		},				
		{
			fieldname:"company",
			reqd: 1,
			label: __("Company"),
			fieldtype: "Select",
			options: ["Unit 5", "Unit 8", "Unit 11"]
		}

	],
	"formatter": function(value, row, column, data, default_formatter) {
        if (data.indent == 0 || data.indent == 1 || data.indent == 2){
            if (data.indent == 0){
                color = '#3EAB36'
            }
            if (data.indent == 1){
                color = '#F15159'
            }
            if (data.indent == 2){
                color = '#9C6137'
            }
            return "<b style=\"color:"+color+"\">Rs "+value+"</b>";
        }else{
            return "<span style=\"color:#B600B8\"><b>Rs "+value+"</b></span>";
        }
    },
    "treeView": true,
    "name_field": "Total Profit",
    "parent_field": "parent_item_group",
    "initial_depth": 1
};
