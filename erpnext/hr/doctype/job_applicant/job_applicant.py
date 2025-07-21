# Copyright (c) 2015, Frappe Technologies Pvt. Ltd. and Contributors
# License: GNU General Public License v3. See license.txt

# For license information, please see license.txt

from __future__ import unicode_literals
from frappe.model.document import Document
import frappe
from frappe import _
from frappe.model.mapper import get_mapped_doc
from frappe.model.naming import make_autoname
from frappe.utils import nowdate, date_diff, comma_and, flt, validate_email_address
from nerp.utils import get_config_by_name
import requests
import json


class JobApplicant(Document):
	def autoname(self):
		if not self.full_name:
			self.update_full_name()
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
   
	def update_full_name(self):
		names = [self.first_name, self.middle_name, self.last_name]
		self.full_name = ' '.join(name for name in names if name)

@frappe.whitelist()
def update_job_applicant_status_to_career_portal(doc, method=None):
	old_status = frappe.db.get_value("Job Applicant", doc.name, "job_applicant_status")
	baseurl =  get_config_by_name("Career_PORTAL_BASE_URL")
	if old_status != doc.job_applicant_status:
		frappe.db.set_value("Job Applicant", doc.name, "job_applicant_status", doc.job_applicant_status)
		url = f"{baseurl}api/user/applications/{doc.source_id}/status"
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


@frappe.whitelist()
def make_employee(source_name, target_doc=None):
    def set_values(source, target):
        # Basic Info
        target.first_name = source.first_name
        target.middle_name = source.middle_name
        target.last_name = source.last_name
        # target.full_name = source.full_name
        target.gender = source.gender
        target.date_of_birth = source.date_of_birth
        target.personal_email = source.email
        target.cell_number = source.contact
        target.status = "Pending"
        
        # Identity Details
        target.cnic_no = source.cnic
        target.nationality = source.nationality
        target.father_name = source.father_name
        target.passport_number = source.passport
        target.passport_issue_date = source.passport_issue_date
        target.passport_valid_upto = source.passport_valid_upto

        # Employment Details
        target.designation = source.position_title

        target.company = source.company
        target.applicant_id = source.name

        # Location
        target.current_address = source.current_address
        target.permanent_address = source.permanent_address

        # Preferences
        target.availability_to_join_in_days = source.availability_to_join_in_days

        target.linkedin_profile = source.linkedin_profile

        map_child_table(source, target, "work_experience", "Employee External Work History", {
            "joining_date": "joining_date",
            "end_date": "end_date",
            "company_name": "company_name",
            "designation": "designation",
            "last_drawn_salary": "salary"
        })

        map_child_table(source, target, "references", "Reference Details", {
            "reference_full_name": "name1",
            "relationship": "relationship",
            "reference_contact": "contact_number",
            "reference_email": "email"
        })

    def map_child_table(source, target, source_table, target_table, field_map):
        source_children = source.get(source_table)
        if not source_children:
            return

        target.set(target_table, []) 
        for child in source_children:
            mapped_child = frappe.new_doc(target_table).as_dict()
            for src_field, tgt_field in field_map.items():
                mapped_child[tgt_field] = child.get(src_field)
            target.append(target_table, mapped_child)

    mapped_doc = get_mapped_doc(
        "Job Applicant", source_name,
        {
            "Job Applicant": {
                "doctype": "Employee",
            }
        },
        target_doc, set_values
    )

    return mapped_doc
