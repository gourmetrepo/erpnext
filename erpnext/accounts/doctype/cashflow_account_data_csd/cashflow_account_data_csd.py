# -*- coding: utf-8 -*-
# Copyright (c) 2023, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

from __future__ import unicode_literals
import frappe
from frappe import _, _dict
from frappe.model.document import Document

class Cashflowaccountdatacsd(Document):
	pass


@frappe.whitelist()
def insertData(from_date,to_date,head=''):
	from erpnext.accounts.report.general_ledger.general_ledger import get_data_with_opening_closing, get_gl_entries
	from nrp_manufacturing.utils import get_config_by_name
	cashflow_config = get_config_by_name('CASH_FLOW_DATA_CONFIG_CSD')
	
	from datetime import datetime, timedelta
	from_date = datetime.strptime(from_date, "%Y-%m-%d").date()	
	to_date = datetime.strptime(to_date, "%Y-%m-%d").date()	
	current_date = from_date
	while current_date <= to_date:
		for company, company_account in cashflow_config.items():
			for a in company_account:
				head = a.get('head')
				for b in a.get('accounts'):
					account_title = b.get('title')
					account_totel = 0
					for account in b.get('account'):
						filters = _dict()
						filters['group_by'] = _("Group by Voucher")
						filters['include_default_book_entries'] = True
						filters['company'] = company
						filters['account'] = account
						filters['from_date'] = current_date
						filters['to_date'] = current_date
						gl_entries = get_gl_entries(filters)
						account_details = ''
						data = get_data_with_opening_closing(filters, account_details, gl_entries)
						for d in data:
							if d:
								if d.get('account') == "'Opening'":
									opening_balance = d.debit - d.credit
								elif d.get('account') == "'Closing (Opening + Total)'":
									closing_balance = d.debit - d.credit
						value = opening_balance - closing_balance
						#save doc
						save_doc = {
							'doctype':'Cashflow account data csd',
							'head':head,
							'company':company,
							'account': str(account),
							'date':current_date,
							'opening': opening_balance,
							'closing' : closing_balance,
							'value' : value
						}
						frappe.get_doc(save_doc).save(ignore_permissions=True)
						account_totel += value
					#save doc
					save_doc = {
						'doctype':'Cashflow account data csd',
						'head':head,
						'company':company,
						'account': str(account_title),
						'date':current_date,
						'opening': opening_balance,
						'closing' : closing_balance,
						'value' : value
					}
					frappe.get_doc(save_doc).save(ignore_permissions=True)
		current_date += timedelta(days=1)
