# -*- coding: utf-8 -*-
# Copyright (c) 2023, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

from __future__ import unicode_literals
import frappe
from frappe import _, _dict
from frappe.model.document import Document
import json
from datetime import datetime,timedelta
#site confige import
from nrp_manufacturing.utils import  get_config_by_name
import ast

class Cashflowaccountdatacsd(Document):
	pass

@frappe.whitelist()
def insertDataQueue(from_date=None,to_date=None,companies=None):
	try:
		if not from_date:
			from_date = (datetime.now() - timedelta(days=1)).strftime('%Y-%m-%d')
		if not to_date:
			to_date = (datetime.now() - timedelta(days=1)).strftime('%Y-%m-%d')

		cashflow_config = get_config_by_name('CASH_FLOW_DATA_CONFIG_CSD')

		if companies:
			if not isinstance(companies, list):
				j_companies = json.loads(companies)
			else:
				j_companies = companies
		else:
			j_companies = cashflow_config.keys()

		companies_tuple = tuple(j_companies)

		query = """
			DELETE FROM `tabCashflow account data csd`
			WHERE `date` >= %(from_date)s
			AND `date` <= %(to_date)s
			AND company IN %(companies)s
		"""
		frappe.db.sql(query, {'from_date': from_date.strip(), 'to_date': to_date.strip(), 'companies': companies_tuple})
		frappe.db.commit()
		from_date = from_date.strip()  
		to_date = to_date.strip() 
		from_date = datetime.strptime(from_date, '%Y-%m-%d')
		to_date = datetime.strptime(to_date, '%Y-%m-%d')


	
		for company in companies_tuple:
			start_date = from_date
			end_date = to_date
			while start_date <= end_date:
				# insertData(from_date=start_date.strftime('%Y-%m-%d'), to_date=start_date.strftime('%Y-%m-%d'), company=company, cashflow_config=cashflow_config)
				frappe.db.commit()
				frappe.enqueue(
					"erpnext.accounts.doctype.cashflow_account_data_csd.cashflow_account_data_csd.insertData",
					from_date=start_date.strftime('%Y-%m-%d'), 
					to_date=start_date.strftime('%Y-%m-%d'), 
					company=company, 
					cashflow_config=cashflow_config,
					queue="sync",
					timeout=13000
				)
				frappe.db.commit()
				start_date += timedelta(days=1)
	except Exception as e:
		title = "CSD Cash Flow Data"
		traceback = frappe.get_traceback()
		frappe.log_error(message=traceback, title=title)

