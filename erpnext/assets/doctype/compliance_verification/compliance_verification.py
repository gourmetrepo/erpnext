# -*- coding: utf-8 -*-
# Copyright (c) 2025, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

from __future__ import unicode_literals
import frappe
import json
from frappe.model.document import Document

class ComplianceVerification(Document):
	def before_save(self):
		self.get_parameter_setup()

	def get_parameter_setup(self):
		# Remove existing data in Parameter Setup Details
		if len(self.compliance_verification_item) > 0:
			self.compliance_verification_item = []

		parameter_setup = frappe.get_doc("Parameter Setup", self.parameter_setup)
		if len(parameter_setup.parameter_setup_item) > 0:
			for psi in parameter_setup.parameter_setup_item:
				cvi = frappe.new_doc('Compliance Verification Item')
				cvi.parameter = psi.parameter
				cvi.rank_type = psi.rank_type
				self.append('compliance_verification_item', cvi)


@frappe.whitelist()
def get_rank_options(compliance_verification_items):
	parameter_options = {}
	cv_items = json.loads(compliance_verification_items)

	for cvi in cv_items:
		options = []
		rank_data = frappe.get_doc("Ranking Setup", cvi.get("rank_type", ""))
		if len(rank_data.ranking_setup_item) > 0:
			for rdi in rank_data.ranking_setup_item:
				options.append(rdi.ranking)
		parameter_options[cvi.get("parameter", "")] = options
	return parameter_options
