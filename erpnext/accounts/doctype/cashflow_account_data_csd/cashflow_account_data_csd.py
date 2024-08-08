# -*- coding: utf-8 -*-
# Copyright (c) 2023, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

from __future__ import unicode_literals
import frappe
from frappe import _, _dict
from frappe.model.document import Document
import json
from datetime import datetime
class Cashflowaccountdatacsd(Document):
	pass

@frappe.whitelist()
def insertDataQueue(from_date,to_date,heads,companies):
	if not from_date:
		from_date = datetime.now().strftime('%Y-%m-%d')
	if not to_date:
		to_date = datetime.now().strftime('%Y-%m-%d')
		
	j_companies = json.loads(companies)
	companies_tuple = tuple(j_companies)
	frappe.db.sql(f"""DELETE FROM `tabCashflow account data csd` WHERE `date`>='{from_date}' AND `date`<='{to_date}' and company IN ({companies_tuple})""")
	frappe.db.commit()	
	while from_date <= to_date:
		frappe.enqueue(
			"erpnext.accounts.doctype.cashflow_account_data_csd.cashflow_account_data_csd.insertData",
			from_date=from_date.strftime('%Y-%m-%d'),
			to_date=from_date.strftime('%Y-%m-%d'),
			heads=heads,
			companies=companies,
			queue="long",
			timeout=13000,
			enqueue_after_commit=True
		)
		from_date += timedelta(days=1)

@frappe.whitelist()
def insertData(from_date,to_date,heads,companies):
	from erpnext.accounts.report.general_ledger.general_ledger import get_data_with_opening_closing, get_gl_entries, initialize_gle_map,get_accountwise_gle
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
								data = frappe.db.sql(
									f""" SELECT 
											(SELECT SUM(debit)-SUM(credit) FROM `tabGL Entry` 
											WHERE ACCOUNT = "{account}" AND company = '{company}' AND posting_date < '{current_date}') AS opening,
											(SELECT SUM(debit)-SUM(credit) FROM `tabGL Entry` 
											WHERE voucher_type!='Period Closing Voucher' and ACCOUNT = "{account}" AND company = '{company}' AND posting_date = '{current_date}') AS value """
											,as_dict=True
								)
								if data:
									opening_balance = data[0].opening if data[0].opening != None else 0
									value = data[0].value if data[0].value != None else 0
									closing_balance = opening_balance + value
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