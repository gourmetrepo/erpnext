# -*- coding: utf-8 -*-
# Copyright (c) 2024, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

from __future__ import unicode_literals
import frappe
from frappe.model.document import Document

class CIPStandardTimeSetup(Document):
	def before_save(self):
		if self.is_new():
			existing_document = frappe.db.sql("""SELECT `name` FROM `tabCIP Standard Time Setup` WHERE `cip_type`=%s""", (self.cip_type))

			if len(existing_document) > 0 and len(existing_document[0]) > 0:
				frappe.throw("CIP Standard Time Setup for {} already exists".format(self.cip_type))