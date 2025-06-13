# Copyright (c) 2015, Frappe Technologies Pvt. Ltd. and Contributors
# License: GNU General Public License v3. See license.txt

# For license information, please see license.txt

from __future__ import unicode_literals
from frappe.model.document import Document
import frappe
from frappe import _
from frappe.model.naming import make_autoname
from frappe.utils import nowdate, date_diff, comma_and, flt, validate_email_address
from nerp.utils import get_config_by_name
import requests
import json


class JobApplicant(Document):
	def autoname(self):
		full_name = self.full_name or ""
		position_title = self.position_title or ""
		self.series = f"{self.email}-.#####"
		self.title = f"{full_name}-{position_title}"
		self.name = make_autoname(self.series)

	def validate(self):
		from nerp.utils import validate_cnic_mask
		if self.cnic and not validate_cnic_mask(self.cnic):
			frappe.throw("CNIC '{0}' format is invalid".format(self.cnic))

	def before_save(self):
		if self.is_new() and self.job_applicant_status != "Applied":
			frappe.throw(_("Job Applicant can only be created with status <b>Applied</b>."))

		if not self.job_application_date:
			self.job_application_date = frappe.utils.nowdate()
		self.calculate_total_work_experience()

	def calculate_total_work_experience(self):
		total_experience = 0
		
		if self.work_experience:
			for we in self.work_experience:
				diff = 0
				if we.end_date:
					diff = date_diff(we.end_date, we.joining_date)
				elif we.currently_employed:
					diff = date_diff(nowdate(), we.joining_date)

				if diff > 0:
					total_experience += diff
		
		if total_experience:
			self.total_work_experience_years = flt(total_experience / 365, 1)


@frappe.whitelist()
def update_job_applicant_status_to_career_portal(doc, method=None):
	old_status = frappe.db.get_value("Job Applicant", doc.name, "job_applicant_status")
	baseurl =  get_config_by_name("Career_PORTAL_BASE_URL")
	if old_status != doc.job_applicant_status:
		frappe.db.set_value("Job Applicant", doc.name, "job_applicant_status", doc.job_applicant_status)
		url = f"{baseurl}api/user/applications/{doc.career_portal}/status"
		payload = {"status": doc.job_applicant_status}
		headers = {'Content-Type': 'application/json', 'Accept': 'application/json', 'Authorization': get_config_by_name("CAREER_PORTAL_API_TOKEN")}
		try:
			for x in range(1, 4):
				
				res = requests.request("POST", url, headers=headers, data= json.dumps(payload))
				integeration_payload = str(json.dumps(payload))

				nrp_integeration = {
					"ref_doctype": "Job Applicant",
					"doctype": "Nrp Integration",
					"request": integeration_payload
				}

				nrp_integeration["title"] = "On update job applicant --- {0}".format(doc.name)
				nrp_integeration["response"] = str(res.status_code) + ': ' + res.reason

				frappe.get_doc(nrp_integeration).save(ignore_permissions=True)
				frappe.db.commit()

				if res.status_code != 200:
					frappe.log_error(message=res.reason, title="Error in Career Portal Api | Status: {0} Retery: {1}".format(str(res.status_code),x))
				else:
					break
		except requests.exceptions.RequestException as e:
			frappe.log_error(f"Failed to sync Applicant status: {str(e)}", "Job Applicant Status Sync")
