# Copyright (c) 2013, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

from __future__ import unicode_literals
import frappe
from collections import defaultdict

def execute(filters=None):
	columns = get_columns(filters)
	data = get_data(filters)
	return columns, data


def get_columns(filters=None):
	return [
		{
			"label": "Platform",
			"fieldname": "platform",
			"fieldtype": "Data",
			"width": 190
		},
		{
			"label": "Applied",
			"fieldname": "applied",
			"fieldtype": "Int",
			"width": 120
		},
		{
			"label": "Longlisted",
			"fieldname": "longlisted",
			"fieldtype": "Int",
			"width": 120
		},
		{
			"label": "Shortlisted",
			"fieldname": "shortlisted",
			"fieldtype": "Int",
			"width": 120
		},
		{
			"label": "Interview",
			"fieldname": "interview",
			"fieldtype": "Int",
			"width": 120
		},
		{
			"label": "Accepted",
			"fieldname": "accepted",
			"fieldtype": "Int",
			"width": 120
		},
		{
			"label": "Rejected",
			"fieldname": "rejected",
			"fieldtype": "Int",
			"width": 120
		},
		{	"label": "On Hold",
			"fieldname": "on_hold",
			"fieldtype": "Int",
			"width": 120
		},
		{
			"label": "Offered",
			"fieldname": "offered",
			"fieldtype": "Int",
			"width": 120
		},
		{
			"label": "Offer Accepted",
			"fieldname": "offer_accepted",
			"fieldtype": "Int",
			"width": 130
		},
		{
			"label": "Offer Rejected",
			"fieldname": "offer_rejected",
			"fieldtype": "Int",
			"width": 130
		},
		{
			"label": "Hired",
			"fieldname": "hired",
			"fieldtype": "Int",
			"width": 130
		}
	]
 


def get_data(filters=None):
	if not filters or not filters.get('job_opening'):
		return []

	job_opening = filters.get('job_opening')

	raw_data = frappe.db.sql("""
		SELECT 
			source AS platform,
			job_applicant_status
		FROM `tabJob Applicant`
		WHERE applied_on = %(applied_on)s
	""", {"applied_on": job_opening}, as_dict=True)

	status_fields = [
		"applied", "longlisted", "shortlisted", "interview", "accepted",
		"rejected", "on_hold", "offered", "offer_accepted", "offer_rejected", "hired"
	]

	status_map = {
		"Applied": "applied",
		"Longlisted": "longlisted",
		"Shortlisted": "shortlisted",
		"Interview": "interview",
		"Accepted": "accepted",
		"Rejected": "rejected",
		"On Hold": "on_hold",
		"Offered": "offered",
		"Offer Accepted": "offer_accepted",
		"Offer Rejected": "offer_rejected",
		"Hired": "hired"
	}

	grouped_data = defaultdict(lambda: {key: 0 for key in status_fields})

	for row in raw_data:
		platform = row["platform"] or "Unknown"
		status = status_map.get(row["job_applicant_status"])
		if status:
			grouped_data[platform][status] += 1

	data = []
	for platform, stats in grouped_data.items():
		row = {"platform": platform}
		row.update(stats)
		data.append(row)

	return data
