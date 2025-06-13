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
	def on_update_after_submit(self):
		if self.applicant_id:
			if self.offer_status == "Accepted":
				frappe.db.set_value("Job Applicant", self.applicant_id, "job_applicant_status", "Offer Accepted")
			elif self.offer_status == "Declined":
				frappe.db.set_value("Job Applicant", self.applicant_id, "job_applicant_status", "Offer Rejected")

	def before_save(self):
		if self.is_new() and self.offer_status != "Offered":
			frappe.throw(_("Job Offer can only be created with status <b>Offered<b>"))
	
	def before_insert(self):
		if self.select_job_offer_template:
			self.apply_template_terms()

	def apply_template_terms(self):
		if self.select_job_offer_template:
			template = frappe.get_doc("Job Offer Term Template", self.select_job_offer_template)

			self.set("offer_terms", [])

			for t in template.terms:
				self.append("offer_terms", {
					"offer_term": t.offer_term,
					"value_description": t.description
				})

	def on_submit(self):
		if self.applicant_id:
			frappe.db.set_value("Job Applicant", self.applicant_id, "job_applicant_status", "Offered")

	def on_cancel(self):
		self.offer_status = "Cancelled"
		if self.applicant_id:
			frappe.db.set_value("Job Applicant", self.applicant_id, "job_applicant_status", "Accepted")


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


@frappe.whitelist()
def apply_offer_term_template(job_offer, template_name):   
	try:
		job_offer = frappe.get_doc("Job Offer", job_offer)
		template = frappe.get_doc("Job Offer Term Template", template_name)

		job_offer.set("offer_terms", [])

		for t in template.terms:
			job_offer.append("offer_terms", {
				"offer_term": t.offer_term,
				"value_description": t.description
			})
   
		job_offer.select_job_offer_template = template_name

		job_offer.save(ignore_permissions=True)
		frappe.db.commit()

		return {
			"status": "success",
			"message": f"Offer terms applied from template '{template_name}'",
			"job_offer": job_offer.name
		}

	except Exception as e:
		frappe.log_error(frappe.get_traceback(), "Apply Job Offer Template Failed")
		return {
			"status": "error",
			"message": str(e)
		}
