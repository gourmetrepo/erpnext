# Copyright (c) 2013, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

from __future__ import unicode_literals
import frappe

def execute(filters=None):

	company = filters.get('company')
	from_date = filters.get('from_date')
	to_date = filters.get('to_date')
	columns = [
		("HEAD")+ "::250",
		("ACCOUNT") + "::250",
        ("CSD") + ":Float:250",
        ("JUICES") + ":Float:200",
        ("WATER") + ":Float:150",
        ("CandyConfectionary") + ":Float:120",
        ("Concentrates") + ":Float:120",
        ("19LTR") + ":Float:180",
		("Other") + ":Float:180"
    ]
	data = []
	from_date='2023-03-01'
	to_date='2023-03-05'
	data = frappe.db.sql(""" 
		SELECT head,`account`,
			SUM(IF (`segment`='CSD (Carbonated Soft Drinks)' , `account_value`,0)) AS csd, 
			SUM(IF (`segment`='Juice' , `account_value` ,0))AS juices,
			SUM(IF (`segment`='Water' , `account_value`,0))AS  water,
			SUM(IF (`segment`='Confectionery' , `account_value`,0)) AS  candyconfectionary,
			SUM(IF (`segment`='Concentrate' , `account_value` ,0)) AS concentrates,
			SUM(IF (`segment`='19 Ltr'  ,`account_value`,0) ) AS 19ltr,
			SUM(IF (`segment`='Other' , `account_value` ,0)) AS other
		FROM `tabAccount Segment Data`
		WHERE date BETWEEN '{from_date}' and '{to_date}' 
		AND company = '{company}'
			group by head,`account`
	""".format(from_date=from_date, to_date=to_date,company=company), as_dict=True)
	
	return columns, data