@frappe.whitelist()
def insertDataQueueAccountConfig(starting_date=None,ending_date=None,companies=None):
	try:
		condition = ""
		if not starting_date:
			starting_date = (datetime.now() - timedelta(days=1)).strftime('%Y-%m-%d')
		if not ending_date:
			ending_date = (datetime.now() - timedelta(days=1)).strftime('%Y-%m-%d')
		
		
			
		if companies:
			if not isinstance(companies, list):
				j_companies = json.loads(companies)
			else:
				j_companies = companies
			companies_tuple = ', '.join(frappe.db.escape(v) for v in j_companies)
			condition = f"AND company IN ({companies_tuple})"
		else:
			condition = ""
		#CONCAT('(', GROUP_CONCAT(CONCAT("'", NAME, "'") SEPARATOR ','), ')') AS account_names
		cashflow_config = frappe.db.sql(f"""SELECT 
			company,
			cash_flow_head,
			cash_flow_title
		FROM 
			`tabAccount`
		WHERE 
			cash_flow_head IS NOT NULL 
			AND cash_flow_title IS NOT NULL {condition}
		GROUP BY  
			company, cash_flow_head, cash_flow_title 
			ORDER BY CASE cash_flow_head
			WHEN 'NET PROFIT/(LOSS)' THEN 1
			WHEN 'Un appropriated Profit/(Loss) Adjustment' THEN 2
			WHEN 'DEPLETION RESERVES' THEN 3
			WHEN 'GAIN/LOSS ON SALE OF ASSETS' THEN 4
			WHEN 'ADD BACK DEPRICIATION FOR THE PERIOD' THEN 5
			WHEN 'TRADEABLE STOCKS' THEN 6
			WHEN 'STORES & SPARES' THEN 7
			WHEN 'SHOP VALUE' THEN 8
			WHEN 'TRADE RECEIVABLES' THEN 9
			WHEN 'INTER UNIT RECEIVABLE' THEN 10
			WHEN 'DEPOSITS AND PREPAYMENTS' THEN 11
			WHEN 'LOAN & ADVANCES' THEN 12
			WHEN 'OTHER CURRENT ASSETS' THEN 13
			WHEN 'TRADE PAYABLES' THEN 14
			WHEN 'INTER UNIT PAYABLE' THEN 15
			WHEN 'ACCRUED LIABILITIES' THEN 16
			WHEN 'PROVISIONAL LIABILITIES' THEN 17
			WHEN 'TAXES PAYABLE' THEN 18
			WHEN 'OTHER CURRENT LIABILITIES' THEN 19
			WHEN 'CAPEX' THEN 20
			WHEN 'LONG TERM INVESTMENT' THEN 21
			WHEN 'LONG TERM SECURITY DEPOSITS' THEN 22
			WHEN 'LONG TERM LOAN RECEIVABLES' THEN 23
			WHEN 'SHARE CAPITAL' THEN 24
			WHEN 'DRAWINGS' THEN 25
			WHEN 'ACCRUED FINANCE COST' THEN 26
			WHEN 'LONG/SHORT TERM LOANS' THEN 27
			WHEN 'RUNNING FINANCE' THEN 28
			WHEN 'LOAN FROM DIRECTORS' THEN 29
			WHEN 'INSTALLMENTS LEASE' THEN 30
			WHEN 'RESERVES & RETAIN EARNINGS' THEN 31
			WHEN 'OTHERS' THEN 32
			WHEN 'OPENING CASH AND BANK BALANCE' THEN 33
			ELSE 999
			END,
			cash_flow_title ASC;""", as_dict=True)

		query = f"""
			DELETE FROM `tabCashflow account data csd`
			WHERE `date` >= {frappe.db.escape(starting_date.strip())}
			AND `date` <= {frappe.db.escape(ending_date.strip())}
			{condition}
			"""
		frappe.db.sql(query)
		frappe.db.commit()

	
		for cfc in cashflow_config:
			
			from_date = starting_date.strip()  
			to_date = ending_date.strip() 
			from_date = datetime.strptime(from_date, '%Y-%m-%d')
			to_date = datetime.strptime(to_date, '%Y-%m-%d')
			start_date = from_date
			end_date = to_date
			while start_date <= end_date:
				# insertData(from_date=start_date.strftime('%Y-%m-%d'), to_date=start_date.strftime('%Y-%m-%d'), company=company, cashflow_config=cashflow_config)
				frappe.db.commit()
				# insertDataAccountConfig(from_date=start_date.strftime('%Y-%m-%d'), 
				# 	to_date=start_date.strftime('%Y-%m-%d'), 
				# 	company=cfc.company, 
				# 	cash_flow_head=cfc.cash_flow_head,
				# 	cash_flow_title=cfc.cash_flow_title)
				frappe.enqueue(
					"erpnext.accounts.doctype.cashflow_account_data_csd.cashflow_account_data_csd.insertDataAccountConfig",
					from_date=start_date.strftime('%Y-%m-%d'), 
					to_date=start_date.strftime('%Y-%m-%d'), 
					company=cfc.company, 
					cash_flow_head=cfc.cash_flow_head,
					cash_flow_title=cfc.cash_flow_title,
					queue="sync",
					timeout=13000
				)
				frappe.db.commit()
				start_date += timedelta(days=1)
	except Exception as e:
		title = "CSD Cash Flow Data"
		traceback = frappe.get_traceback()
		frappe.log_error(message=traceback, title=title)


