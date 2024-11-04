# -*- coding: utf-8 -*-
# Copyright (c) 2024, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

from __future__ import unicode_literals
import frappe
from frappe.model.document import Document
from erpnext.manufacturing.doctype.work_order.work_order import stop_unstop

class Maintenance(Document):

	def validate(self):
		# Store the current value of workflow_state before any updates
		self.previous_workflow_state = frappe.db.get_value("Maintenance", self.name, "workflow_state")
	
	def on_update(self):
		# Check if workflow_state has changed
		if self.previous_workflow_state and self.previous_workflow_state != self.workflow_state:
			# Call the respective function based on the new workflow_state value
			if self.workflow_state == "CIP Inprogress":
				self.mark_cip_inprogress()
			elif self.workflow_state == "CIP Finished":
				self.mark_cip_finished()
		else:
			print("Hello")

	def mark_cip_inprogress(self):
		# Stop the work order if CIP document goes in progress
		if self.work_order_id:
			stop_unstop(self.work_order_id, "Stopped")

	def mark_cip_finished(self):
		# Resume the work order if CIP document is finished
		if self.work_order_id:
			stop_unstop(self.work_order_id, "Resumed")