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
				try:
					cip_time = row.standard_time
					cip_time_part = cip_time.split(":")
					
					hours, minutes, seconds = 0, 0, 0
					if 0 < len(cip_time_part[0]) < 3 and 0 < len(cip_time_part[1]) < 3 and 0 < len(cip_time_part[2]) < 3:
						hours = int(cip_time_part[0])
						minutes = int(cip_time_part[1])
						seconds = int(cip_time_part[2])
					else:
						raise Exception			
					
					if hours < 0 or hours > 23 or minutes < 0 or minutes > 59 or seconds < 0 or seconds > 59:
						raise Exception
						
					cip_minutes = ((hours * 60) + minutes)
					if cip_minutes <= 0:
						frappe.throw(_("The Standard Time needs to be at least 1 minute."))
				except:
					frappe.throw(_(f"The Standard Time {row.standard_time} is invalid."))