@frappe.whitelist()
def insertData(from_date,to_date, company, cashflow_config):
	from erpnext.accounts.report.general_ledger.general_ledger import get_data_with_opening_closing, get_gl_entries, initialize_gle_map,get_accountwise_gle

	from datetime import datetime, timedelta
	from_date = datetime.strptime(from_date, "%Y-%m-%d").date()	
	to_date = datetime.strptime(to_date, "%Y-%m-%d").date()	
	current_date = from_date
	account_head_total = {}
	

	while current_date <= to_date:
		company_account = cashflow_config.get(company)
		for a in company_account:
			head = a.get('head')
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
def insertDataAccountConfig(from_date, to_date, company, cash_flow_head, cash_flow_title):
	try:
		from erpnext.accounts.report.general_ledger.general_ledger import get_data_with_opening_closing, get_gl_entries, initialize_gle_map,get_accountwise_gle

		from datetime import datetime, timedelta
		from_date = datetime.strptime(from_date, "%Y-%m-%d").date()	
		to_date = datetime.strptime(to_date, "%Y-%m-%d").date()	
		current_date = from_date
		account_total = 0
		account_closing = 0
		account_opening = 0
		if company:
       
			if isinstance(company, list):
				j_companies = company
			else:
				try:
					parsed = json.loads(company)
					if isinstance(parsed, list):
						j_companies = parsed
					else:
						
						j_companies = [parsed]
				except json.JSONDecodeError:
					j_companies = [company]

			companies_tuple = ', '.join(frappe.db.escape(v) for v in j_companies)
			condition = f"AND company IN ({companies_tuple})"
		else:
			condition = ""

		account_names  = frappe.db.sql(f"""SELECT company,cash_flow_head,cash_flow_title,NAME AS account_names
		FROM 
			`tabAccount`
		WHERE 
			cash_flow_head="{cash_flow_head}"
			AND cash_flow_title="{cash_flow_title}" {condition}
		 order by account_number ASC""",as_dict=True)
		while current_date <= to_date:
			for acc in account_names:
				data = frappe.db.sql(
						f""" SELECT 
								(SELECT SUM(debit)-SUM(credit) FROM `tabGL Entry` 
								WHERE ACCOUNT = "{acc.account_names}" AND company = '{company}' AND posting_date < '{current_date}') AS opening,
								(SELECT SUM(debit)-SUM(credit) FROM `tabGL Entry` 
								WHERE voucher_type!='Period Closing Voucher' and ACCOUNT = "{acc.account_names}" AND company = '{company}' AND posting_date = '{current_date}') AS value """
								,as_dict=True,debug=1
					)
				if data:
					opening_balance = data[0].opening if data[0].opening != None else 0
					value = data[0].value if data[0].value != None else 0
					closing_balance = opening_balance + value
					#save doc
					if opening_balance!=0 and closing_balance!=0:
						save_doc = {
							'doctype':'Cashflow account data csd',
							'head':cash_flow_head,
							'company':company,
							'account': str(acc.account_names),
							'date':current_date,
							'opening': opening_balance,
							'closing' : closing_balance,
							'value' : value
						}
						frappe.get_doc(save_doc).save(ignore_permissions=True)
						account_total += value
						account_opening += opening_balance
						account_closing += closing_balance
						if cash_flow_title == 'GAIN/LOSS ON SALE OF ASSETS':
							account_total = account_total * -1
				

			#save doc
			save_doc = {
				'doctype':'Cashflow account data csd',
				'head':cash_flow_head,
				'company':company,
				'account': str(cash_flow_title),
				'date':current_date,
				'opening': account_opening,
				'closing' : account_closing,
				'value' : account_total
			}
			frappe.get_doc(save_doc).save(ignore_permissions=True)
			frappe.db.commit()
			current_date += timedelta(days=1)
	except Exception as e:
		print(e)

@frappe.whitelist()
def updateCashBankData():
	data = frappe.db.sql("SELECT head,date,account,sum(opening) as opening,sum(closing) as closing,value FROM `tabCashflow account data csd` WHERE  head like 'BANKS' GROUP BY DATE", as_dict=True)
	for d in data:
		sql = f"""update `tabCashflow account data csd` set opening = {d.opening}, closing = {d.closing} where account = 'BANKS' and date = '{d.date}'"""
		frappe.db.sql(sql)
		print(d)	



# Code by Moeiz
# Cron job for daily update of cashflow data
@frappe.whitelist()
def csd_cashflow_data_job():
	frappe.enqueue("erpnext.accounts.doctype.cashflow_account_data_csd.cashflow_account_data_csd.insertDataQueueAccountConfig", queue="sync")
	frappe.db.commit()