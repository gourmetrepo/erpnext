# -*- coding: utf-8 -*-
# Copyright (c) 2024, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

from __future__ import unicode_literals
import frappe
from frappe import _
from frappe.model.document import Document

class CIPStandardTimeSetup(Document):
	def before_save(self):
		if self.is_new():
			existing_document = frappe.db.sql("""SELECT `name` FROM `tabCIP Standard Time Setup` WHERE `cip_type`=%s AND `cip_section`=%s""", (self.cip_type, self.cip_section), as_dict=1)

			if len(existing_document) > 0 and len(existing_document[0]) > 0:
				frappe.throw(f"Setup for standard time for type {self.cip_type} and section {self.cip_section} already exists")
	
	# This code makes sure the standard time is never less than 1 minute
	def validate(self):
		for row in self.cip_standard_time:
			if row.standard_time:
				cip_time = row.standard_time
				cip_time_part = cip_time.split(":")
				hours = int(cip_time_part[0])
				minutes = int(cip_time_part[1])
				cip_minutes = ((hours * 60) + minutes)
				if cip_minutes <= 0:
					frappe.throw(_("The Standard Time needs to be at least 1 minute."))