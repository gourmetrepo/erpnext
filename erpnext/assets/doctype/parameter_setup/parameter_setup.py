# -*- coding: utf-8 -*-
# Copyright (c) 2025, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

from __future__ import unicode_literals
import frappe
from frappe.model.document import Document

class ParameterSetup(Document):
	def before_save(self):
		self.validate_weight()
		self.get_parameter_details()

	def validate_weight(self):
		total_weight = 0.0
		for psi in self.parameter_setup_item:
			total_weight += psi.weight
		if total_weight > 100:
			frappe.throw("Total weight cannot be more than 100%")
		elif total_weight < 0:
			frappe.throw("Total weight cannot be less than 0%")
		elif total_weight < 100:
			frappe.throw("Total weight must be 100%")

	def get_parameter_details(self):
		ranking_setup = {}
		# Remove existing data in Parameter Setup Details
		if len(self.parameter_setup_details) > 0:
			self.parameter_setup_details = []
			
		for psi in self.parameter_setup_item:
			if not ranking_setup.get(psi.rank_type, ""):
				rsi_data = frappe.db.sql(f"""SELECT ranking, rank_split_percentage FROM `tabRanking Setup Item` WHERE parent='{psi.rank_type}';""", as_dict=True)
				rsi_dict = {rsid.get('ranking', ''): rsid.get('rank_split_percentage', '') for rsid in rsi_data}
				ranking_setup[psi.rank_type] = rsi_dict
			
			ranks = ranking_setup.get(psi.rank_type, "")
			for key, val in ranks.items():
				rsd = frappe.new_doc('Parameter Setup Details')
				rsd.parameter = psi.parameter
				rsd.ranking = key
				rsd.rank_value = val
				rsd.score = (psi.weight/100.0) * val
				self.append('parameter_setup_details', rsd)
