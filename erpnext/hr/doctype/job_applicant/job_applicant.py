# Copyright (c) 2015, Frappe Technologies Pvt. Ltd. and Contributors
# License: GNU General Public License v3. See license.txt

# For license information, please see license.txt

from __future__ import unicode_literals
from frappe.model.document import Document
import frappe
from frappe import _
from frappe.utils import comma_and, validate_email_address


class JobApplicant(Document):

	def validate(self):
		from nerp.utils import validate_cnic_mask
		if self.cnic and not validate_cnic_mask(self.cnic):
			frappe.throw("CNIC '{0}' format is invalid".format(self.cnic))

	def before_save(self):
		if not self.job_application_date:
			self.job_application_date = frappe.utils.nowdate()


