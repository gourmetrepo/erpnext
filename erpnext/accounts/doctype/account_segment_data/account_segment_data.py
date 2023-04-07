# -*- coding: utf-8 -*-
# Copyright (c) 2023, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

from __future__ import unicode_literals
import frappe
from frappe.model.document import Document
from frappe.utils import (today, add_days)
import ast
import json
from datetime import datetime, timedelta
#site confige import
from nrp_manufacturing.utils import  get_config_by_name,get_post_params
class AccountSegmentData(Document):
	pass
@frappe.whitelist()
def calculate_segmented_profit_date_range():
		form_body = get_post_params()
		if form_body.get('start_date'):
			start_date = datetime.strptime(form_body.get('start_date'), "%Y-%m-%d")

		for i in range(0, 32):  # loop through 1 to 15 days
			date = start_date + timedelta(days=i)
			calculate_segment_profit(date)
			print(date.strftime('%Y-%m-%d'))
   
   
@frappe.whitelist()
def calculate_segment_profit(f_date=''):
		sumdiv=0.0
		sumtotal=0.0
		Shopdiscountinvoices=0.0
		DistributorRevenue={"Confectionery":0,"Concentrate":0,"Juice":0,"csd":0,"nineteenLtr":0,"Water":0,"other":0}
		ShopRevenue={"Confectionery":0,"Concentrate":0,"Juice":0,"csd":0,"nineteenLtr":0,"Water":0,"other":0}
		InterunitRevenue={"Confectionery":0,"Concentrate":0,"Juice":0,"csd":0,"nineteenLtr":0,"Water":0,"other":0}
		bgroup = ['19 Ltr','Concentrate','Confectionery','CSD (Carbonated Soft Drinks)','Juice','Other','Water']

		if(f_date!=''):
			date_yesterday = f_date
		
		else:
			date_yesterday = add_days(today(), -1)

		units = get_config_by_name("segment_wise_profit_csd", {})
		b_group_data = []
		for single_unit in units:
			count = 0
			totalsales = 0		
			for coa in units[single_unit].get('segment'):
				print(coa.title())
				acc_data=units[single_unit].get('segment').get(coa)
				if  acc_data.get('accounts') != "":		
					account = acc_data.get('accounts')
				else:
					account = ""
				head = acc_data.get('head')
				formula =acc_data.get('formula')
				Amount =0
				if account != None and account != "":

						if formula.title()=='true'.title():
							if(coa.title()=='Distributors Incentive' or coa.title()=='Leakge & Bursting' or coa.title()=='Vsp Mark Up'or coa.title()=='Sales Promotions'):
										sumtotal= 0.00
										sumdiv= 0.00
										data = frappe.db.sql("""
												SELECT IFNULL(SUM(`credit_in_account_currency`-`debit_in_account_currency`),0.000) AS account_value 
												FROM `tabGL Entry` WHERE account in ({0})  AND company='{2}' 
												AND DATE(posting_date) BETWEEN '{1}' AND '{1}'
												""".format(account,date_yesterday,single_unit),as_dict=True )
										sumtotal =	DistributorRevenue.get('csd')+DistributorRevenue.get('Juice')+DistributorRevenue.get('Water')+DistributorRevenue.get('nineteenLtr')+DistributorRevenue.get('Confectionery')
										for index,bgroup_data in enumerate(bgroup):
													if(bgroup_data=='Concentrate'):
														Amount =  0.00
													elif(bgroup_data=='CSD (Carbonated Soft Drinks)'):
														sumdiv= DistributorRevenue.get('csd')
														Amount =   (sumdiv/sumtotal) * data[0].account_value  
													elif(bgroup_data=='Juice'):
														sumdiv=DistributorRevenue.get('Juice')
														Amount =   (sumdiv/sumtotal) * data[0].account_value 
													elif(bgroup_data=='Other'):
														Amount =0.000
													elif(bgroup_data=='19 Ltr'):
														sumdiv=DistributorRevenue.get('nineteenLtr')
														Amount =   (sumdiv/sumtotal) * data[0].account_value 
													elif(bgroup_data=='Water'):
														sumdiv=DistributorRevenue.get('Water')
														Amount =   (sumdiv/sumtotal) * data[0].account_value 
														
													elif(bgroup_data=='Confectionery'):
														sumdiv=DistributorRevenue.get('Confectionery')
														Amount =   (sumdiv/sumtotal) * data[0].account_value 
														
													save_doc = {
															'doctype':'Account Segment Data',
															'segment':bgroup_data,
															'account':coa.title(),
															'coa': str(account),
															'company':single_unit,
															'head':head.title(),
															'date':date_yesterday,
															'account_value':float(Amount)
														}
													frappe.get_doc(save_doc).save(ignore_permissions=True)	
							elif(coa.title()=='Sales Tax & Fed' or coa.title()=='Federal Excise Duty'):
									sumtotal= 0.00
									sumdiv= 0.00
									data = frappe.db.sql("""
												SELECT IFNULL(SUM(`credit_in_account_currency`-`debit_in_account_currency`),0.000) AS account_value 
												FROM `tabGL Entry` WHERE account in ({0})  AND company='{2}' 
												AND DATE(posting_date) BETWEEN '{1}' AND '{1}'
												""".format(account,date_yesterday,single_unit),as_dict=True )
									sumtotal = DistributorRevenue.get('csd')+DistributorRevenue.get('Juice')+DistributorRevenue.get('Water')+DistributorRevenue.get('nineteenLtr')+DistributorRevenue.get('Confectionery')+DistributorRevenue.get('Concentrate')+ShopRevenue.get('csd')+ShopRevenue.get('Juice')+ShopRevenue.get('Water')+ShopRevenue.get('nineteenLtr')+ShopRevenue.get('Confectionery')+ShopRevenue.get('Concentrate')
									print(sumtotal)	
									for index,bgroup_data in enumerate(bgroup):
											if(bgroup_data=='Concentrate'):
												sumdiv= ShopRevenue.get('Concentrate')+DistributorRevenue.get('Concentrate')
												Amount =   ((sumdiv/sumtotal) * data[0].account_value) 
											elif(bgroup_data=='CSD (Carbonated Soft Drinks)'):
												sumdiv= ShopRevenue.get('csd')+DistributorRevenue.get('csd')
												Amount =   ((sumdiv/sumtotal) * data[0].account_value)  
											elif(bgroup_data=='Juice'):
												sumdiv= ShopRevenue.get('Juice')+DistributorRevenue.get('Juice')
												Amount =   ((sumdiv/sumtotal) * data[0].account_value)  
											elif(bgroup_data=='Other'):
												Amount =0.000
											elif(bgroup_data=='19 Ltr'):
												sumdiv= ShopRevenue.get('nineteenLtr')+DistributorRevenue.get('nineteenLtr')
												Amount =   ((sumdiv/sumtotal) * data[0].account_value)  
											elif(bgroup_data=='Water'):
												sumdiv= ShopRevenue.get('Water')+DistributorRevenue.get('Water')
												Amount =   ((sumdiv/sumtotal) * data[0].account_value)  
											elif(bgroup_data=='Confectionery'):
												sumdiv= ShopRevenue.get('Confectionery')+DistributorRevenue.get('Confectionery')
												Amount =   ((sumdiv/sumtotal) * data[0].account_value)  
												
											print(sumdiv)
											save_doc = {
											'doctype':'Account Segment Data',
											'segment':bgroup_data,
											'account':coa.title(),
											'coa': str(account),
											'company':single_unit,
											'head':head.title(),
											'date':date_yesterday,
											'account_value':float(Amount)
											}
											frappe.get_doc(save_doc).save(ignore_permissions=True)	
							elif(coa.title()=='Direct Cost' or coa.title()=='Electricity Cost-Factory' or coa.title()=='Boiler_Fuel' or coa.title()=='Water Bill' or coa.title()=='Salaries And Wages-Direct' or coa.title()=='Repair & Maintenance' or coa.title()=='Mess Expenses' or coa.title() == 'Vehicle Running Expenses' or coa.title()=='Other Cost Of Goods Sold' or coa.title()=='Salaries Wages And Benefits' or coa.title()=='Charity And Donations' or coa.title()=='Lunger' or coa.title()=='Legal Expenses' or coa.title()=='Fuel Expenses' or coa.title()=='Research And Development Expenses' or coa.title()=='Reapir And Maintenance Admin' or coa.title()=='Insurance Expenses' or coa.title()=='Other Admin Expenses' or coa.title()=='Mark Up On Short Term Borrowing' or coa.title()=='Mark Up Leasing' or coa.title()=='Bank Charges' or coa.title()=='Taxation Expense'):
									sumdiv=0.0
									sumtotal=0.0
									data = frappe.db.sql("""
												SELECT IFNULL(SUM(`credit_in_account_currency`-`debit_in_account_currency`),0.000) AS account_value 
												FROM `tabGL Entry` WHERE account in ({0})  AND company='{2}' 
												AND DATE(posting_date) BETWEEN '{1}' AND '{1}'
												""".format(account,date_yesterday,single_unit),as_dict=True ,debug=True)
									sumtotal = DistributorRevenue.get('csd')+DistributorRevenue.get('Juice')+DistributorRevenue.get('Water')+DistributorRevenue.get('nineteenLtr')+DistributorRevenue.get('Confectionery')+DistributorRevenue.get('Concentrate')+ShopRevenue.get('csd')+ShopRevenue.get('Juice')+ShopRevenue.get('Water')+ShopRevenue.get('nineteenLtr')+ShopRevenue.get('Confectionery')+ShopRevenue.get('Concentrate')+InterunitRevenue.get('csd')+InterunitRevenue.get('Juice')+InterunitRevenue.get('Water')+InterunitRevenue.get('nineteenLtr')+InterunitRevenue.get('Confectionery')+InterunitRevenue.get('Concentrate')
									print(sumtotal)			
									for index,bgroup_data in enumerate(bgroup):
								
											if(bgroup_data=='Concentrate'):
												sumdiv = InterunitRevenue.get('Concentrate')+ShopRevenue.get('Concentrate')+DistributorRevenue.get('Concentrate')
												Amount =   ((sumdiv/sumtotal) * data[0].account_value) 
											elif(bgroup_data=='CSD (Carbonated Soft Drinks)'):
												sumdiv = InterunitRevenue.get('csd')+ShopRevenue.get('csd')+DistributorRevenue.get('csd')
												Amount =   ((sumdiv/sumtotal) * data[0].account_value) 
											elif(bgroup_data=='Juice'):
												sumdiv = InterunitRevenue.get('Juice')+ShopRevenue.get('Juice')+DistributorRevenue.get('Juice')
												Amount =   ((sumdiv/sumtotal) * data[0].account_value) 
											elif(bgroup_data=='Other'):
												Amount =0.000
											elif(bgroup_data=='19 Ltr'):
												sumdiv = InterunitRevenue.get('nineteenLtr')+ShopRevenue.get('nineteenLtr')+DistributorRevenue.get('nineteenLtr')
												Amount =   ((sumdiv/sumtotal) * data[0].account_value) 
											elif(bgroup_data=='Water'):
												sumdiv = InterunitRevenue.get('Water')+ShopRevenue.get('Water')+DistributorRevenue.get('Water')
												Amount =   ((sumdiv/sumtotal) * data[0].account_value) 
											elif(bgroup_data=='Confectionery'):
												sumdiv = InterunitRevenue.get('Confectionery')+ShopRevenue.get('Confectionery')+DistributorRevenue.get('Confectionery')
												Amount =   ((sumdiv/sumtotal) * data[0].account_value) 
												
											print(sumdiv)	
											save_doc = {
											'doctype':'Account Segment Data',
											'segment':bgroup_data,
											'account':coa.title(),
											'coa': str(account),
											'company':single_unit,
											'head':head.title(),
											'date':date_yesterday,
											'account_value':float(Amount)
											}
											frappe.get_doc(save_doc).save(ignore_permissions=True)	
							elif(coa.title()=='Salaries Sales Staff' or coa.title()=='Advertising' or coa.title()=='Out Words Freights' or coa.title()=='Whare House Fork Lifetr Fuel & Repair' or coa.title()=='Give Away' or coa.title()=='Other Selling Expenses'):
									sumdiv=0.0
									sumtotal=0.0
									data = frappe.db.sql("""
												SELECT IFNULL(SUM(`credit_in_account_currency`-`debit_in_account_currency`),0.000) AS account_value 
												FROM `tabGL Entry` WHERE account in ({0})  AND company='{2}' 
												AND DATE(posting_date) BETWEEN '{1}' AND '{1}'
												""".format(account,date_yesterday,single_unit),as_dict=True )
									sumtotal= DistributorRevenue.get('csd')+DistributorRevenue.get('Juice')+DistributorRevenue.get('Water')+DistributorRevenue.get('Confectionery')+ShopRevenue.get('csd')+ShopRevenue.get('Juice')+ShopRevenue.get('Water')+ShopRevenue.get('Confectionery')+InterunitRevenue.get('csd')+InterunitRevenue.get('Juice')+InterunitRevenue.get('Water')+InterunitRevenue.get('Confectionery')
									print(sumtotal)
									for index,bgroup_data in enumerate(bgroup):
										
											if(bgroup_data=='Concentrate'):
												Amount =  0.000
											elif(bgroup_data=='CSD (Carbonated Soft Drinks)'):
												sumdiv=InterunitRevenue.get('csd')+ShopRevenue.get('csd')+DistributorRevenue.get('csd')
												Amount =   (sumdiv/sumtotal) * data[0].account_value 
											elif(bgroup_data=='Juice'):
												sumdiv=InterunitRevenue.get('Juice')+ShopRevenue.get('Juice')+DistributorRevenue.get('Juice')
												Amount =   (sumdiv/sumtotal) * data[0].account_value 
											elif(bgroup_data=='Other'):
												Amount =0.000
											elif(bgroup_data=='19 Ltr'):
												Amount =   0.0000
											elif(bgroup_data=='Water'):
												sumdiv=InterunitRevenue.get('Water')+ShopRevenue.get('Water')+DistributorRevenue.get('Water')
												Amount =   (sumdiv/sumtotal) * data[0].account_value 
												
											elif(bgroup_data=='Confectionery'):
												sumdiv=InterunitRevenue.get('Confectionery')+ShopRevenue.get('Confectionery')+DistributorRevenue.get('Confectionery')
												Amount =   (sumdiv/sumtotal) * data[0].account_value 
												  
											print(sumdiv)
											save_doc = {
											'doctype':'Account Segment Data',
											'segment':bgroup_data,
											'account':coa.title(),
											'coa': str(account),
											'company':single_unit,
											'head':head.title(),
											'date':date_yesterday,
											'account_value':float(Amount)
											}
											frappe.get_doc(save_doc).save(ignore_permissions=True)	
							elif(coa.title()=='Other Material Consumption'):
									sumdiv=0.0
									sumtotal=0.0
									data = frappe.db.sql("""
												SELECT IFNULL(SUM(`credit_in_account_currency`-`debit_in_account_currency`),0.000) AS account_value 
												FROM `tabGL Entry` WHERE account in ({0})  AND company='{2}' 
												AND DATE(posting_date) BETWEEN '{1}' AND '{1}' AND voucher_type!='Delivery Note'
												""".format(account,date_yesterday,single_unit),as_dict=True ,debug=True)
									sumtotal = DistributorRevenue.get('csd')+DistributorRevenue.get('Juice')+DistributorRevenue.get('Water')+DistributorRevenue.get('nineteenLtr')+DistributorRevenue.get('Confectionery')+DistributorRevenue.get('Concentrate')+ShopRevenue.get('csd')+ShopRevenue.get('Juice')+ShopRevenue.get('Water')+ShopRevenue.get('nineteenLtr')+ShopRevenue.get('Confectionery')+ShopRevenue.get('Concentrate')+InterunitRevenue.get('csd')+InterunitRevenue.get('Juice')+InterunitRevenue.get('Water')+InterunitRevenue.get('nineteenLtr')+InterunitRevenue.get('Confectionery')+InterunitRevenue.get('Concentrate')
									print(sumtotal)			
									for index,bgroup_data in enumerate(bgroup):
								
											if(bgroup_data=='Concentrate'):
												sumdiv = InterunitRevenue.get('Concentrate')+ShopRevenue.get('Concentrate')+DistributorRevenue.get('Concentrate')
												Amount =   ((sumdiv/sumtotal) * data[0].account_value) 
											elif(bgroup_data=='CSD (Carbonated Soft Drinks)'):
												sumdiv = InterunitRevenue.get('csd')+ShopRevenue.get('csd')+DistributorRevenue.get('csd')
												Amount =   ((sumdiv/sumtotal) * data[0].account_value) 
											elif(bgroup_data=='Juice'):
												sumdiv = InterunitRevenue.get('Juice')+ShopRevenue.get('Juice')+DistributorRevenue.get('Juice')
												Amount =   ((sumdiv/sumtotal) * data[0].account_value) 
											elif(bgroup_data=='Other'):
												Amount =0.000
											elif(bgroup_data=='19 Ltr'):
												sumdiv = InterunitRevenue.get('nineteenLtr')+ShopRevenue.get('nineteenLtr')+DistributorRevenue.get('nineteenLtr')
												Amount =   ((sumdiv/sumtotal) * data[0].account_value) 
											elif(bgroup_data=='Water'):
												sumdiv = InterunitRevenue.get('Water')+ShopRevenue.get('Water')+DistributorRevenue.get('Water')
												Amount =   ((sumdiv/sumtotal) * data[0].account_value) 
											elif(bgroup_data=='Confectionery'):
												sumdiv = InterunitRevenue.get('Confectionery')+ShopRevenue.get('Confectionery')+DistributorRevenue.get('Confectionery')
												Amount =   ((sumdiv/sumtotal) * data[0].account_value) 
												
											print(sumdiv)	
											save_doc = {
											'doctype':'Account Segment Data',
											'segment':bgroup_data,
											'account':coa.title(),
											'coa': str(account),
											'company':single_unit,
											'head':head.title(),
											'date':date_yesterday,
											'account_value':float(Amount)
											}
											frappe.get_doc(save_doc).save(ignore_permissions=True)		
						else:
							if (coa.title()=='Distributor Revenue'):
									DRData =  frappe.db.sql("""
											select business_group,sum(amount) as amount from `tabSales Invoice Item` as A
											INNER JOIN `tabItem` as B ON A.`item_code` = B.item_code
											INNER JOIN `tabSales Invoice` AS C ON C.name = A.parent
											INNER JOIN `tabCustomer` AS D ON D.name = C.`customer`
											where 
											DATE(C.`posting_date`) between '{0}' AND '{0}' AND C.docstatus=1 AND C.company = '{1}' AND D.customer_group IN ('All Customer Groups','CSD Distributors','Restaurants','Gourmet Gujranwala Shops','Confectionary Distributors','RGB Distributors')
											AND `business_group` IN ('CSD (Carbonated Soft Drinks)','Concentrate','Confectionery','Water','Juice','19 Ltr','Other')	
											GROUP BY business_group											
											""".format(date_yesterday,single_unit),as_dict=True)
									count = 0
									for index,bg in enumerate(bgroup):			
										if bg not in str(DRData):
											Amount=0.000
										else:
											Amount= DRData[count].get('amount')
											count = count + 1
											
										if(bg=='Concentrate'):
											DistributorRevenue['Concentrate'] = Amount
										elif(bg=='CSD (Carbonated Soft Drinks)'):
											DistributorRevenue['csd'] = Amount
										elif(bg=='Juice'):
											DistributorRevenue['Juice'] = Amount
										elif(bg=='Other'):
											DistributorRevenue['other']= Amount
										elif(bg=='19 Ltr'):
											DistributorRevenue['nineteenLtr']= Amount
										elif(bg=='Water'):
											DistributorRevenue['Water']= Amount
										elif(bg=='Confectionery'):
											DistributorRevenue['Confectionery']= Amount
										save_doc = {
											'doctype':'Account Segment Data',
											'segment':bg,
											'account':coa.title(),
											'coa': str(account),
											'company':single_unit,
											'head':head.title(),
											'date':date_yesterday,
											'account_value':float(Amount)
											}
										frappe.get_doc(save_doc).save(ignore_permissions=True)	
							elif (coa.title()=='Shop Sale'):
									Shopdata =  frappe.db.sql("""
												select business_group,sum(amount) as amount from `tabSales Invoice Item` as A
												INNER JOIN `tabItem` as B ON A.`item_code` = B.item_code
												INNER JOIN `tabSales Invoice` AS C ON C.name = A.parent
												INNER JOIN `tabCustomer` AS D ON D.name = C.`customer`
												where 
												DATE(C.`posting_date`) between '{0}' AND '{0}' AND C.docstatus=1 AND C.company = '{1}' AND D.customer_group IN ('Faisalabad Retail Shops','Islamabad Retail Shops','Multan Retail Shops','Lahore Retail Shops','Key-Account Customer','Modern Trade Shop')
												AND `business_group` IN ('CSD (Carbonated Soft Drinks)','Concentrate','Confectionery','Water','Juice','19 Ltr','Other')	
											GROUP BY business_group		
												""".format(date_yesterday,single_unit),as_dict=True)
									count = 0
									for index,bg in enumerate(bgroup):			
										if bg not in str(Shopdata):
											Amount=0.000
										else:
											Amount= Shopdata[count].get('amount')
											count = count + 1
											
										if(bg=='Concentrate'):
											ShopRevenue['Concentrate'] = Amount
										elif(bg=='CSD (Carbonated Soft Drinks)'):
											ShopRevenue['csd'] = Amount
										elif(bg=='Juice'):
											ShopRevenue['Juice'] = Amount
										elif(bg=='Other'):
											ShopRevenue['other']= Amount
										elif(bg=='19 Ltr'):
											ShopRevenue['nineteenLtr']= Amount
										elif(bg=='Water'):
											ShopRevenue['Water']= Amount
										elif(bg=='Confectionery'):
											ShopRevenue['Confectionery']= Amount

										save_doc = {
											'doctype':'Account Segment Data',
											'segment':bg,
											'account':coa.title(),
											'coa': str(account),
											'company':single_unit,
											'head':head.title(),
											'date':date_yesterday,
											'account_value':float(Amount)
											}
										frappe.get_doc(save_doc).save(ignore_permissions=True)	
							elif (coa.title()=='Inter Units Revenue'):
									iudata =  frappe.db.sql("""
												select business_group,sum(amount) as amount from `tabSales Invoice Item` as A
												INNER JOIN `tabItem` as B ON A.`item_code` = B.item_code
												INNER JOIN `tabSales Invoice` AS C ON C.name = A.parent
												INNER JOIN `tabCustomer` AS D ON D.name = C.`customer`
												where 
												DATE(C.`posting_date`) between '{0}' AND '{0}' AND C.docstatus=1 AND C.company = '{1}'  AND D.customer_group IN ('Inter-Unit')
												AND `business_group` IN ('CSD (Carbonated Soft Drinks)','Concentrate','Confectionery','Water','Juice','19 Ltr','Other')	
											GROUP BY business_group		
												""".format(date_yesterday,single_unit),as_dict=True)
									count = 0
									for index,bg in enumerate(bgroup):			
										if bg not in str(iudata):
											Amount=0.000
										else:
											Amount= iudata[count].get('amount')
											count = count + 1
											
										if(bg=='Concentrate'):
											InterunitRevenue['Concentrate'] = Amount
										elif(bg=='CSD (Carbonated Soft Drinks)'):
											InterunitRevenue['csd'] = Amount
										elif(bg=='Juice'):
											InterunitRevenue['Juice'] = Amount
										elif(bg=='Other'):
											InterunitRevenue['other']= Amount
										elif(bg=='19 Ltr'):
											InterunitRevenue['nineteenLtr']= Amount
										elif(bg=='Water'):
											InterunitRevenue['Water']= Amount
										elif(bg=='Confectionery'):
											InterunitRevenue['Confectionery']= Amount

										save_doc = {
											'doctype':'Account Segment Data',
											'segment':bg,
											'account':coa.title(),
											'coa': str(account),
											'company':single_unit,
											'head':head.title(),
											'date':date_yesterday,
											'account_value':float(Amount)
											}
										frappe.get_doc(save_doc).save(ignore_permissions=True)
							elif(coa.title()=='Other Revenue'):
									otherdata =  frappe.db.sql("""
												select business_group,sum(amount) as amount from `tabSales Invoice Item` as A
												INNER JOIN `tabItem` as B ON A.`item_code` = B.item_code
												INNER JOIN `tabSales Invoice` AS C ON C.name = A.parent
												INNER JOIN `tabCustomer` AS D ON D.name = C.`customer`
												where 
												DATE(C.`posting_date`) between '{0}' AND '{0}' AND C.docstatus=1 AND C.company = '{1}' AND D.customer_group NOT IN ('Faisalabad Retail Shops','Islamabad Retail Shops','Multan Retail Shops','Lahore Retail Shops','Key-Account Customer','Modern Trade Shop','Inter-Unit','All Customer Groups','CSD Distributors','Restaurants','Gourmet Gujranwala Shops','Confectionary Distributors','RGB Distributors')
												AND `business_group` IN ('CSD (Carbonated Soft Drinks)','Concentrate','Confectionery','Water','Juice','19 Ltr','Other')	
											GROUP BY business_group		
												""".format(date_yesterday,single_unit),as_dict=True)
									count = 0
									for index,bg in enumerate(bgroup):			
										if bg not in str(otherdata):
											Amount=0.000
										else:
											Amount= otherdata[count].get('amount')
											count = count + 1
										

										save_doc = {
											'doctype':'Account Segment Data',
											'segment':bg,
											'account':coa.title(),
											'coa': str(account),
											'company':single_unit,
											'head':head.title(),
											'date':date_yesterday,
											'account_value':float(Amount)
											}
										frappe.get_doc(save_doc).save(ignore_permissions=True)
							elif(coa.title()=='Distributor Margin'):
									dict = {}
									Amount = 0	
									result = frappe.db.sql(f"""SELECT item_wise_tax_detail
																	FROM `tabSales Invoice` AS A
																	INNER JOIN `tabSales Taxes and Charges` AS B ON B.parent= A.name
																	INNER JOIN `tabCustomer` AS C ON C.name = A.`customer`
																	WHERE A.docstatus=1 AND  DATE(A.`posting_date`) BETWEEN '{date_yesterday}' AND '{date_yesterday}' AND A.company = '{single_unit}'  AND C.customer_group IN ('All Customer Groups','CSD Distributors','Restaurants','Gourmet Gujranwala Shops','Confectionary Distributors','RGB Distributors') 
																	AND B.`account_head` in ({account})""")
									b_g = frappe.db.sql("""SELECT business_group, group_concat(NAME) as items_code FROM `tabItem` GROUP BY business_group""", as_dict=True)
									for d in result:
											json_result = json.loads(d[0])
											for item_code, value in json_result.items():
												bg = ''
												for i in b_g:
													if item_code in i.items_code:
														bg = i.business_group
												if bg in dict:
													dict[bg] += value[1]
												else:
													dict[bg] = value[1]
									
									for index,bg in enumerate(bgroup):
										if bg not in dict:
											Amount=0.000
										else:
											Amount= dict.get(bg)
										
										save_doc = {
												'doctype':'Account Segment Data',
												'segment':bg,
												'account':coa.title(),
												'coa': str(account),
												'company':single_unit,
												'head':head.title(),
												'date':date_yesterday,
												'account_value':float(Amount)
											}
										frappe.get_doc(save_doc).save(ignore_permissions=True)	
							elif(coa.title()=='Retailer Margin'):
									dict = {}
									Amount = 0	
									result = frappe.db.sql(f"""SELECT item_wise_tax_detail
																	FROM `tabSales Invoice` AS A
																	INNER JOIN `tabSales Taxes and Charges` AS B ON B.parent= A.name
																	INNER JOIN `tabCustomer` AS C ON C.name = A.`customer`
																	WHERE A.docstatus=1 AND  DATE(A.`posting_date`) BETWEEN '{date_yesterday}' AND '{date_yesterday}' AND A.company = '{single_unit}'  AND C.customer_group IN ('All Customer Groups','CSD Distributors','Restaurants','Gourmet Gujranwala Shops','Confectionary Distributors','RGB Distributors') 
																	AND B.`account_head` in ({account})""")
									b_g = frappe.db.sql("""SELECT business_group, group_concat(NAME) as items_code FROM `tabItem` GROUP BY business_group""", as_dict=True)
									for d in result:
											json_result = json.loads(d[0])
											for item_code, value in json_result.items():
												bg = ''
												for i in b_g:
													if item_code in i.items_code:
														bg = i.business_group
												if bg in dict:
													dict[bg] += value[1]
												else:
													dict[bg] = value[1]
									
									for index,bg in enumerate(bgroup):
										if bg not in dict:
											Amount=0.000
										else:
											Amount= dict.get(bg)
										
										save_doc = {
												'doctype':'Account Segment Data',
												'segment':bg,
												'account':coa.title(),
												'coa': str(account),
												'company':single_unit,
												'head':head.title(),
												'date':date_yesterday,
												'account_value':float(Amount)
											}
										frappe.get_doc(save_doc).save(ignore_permissions=True)
							elif(coa.title()=='Trade Promo'):
									dict = {}
									Amount = 0	
									result = frappe.db.sql(f"""SELECT item_wise_tax_detail
																	FROM `tabSales Invoice` AS A
																	INNER JOIN `tabSales Taxes and Charges` AS B ON B.parent= A.name
																	INNER JOIN `tabCustomer` AS C ON C.name = A.`customer`
																	WHERE A.docstatus=1 AND  DATE(A.`posting_date`) BETWEEN '{date_yesterday}' AND '{date_yesterday}' AND A.company = '{single_unit}'  AND C.customer_group IN ('All Customer Groups','CSD Distributors','Restaurants','Gourmet Gujranwala Shops','Confectionary Distributors','RGB Distributors') 
																	AND B.`account_head` in ({account})""")
									b_g = frappe.db.sql("""SELECT business_group, group_concat(NAME) as items_code FROM `tabItem` GROUP BY business_group""", as_dict=True)
									for d in result:
											json_result = json.loads(d[0])
											for item_code, value in json_result.items():
												bg = ''
												for i in b_g:
													if item_code in i.items_code:
														bg = i.business_group
												if bg in dict:
													dict[bg] += value[1]
												else:
													dict[bg] = value[1]
									
									for index,bg in enumerate(bgroup):
										if bg not in dict:
											Amount=0.000
										else:
											Amount= dict.get(bg)
										
										save_doc = {
												'doctype':'Account Segment Data',
												'segment':bg,
												'account':coa.title(),
												'coa': str(account),
												'company':single_unit,
												'head':head.title(),
												'date':date_yesterday,
												'account_value':float(Amount)
											}
										frappe.get_doc(save_doc).save(ignore_permissions=True)	
							elif(coa.title()=='Shop Sale Discount'):
									dict = {}
									Amount = 0	
									result = frappe.db.sql(f"""SELECT item_wise_tax_detail
																	FROM `tabSales Invoice` AS A
																	INNER JOIN `tabSales Taxes and Charges` AS D ON D.parent= A.name
																	WHERE A.docstatus=1 AND  DATE(A.`posting_date`) BETWEEN '{date_yesterday}' AND '{date_yesterday}' AND A.company = '{single_unit}'  
																	AND D.`account_head` in ({account})""")
									b_g = frappe.db.sql("""SELECT business_group, group_concat(NAME) as items_code FROM `tabItem` GROUP BY business_group""", as_dict=True)
									for d in result:
											json_result = json.loads(d[0])
											for item_code, value in json_result.items():
												bg = ''
												for i in b_g:
													if item_code in i.items_code:
														bg = i.business_group
												if bg in dict:
													dict[bg] += value[1]
												else:
													dict[bg] = value[1]

												Shopdiscountinvoices +=value[1]	
									
									for index,bg in enumerate(bgroup):
										if bg not in dict:
											Amount=0.000
										else:
											Amount= dict.get(bg)
										
										save_doc = {
												'doctype':'Account Segment Data',
												'segment':bg,
												'account':coa.title(),
												'coa': str(account),
												'company':single_unit,
												'head':head.title(),
												'date':date_yesterday,
												'account_value':float(Amount)
											}
										frappe.get_doc(save_doc).save(ignore_permissions=True)	
							elif(coa.title()=='Other Shop Sale Discount'):
									sumdiv=0.0
									sumtotal=0.0
									data = frappe.db.sql("""
												SELECT IFNULL(SUM(`credit_in_account_currency`-`debit_in_account_currency`),0.000) AS account_value 
												FROM `tabGL Entry` WHERE account in ({0})  AND company='{2}' 
												AND DATE(posting_date) BETWEEN '{1}' AND '{1}'
												""".format(account,date_yesterday,single_unit),as_dict=True ,debug=True)
											
									for index,bgroup_data in enumerate(bgroup):
								
											if(bgroup_data=='Concentrate'):
												Amount=0.00
											elif(bgroup_data=='CSD (Carbonated Soft Drinks)'):
												Amount=(-1*Shopdiscountinvoices)-(-1*data[0].account_value)
											elif(bgroup_data=='Juice'):
												Amount=0.00
											elif(bgroup_data=='Other'):
												Amount =0.000
											elif(bgroup_data=='19 Ltr'):
												Amount=0.00
											elif(bgroup_data=='Water'):
												Amount=0.00
											elif(bgroup_data=='Confectionery'):
												Amount=0.00

											save_doc = {
											'doctype':'Account Segment Data',
											'segment':bgroup_data,
											'account':coa.title(),
											'coa': str(account),
											'company':single_unit,
											'head':head.title(),
											'date':date_yesterday,
											'account_value':float(Amount)
											}
											frappe.get_doc(save_doc).save(ignore_permissions=True)	
							elif(coa.title()=='Inter Units Sales Discount'):
									dict = {}
									Amount = 0	
									result = frappe.db.sql(f"""SELECT item_wise_tax_detail
																	FROM `tabSales Invoice` AS A
																	INNER JOIN `tabSales Taxes and Charges` AS D ON D.parent= A.name
																	WHERE A.docstatus=1 AND  DATE(A.`posting_date`) BETWEEN '{date_yesterday}' AND '{date_yesterday}' AND A.company = '{single_unit}'  
																	AND D.`account_head` in ({account})""")
									b_g = frappe.db.sql("""SELECT business_group, group_concat(NAME) as items_code FROM `tabItem` GROUP BY business_group""", as_dict=True)
									for d in result:
											json_result = json.loads(d[0])
											for item_code, value in json_result.items():
												bg = ''
												for i in b_g:
													if item_code in i.items_code:
														bg = i.business_group
												if bg in dict:
													dict[bg] += value[1]
												else:
													dict[bg] = value[1]
									
									for index,bg in enumerate(bgroup):
										if bg not in dict:
											Amount=0.000
										else:
											Amount= dict.get(bg)
										
										save_doc = {
												'doctype':'Account Segment Data',
												'segment':bg,
												'account':coa.title(),
												'coa': str(account),
												'company':single_unit,
												'head':head.title(),
												'date':date_yesterday,
												'account_value':float(Amount)
											}
										frappe.get_doc(save_doc).save(ignore_permissions=True)			
							elif(coa.title()=='Others Income' or coa.title()=='Waste Sale'):
									data = frappe.db.sql("""
												SELECT IFNULL(SUM(`credit_in_account_currency`-`debit_in_account_currency`),0.000) AS account_value 
												FROM `tabGL Entry` WHERE account in ({0})  AND company='{2}' 
												AND DATE(posting_date) BETWEEN '{1}' AND '{1}'
												""".format(account,date_yesterday,single_unit),as_dict=True )
									for index,bgroup_data in enumerate(bgroup):
												if(bgroup_data=='Concentrate'):
													Amount =  0.00
												elif(bgroup_data=='CSD (Carbonated Soft Drinks)'):
													Amount =  data[0].account_value  
												elif(bgroup_data=='Juice'):
													Amount =   0.0000
												elif(bgroup_data=='Other'):
													Amount =0.000
												elif(bgroup_data=='19 Ltr'):
													Amount =     0.0000
												elif(bgroup_data=='Water'):
													Amount =    0.0000 
												elif(bgroup_data=='Confectionery'):
													Amount =   0.0000
									
												save_doc = {
												'doctype':'Account Segment Data',
												'segment':bgroup_data,
												'account':coa.title(),
												'coa': str(account),
												'company':single_unit,
												'head':head.title(),
												'date':date_yesterday,
												'account_value':float(Amount)
												}
												frappe.get_doc(save_doc).save(ignore_permissions=True)
							elif(coa.title()=='Material Consumption'):
									Consumption =  frappe.db.sql("""
													SELECT business_group,SUM(stock_value_difference) as amount FROM `tabStock Ledger Entry`  AS A
													INNER JOIN `tabItem` AS B ON A.`item_code` = B.item_code
													WHERE  A.voucher_type='Delivery Note' AND DATE(A.posting_date) BETWEEN '{0}' AND '{0}' AND A.company = '{1}'
													AND `business_group` IN ('CSD (Carbonated Soft Drinks)','Concentrate','Confectionery','Water','Juice','19 Ltr','Other')	
													GROUP BY business_group	
													""".format(date_yesterday,single_unit),as_dict=True)
									count = 0
									for index,bg in enumerate(bgroup):			
										if bg not in str(Consumption):
											Amount=0.000
										else:
											Amount = (-1*(Consumption[count].get('amount')))
											count = count + 1

										save_doc = {
											'doctype':'Account Segment Data',
											'segment':bg,
											'account':coa.title(),
											'coa': str(account),
											'company':single_unit,
											'head':head.title(),
											'date':date_yesterday,
											'account_value':float(Amount)
											}
										frappe.get_doc(save_doc).save(ignore_permissions=True)	
						
						frappe.db.commit()

							

