# -*- coding: utf-8 -*-
# Copyright (c) 2023, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

from __future__ import unicode_literals
import frappe
from frappe.model.document import Document
from frappe.utils import (today, add_days)
import ast
#site confige import
from nrp_manufacturing.utils import  get_config_by_name,get_post_params
class AccountSegmentData(Document):
	pass

@frappe.whitelist()
def calculate_segment_profit():
	bgroup = ['CSD (Carbonated Soft Drinks)','Concentrate','Confectionery','Water','Juice','19 Ltr','Other']
	form_body = get_post_params()
	if form_body.get('date'):
		date_yesterday = form_body.get('date')
	else:
		date_yesterday = add_days(today(), -1)

	units = get_config_by_name("segment_wise_profit_csd", {})
	b_group_data = []
	for single_unit in units:
		sale_bgroup = get_unit_sales_bgroup(single_unit,date_yesterday)
		count = 0
		totalsales = 0
		for index,bg in enumerate(bgroup):			
			if bg not in str(sale_bgroup):
				b_group_data.append({"business_group":bg,'amount':1})
			else:
				print(sale_bgroup[count].get('amount'))
				b_group_data.append(sale_bgroup[count])
				totalsales = totalsales + sale_bgroup[count].get('amount')
				count = count + 1
		
		if b_group_data:
			for total_sale in b_group_data:
				totalsales = totalsales + total_sale.get('amount')
		for coa in units[single_unit].get('segment'):
			acc_data=units[single_unit].get('segment').get(coa)
   
			# account =re.sub('"', '',acc_data[0]['accounts'])
			if  acc_data.get('accounts') != "":		
				# account  = ast.literal_eval(acc_data.get('accounts'))
				account = acc_data.get('accounts')
			else:
				account = ""
			head = acc_data.get('head')
			formula =acc_data.get('formula')
			data =get_segment_gl_data(coa,account,head,formula,date_yesterday,single_unit,b_group_data,totalsales)
		




def get_unit_sales_bgroup(unit,date):
	return frappe.db.sql("""
	select business_group,sum(amount) as amount from `tabSales Invoice Item` as A
	INNER JOIN `tabItem CSD` as B ON A.`item_code` = B.item_code
	INNER JOIN `tabSales Invoice` AS C ON C.name = A.parent
	 where 
	DATE(A.`creation`) between '{0}' AND '{0}' AND C.company = '{1}' AND
	`business_group` IN ('CSD (Carbonated Soft Drinks)','Concentrate','Confectionery','Water','Juice','19 Ltr','Other')
	group by `business_group`
	""".format(date,unit),as_dict=True, debug = 1)
	
def get_segment_gl_data(account_title,account,head,formula,date,unit,sale_bgroup,totalsales):		
		condition = ''
		Amount =0
		if account != None and account != "":	
		# if type(account) == str:
		# 		condition = (f"""('{account}')""")
		# else:
		# 		condition = (f"""{account}""")
			data = frappe.db.sql("""
				SELECT SUM(`credit_in_account_currency`-`debit_in_account_currency`) AS account_value 
				FROM `tabGL Entry` WHERE account in ({0})  AND company='{2}' 
				AND DATE(creation) BETWEEN '{1}' AND '{1}'
				""".format(account,date,unit),as_dict=True ,debug =1)
			for bgroup_data in sale_bgroup:
				try:
					if data:
						# if data[0].account_value != None:
						# 	Amount = data[0].account_value
						if data[0].account_value != None :
							Amount =   (bgroup_data.get('amount')/totalsales) * data[0].account_value  
						else:
							Amount = 0
					else:
						Amount = 0
				except Exception as e:
					print(e)
					Amount = 0
				save_doc = {
					'doctype':'Account Segment Data',
					'segment':bgroup_data.get('business_group'),
					'account':account_title.title(),
					'coa': str(account),
					'company':unit,
					'head':head.title(),
					'date':date,
					'account_value':Amount
				}
				frappe.get_doc(save_doc).save(ignore_permissions=True)
				frappe.db.commit()