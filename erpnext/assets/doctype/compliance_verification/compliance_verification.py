# -*- coding: utf-8 -*-
# Copyright (c) 2025, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

from __future__ import unicode_literals
import frappe
import json
from frappe.model.document import Document

class ComplianceVerification(Document):
	@frappe.whitelist()
	def fetch_data(self):
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

	def on_submit(self):
		# Validate ranking for each parameter
		self.validate_ranking()
		
		parameter = frappe.get_doc("Parameter Setup", self.parameter_setup)
		total_score = 0
		final_rank = ""

		# Set Score for each parameter and calculate total score
		for cvi in self.compliance_verification_item:
			for pd in parameter.parameter_setup_details:
				if pd.parameter == cvi.parameter and pd.ranking == cvi.ranking:
					cvi.score = pd.score
					total_score += pd.score
					cvi.db_update()
					break
		
		# Getting Scoring Criteria
		grade_range = "<b>Scoring Criteria:</b>"
		ranking = frappe.get_doc("Ranking Setup", self.ranking)
		if len(ranking.ranking_setup_item) > 0:
			for rsi in ranking.ranking_setup_item:
				if total_score >= rsi.range_slab_start and total_score <= rsi.range_slab_end:
					final_rank = rsi.ranking
				grade_range = f"{grade_range} {rsi.range_slab_start} - {rsi.range_slab_end} <b>{rsi.ranking}</b>"

		self.score_criteria = grade_range
		self.rank = final_rank
		self.total_score = total_score
		self.db_update()
	
	def validate_ranking(self):
		if not len(self.compliance_verification_item):
			frappe.throw(f"Please fetch data from '{self.parameter_setup}'.")
		for cvi in self.compliance_verification_item:
			if not cvi.ranking:
				frappe.throw(f"Please select ranking for '{cvi.parameter}'.")


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
