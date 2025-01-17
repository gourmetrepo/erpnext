# -*- coding: utf-8 -*-
# Copyright (c) 2018, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

from __future__ import unicode_literals
import frappe
from frappe.model.document import Document
import re

class QualityInspectionTemplate(Document):
	def validate(self):
		regex = r'^[A-Za-z]+$'
		for item in self.item_quality_inspection_parameter:
			if item.type in ["String", "Str"]:
				if not re.match(regex, item.min_value or ""):
					frappe.throw(f"Invalid min_value '{item.min_value}'. Only A-Z and a-z are allowed.")
				if not re.match(regex, item.max_value or ""):
					frappe.throw(f"Invalid max_value '{item.max_value}'. Only A-Z and a-z are allowed.")
  

def get_template_details(template):
	if not template: return []

	return frappe.get_all('Item Quality Inspection Parameter', fields=["specification", "value", "type", "min_value", "max_value"],
		filters={'parenttype': 'Quality Inspection Template', 'parent': template}, order_by="idx")