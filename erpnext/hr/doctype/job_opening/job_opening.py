# Copyright (c) 2015, Frappe Technologies Pvt. Ltd. and Contributors
# License: GNU General Public License v3. See license.txt

# For license information, please see license.txt

from __future__ import unicode_literals
import frappe
from frappe.model.document import Document
from frappe import _
from nerp.utils import get_config_by_name
import requests
import json
from frappe.model.naming import make_autoname


class JobOpening(Document):
	def autoname(self):
		self.title = f"{self.position_title}"

	def before_save(self):
		if self.is_new() and self.job_opening_status != "Open":
			frappe.throw(_("Job Opening can only be created with status <b>Open<b>."))

		if not self.creation_date:
			self.creation_date = frappe.utils.nowdate()
		
		# self.load_competencies()
		
	def load_competencies(self):
		"""Load competencies from the selected position"""
		if self.position:
			position_doc = frappe.get_doc("Position", self.position)

			self.required_core_skills = []
			for core_skill in position_doc.required_core_skills:
				core_doc = frappe.new_doc("Core Skills")
				core_doc.update({
					"skill": core_skill.get("skill"),
					"required_proficiency_level": core_skill.get("required_proficiency_level"),
				})
				self.append("required_core_skills", core_doc)
			
			self.required_behavioral_competencies = []
			for behavioral_competency in position_doc.required_behavioral_competencies:
				behavioral_doc = frappe.new_doc("Behavioral Skills")
				behavioral_doc.update({
					"skill": behavioral_competency.get("skill"),
					"required_proficiency_level": behavioral_competency.get("required_proficiency_level"),
					
				})
				self.append("required_behavioral_competencies", behavioral_doc)


@frappe.whitelist()
def sync_job_opening_to_career_portal(doc, method=None):
	if doc:
		field_names = [
			"name", "creation", "modified", "modified_by", "owner", "docstatus", "parent", "parentfield",
			"parenttype", "idx", "job_title", "company", "status", "designation", "department",
			"staffing_plan", "route", "_user_tags",
			"_comments", "_assign", "_liked_by", "branch", "sub_branch", "job_opening_status",
			"posting_date", "job_requisition_id", "position_title", "cadre", "grade", "location",
			"no_of_openings", "required_education", "required_specialization", "required_certification",
			 "required_behavioral_competencies", "required_to_work_in_shifts",
			"required_to_travel", "required_background_check",
			"should_be_able_to_join_in_days", "preferred_interview_mode", "minimum_salary",
			"maximum_salary", "brief_summary", "main_responsibilities", "position"
		]

		payload = {}

		for field in field_names:
			value = getattr(doc, field, None)
			if isinstance(value, list):
				child_list = [child_doc.as_dict() for child_doc in value if hasattr(child_doc, 'as_dict')]
				if field in ["required_core_skills", "required_behavioral_competencies"]:
					payload[field] = "Dummy data"
				else:
					payload[field] = child_list
			else:
				payload[field] = getattr(doc, field, None)

		base_url = get_config_by_name("Career_PORTAL_BASE_URL")

		url  = f"{base_url}api/jobs/create"
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

				nrp_integeration["title"] = "On job opening  --- {0}".format(doc.name)
				nrp_integeration["response"] = str(res.status_code) + ': ' + res.reason
				frappe.get_doc(nrp_integeration).save(ignore_permissions=True)
				frappe.db.commit()
				if res.status_code != 201:
					frappe.log_error(message=res.reason, title="Error in Career Portal Api | Status: {0} Retery: {1}".format(str(res.status_code),x))
				else:
					break

		except requests.exceptions.RequestException as e:
			frappe.log_error(f"Failed to sync job opening to Career Portal: {str(e)}", "Job Opening Sync")

@frappe.whitelist()
def update_job_opening_status_to_career_portal(doc, method=None):
	old_status = frappe.db.get_value("Job Opening", doc.name, "job_opening_status")
	baseurl =  get_config_by_name("Career_PORTAL_BASE_URL")
	if old_status != doc.job_opening_status:
		frappe.db.set_value("Job Opening", doc.name, "job_opening_status", doc.job_opening_status)
		url = f"{baseurl}api/jobs/{doc.name}/status"
		payload = {"job_opening_status": doc.job_opening_status}
		headers = {'Content-Type': 'application/json', 'Accept': 'application/json', 'Authorization': get_config_by_name("CAREER_PORTAL_API_TOKEN")}
		try:
			for x in range(1, 4):
				
				res = requests.request("POST", url, headers=headers, data= json.dumps(payload))
				integeration_payload = str(json.dumps(payload))

				# To maintain logs
				nrp_integeration = {
					"ref_doctype": "Job Opening",
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
