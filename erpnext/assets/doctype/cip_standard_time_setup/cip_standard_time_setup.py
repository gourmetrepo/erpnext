# -*- coding: utf-8 -*-
# Copyright (c) 2024, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

from __future__ import unicode_literals
import frappe
from frappe.model.document import Document

class CIPStandardTimeSetup(Document):
	def before_save(self):
		if self.is_new():
			existing_document = frappe.db.sql("""SELECT `name` FROM `tabCIP Standard Time Setup` WHERE `cip_type`=%s AND `cip_section`=%s""", (self.cip_type, self.cip_section), as_dict=1)

			if len(existing_document) > 0 and len(existing_document[0]) > 0:
				frappe.throw(f"Setup for standard time for type {self.cip_type} and section {self.cip_section} already exists")