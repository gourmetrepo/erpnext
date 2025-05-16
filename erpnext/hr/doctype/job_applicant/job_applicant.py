# Copyright (c) 2015, Frappe Technologies Pvt. Ltd. and Contributors
# License: GNU General Public License v3. See license.txt

# For license information, please see license.txt

from __future__ import unicode_literals
from frappe.model.document import Document
import frappe
from frappe import _
from frappe.model.naming import make_autoname
from frappe.utils import nowdate, date_diff, comma_and, flt, validate_email_address


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


