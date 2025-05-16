# Copyright (c) 2015, Frappe Technologies Pvt. Ltd. and Contributors
# License: GNU General Public License v3. See license.txt

# For license information, please see license.txt

from __future__ import unicode_literals
from frappe.model.document import Document
import frappe
from frappe import _
from frappe.model.naming import make_autoname
from frappe.utils import nowdate, date_diff, comma_and, flt, validate_email_address
from frappe.utils import comma_and, validate_email_address

sender_field = "email_id"

class DuplicationError(frappe.ValidationError): pass

class JobApplicant(Document):
	def autoname(self):
		full_name = self.full_name or ""
		position_title = self.position_title or ""
		self.series = f"{self.email}-.#####"
		self.title = f"{full_name}-{position_title}"
		self.name = make_autoname(self.series)

	def validate(self):
		self.check_email_id_is_unique()
		if self.email_id:
			validate_email_address(self.email_id, True)

		if not self.applicant_name and self.email_id:
			guess = self.email_id.split('@')[0]
			self.applicant_name = ' '.join([p.capitalize() for p in guess.split('.')])

	def check_email_id_is_unique(self):
		if self.email_id:
			names = frappe.db.sql_list("""select name from `tabJob Applicant`
				where email_id=%s and name!=%s and job_title=%s""", (self.email_id, self.name, self.job_title))

			if names:
				frappe.throw(_("Email Address must be unique, already exists for {0}").format(comma_and(names)), frappe.DuplicateEntryError)

