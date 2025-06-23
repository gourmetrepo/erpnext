// Copyright (c) 2016, Frappe Technologies Pvt. Ltd. and contributors
// For license information, please see license.txt
/* eslint-disable */

frappe.query_reports["Job Applicant Details"] = {
	"filters": [
		{
			"fieldname":"job_opening",
			"label": __("Job Opening"),
			"fieldtype": "Link",
			"options": "Job Opening",
		},
		{
			"fieldname": "status",
			"label": __("Status"),
			"fieldtype": "Select",
			"options": [
				{"label": "Applied", "value": "Applied"},
				{"label": "Longlisted", "value": "Longlisted"},
				{"label": "Shortlisted", "value": "Shortlisted"},
				{"label": "Interview", "value": "Interview"},
				{"label": "Accepted", "value": "Accepted"},
				{"label": "Rejected", "value": "Rejected"},
				{"label": "On Hold", "value": "On Hold"},
				{"label": "Offered", "value": "Offered"},
				{"label": "Offer Accepted", "value": "Offer Accepted"},
				{"label": "Offer Rejected", "value": "Offer Rejected"},	
				{"label": "Hired", "value": "Hired"}
			],
			
		},
		{
			"fieldname":"platform",
			"label": __("Platform"),
			"fieldtype": "Link",
			"options": "Job Posting Sites",
		}

	]
};
