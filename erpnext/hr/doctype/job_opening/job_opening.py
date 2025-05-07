# Copyright (c) 2015, Frappe Technologies Pvt. Ltd. and Contributors
# License: GNU General Public License v3. See license.txt

# For license information, please see license.txt

from __future__ import unicode_literals
import frappe
from frappe.model.document import Document
from frappe import _

class JobOpening(Document):
	def before_save(self):
		if self.is_new():
			self.job_opening_status = "Open"

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