# Copyright (c) 2015, Frappe Technologies Pvt. Ltd. and Contributors
# License: GNU General Public License v3. See license.txt

from __future__ import unicode_literals
import frappe
import frappe.defaults
import json
import requests
from frappe import msgprint, _
from frappe.model.naming import set_name_by_naming_series
from frappe.contacts.address_and_contact import load_address_and_contact, delete_contact_and_address
from erpnext.utilities.transaction_base import TransactionBase
from erpnext.accounts.party import validate_party_accounts, get_dashboard_info, get_timeline_data # keep this
from nrp_manufacturing.utils import get_config_by_name, json_error_response
from nrp_manufacturing.constants.globals import PERMISSION_ERROR_MSG, ERROR_MSG
from frappe.exceptions import ValidationError


class Supplier(TransactionBase):
	def get_feed(self):
		return self.supplier_name

	def onload(self):
		"""Load address and contacts in `__onload`"""
		load_address_and_contact(self)
		self.load_dashboard_info()

	def before_save(self):
		if not self.on_hold:
			self.hold_type = ''
			self.release_date = ''
		elif self.on_hold and not self.hold_type:
			self.hold_type = 'All'

		# Supplier Sync with third party API
		try:
			from datetime import datetime
			baseurl = get_config_by_name("THIRD_PARTY_SUPPLIER_APP")
			if baseurl:
				url = baseurl + 'PostSuppliers'

				address_data = frappe.db.sql(f"""SELECT address_line1, phone, city FROM `tabAddress` WHERE address_title='{self.name}';""", as_dict=True)
				address=""
				phone=""
				city=""

				if len(address_data) > 0:
					if address_data[0].address_line1:
						address=address_data[0].address_line1
					if address_data[0].phone:
						phone=address_data[0].phone
					if address_data[0].city:
						city=address_data[0].city

				payload = [{
						"supplierName": self.supplier_name if self.supplier_name else '',
						"supplierCode": self.name if self.name else '',
						"address": address,
						"phone": phone,
						"city": city,
						"company": "",
						"supplierGroup": self.supplier_group if self.supplier_group else '',
						"supplierType": self.supplier_type if self.supplier_type else ''
					}]

				# Maintain logs
				nrp_integeration = {
					"ref_doctype": "Supplier",
					"doctype": "Nrp Integration",
					"request": str(payload)
				}

				nrp_integeration["title"] = "Supplier Sync with GSSM " + str(datetime.now())
				nrp_logs = frappe.get_doc(nrp_integeration)
				nrp_logs.save(ignore_permissions=True)
				response_gssm = []

				data = json.dumps(payload, default=str)
				headers = {'Content-Type': 'application/json'}
				response = requests.request("POST", url , headers=headers, data=data)
				response_gssm.append(response.text)
				
				# Maintain logs
				frappe.db.set_value('Nrp Integration', nrp_logs.name, 'response', str(response_gssm))
		except ValidationError as error:
			return json_error_response(str(error))
		except frappe.PermissionError as error:
			return json_error_response(PERMISSION_ERROR_MSG)
		except Exception as error:
			traceback = frappe.get_traceback()
			frappe.log_error(message=traceback, title="Error While Supplier Sync with GSSM.")
			return json_error_response(ERROR_MSG)


	def load_dashboard_info(self):
		info = get_dashboard_info(self.doctype, self.name)
		self.set_onload('dashboard_info', info)

	def autoname(self):
		supp_master_name = frappe.defaults.get_global_default('supp_master_name')
		if supp_master_name == 'Supplier Name':
			self.name = self.supplier_name
		else:
			set_name_by_naming_series(self)

	def on_update(self):
		if not self.naming_series:
			self.naming_series = ''

	def validate(self):
		# validation for Naming Series mandatory field...
		if frappe.defaults.get_global_default('supp_master_name') == 'Naming Series':
			if not self.naming_series:
				msgprint(_("Series is mandatory"), raise_exception=1)

		validate_party_accounts(self)

	def on_trash(self):
		delete_contact_and_address('Supplier', self.name)

	def after_rename(self, olddn, newdn, merge=False):
		if frappe.defaults.get_global_default('supp_master_name') == 'Supplier Name':
			frappe.db.set(self, "supplier_name", newdn)
