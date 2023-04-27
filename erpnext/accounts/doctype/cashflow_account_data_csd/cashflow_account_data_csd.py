# -*- coding: utf-8 -*-
# Copyright (c) 2023, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

from __future__ import unicode_literals
import frappe
from frappe import _, _dict
from frappe.model.document import Document
import json
class Cashflowaccountdatacsd(Document):
	pass


@frappe.whitelist()
def insertData(from_date,to_date,heads,companies):
	from erpnext.accounts.report.general_ledger.general_ledger import get_data_with_opening_closing, get_gl_entries
	from nrp_manufacturing.utils import get_config_by_name
	cashflow_config = get_config_by_name('CASH_FLOW_DATA_CONFIG_CSD')
	
	from datetime import datetime, timedelta
	from_date = datetime.strptime(from_date, "%Y-%m-%d").date()	
	to_date = datetime.strptime(to_date, "%Y-%m-%d").date()	
	current_date = from_date
	account_head_total = {}
	companies = json.loads(companies)
	while current_date <= to_date:
		for company, company_account in cashflow_config.items():
			if company in companies:
				for a in company_account:
					head = a.get('head')
					if head in heads:
						for b in a.get('accounts'):
							account_title = b.get('title')
							account_total = 0
							account_opening = 0
							account_closing = 0
							for account in b.get('account'):
								print(account)
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
								# if account_title == "6.01.01.001 - Un appropriated Profit/(Loss)":
								# 	opening_balance += account_head_total['404 - Income'].get('opening')
								# 	closing_balance += account_head_total['404 - Income'].get('closing')
								# 	opening_balance += account_head_total['505 - Expenses'].get('opening')
								# 	closing_balance += account_head_total['505 - Expenses'].get('closing')

								# 	value = opening_balance - closing_balance
								# 	value = value - account_head_total['404 - Income'].get('value')
								# 	value = value - account_head_total['505 - Expenses'].get('value')

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
								account_total += value
								account_opening += opening_balance
								account_closing += closing_balance
							if account_title == 'GAIN/LOSS ON SALE OF ASSETS':
								account_total = account_total * -1
							
							# account_head_total[account_title] = {'opening' : account_opening,'closing' : account_closing,'value' : account_total}

							#save doc
							save_doc = {
								'doctype':'Cashflow account data csd',
								'head':head,
								'company':company,
								'account': str(account_title),
								'date':current_date,
								'opening': account_opening,
								'closing' : account_closing,
								'value' : account_total
							}
							frappe.get_doc(save_doc).save(ignore_permissions=True)
						frappe.db.commit()
		current_date += timedelta(days=1)


@frappe.whitelist()
def updateCashBankData():
	data = frappe.db.sql("SELECT head,date,account,sum(opening) as opening,sum(closing) as closing,value FROM `tabCashflow account data csd` WHERE  head like 'BANKS' GROUP BY DATE", as_dict=True)
	for d in data:
		sql = f"""update `tabCashflow account data csd` set opening = {d.opening}, closing = {d.closing} where account = 'BANKS' and date = '{d.date}'"""
		frappe.db.sql(sql)
		print(d)	