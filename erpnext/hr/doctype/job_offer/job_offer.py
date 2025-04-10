# Copyright (c) 2015, Frappe Technologies Pvt. Ltd. and Contributors and contributors
# For license information, please see license.txt

from __future__ import unicode_literals
import frappe
from frappe.utils import cint
from frappe.model.document import Document
from frappe.model.mapper import get_mapped_doc
from frappe import _
from frappe.utils.data import get_link_to_form

class JobOffer(Document):
	pass

def update_job_applicant(status, job_applicant):
	if status in ("Accepted", "Rejected"):
		frappe.set_value("Job Applicant", job_applicant, "status", status)

def get_staffing_plan_detail(designation, company, offer_date):
	detail = frappe.db.sql("""
		SELECT DISTINCT spd.parent,
			sp.from_date as from_date,
			sp.to_date as to_date,
			sp.name,
			sum(spd.vacancies) as vacancies,
			spd.designation
		FROM `tabStaffing Plan Detail` spd, `tabStaffing Plan` sp
		WHERE
			sp.docstatus=1
			AND spd.designation=%s
			AND sp.company=%s
			AND spd.parent = sp.name
			AND %s between sp.from_date and sp.to_date
	""", (designation, company, offer_date), as_dict=1)

	return frappe._dict(detail[0]) if (detail and detail[0].parent) else None

@frappe.whitelist()
def make_employee(source_name, target_doc=None):
	def set_missing_values(source, target):
		target.personal_email = frappe.db.get_value("Job Applicant", source.job_applicant, "email_id")
	doc = get_mapped_doc("Job Offer", source_name, {
			"Job Offer": {
				"doctype": "Employee",
				"field_map": {
					"applicant_name": "employee_name",
				}}
		}, target_doc, set_missing_values)
	return doc
