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
	r_data = frappe.db.sql(""" 
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
	data = prepare_data(r_data)

	return columns, data
def prepare_data(r_data):
	import copy
	final_data = [{
        'indent': 0,
        'head': 'Total Profit',
        'parent_item_group': None,
        'csd':0,
        'juices':0,
        'water':0,
        'candyconfectionary':0,
        'concentrates':0,
        '19ltr':0,
        'other':0
        
        
    }]
	parent_head =""
	for k, d in enumerate(r_data):
		if parent_head != d.head:
			parent_head = d.head
			child_rows=[]
			parent_row = copy.copy(d)
			parent_row["concentrates"]=parent_row["csd"]=parent_row["juices"]=parent_row["water"]=parent_row["candyconfectionary"]=parent_row["19ltr"]=parent_row["other"]=0
			account =""
			for _k, _d in enumerate(r_data[k:]):
				if parent_head == _d.head:
					parent_row["csd"] += float(_d["csd"] or 0)
					parent_row["juices"] += float(_d["juices"] or 0)
					parent_row["water"] += float(_d["water"] or 0)
					parent_row["candyconfectionary"] += float(_d["candyconfectionary"] or 0)
					parent_row["concentrates"] += float(_d["concentrates"] or 0)
					parent_row["19ltr"] += float(_d["19ltr"] or 0)
					parent_row["other"] += float(_d["other"] or 0)
					parent_row['account']=''
					head=""
					if account != _d.account:
						account = _d.account
						child_row = copy.copy(_d)
						child_row['csd'] = float(_d["csd"] or 0)
						child_row['juices'] = float(_d["juices"] or 0)
						child_row['water'] = float(_d["water"] or 0)
						child_row['candyconfectionary'] = float(_d["candyconfectionary"] or 0)
						child_row["concentrates"] = float(_d["concentrates"] or 0)
						child_row['19ltr'] = float(_d["19ltr"] or 0)
						child_row['other'] = float(_d["other"] or 0)
						child_row['head'] = ''
						child_row['parent_item_group'] = _d["head"]
						child_row['indent'] = 2
						child_row['has_value'] = True
						grand_child = []
						child_rows.append(child_row)


			parent_row['indent'] = 1
			parent_row['parent_item_group'] ='Total Profit'
			parent_row['has_value'] = True
			final_data.append(parent_row)
			final_data[0]['csd'] += parent_row['csd']
			final_data[0]['juices'] += parent_row['juices']
			final_data[0]['water'] += parent_row['water']
			final_data[0]['candyconfectionary'] += parent_row['candyconfectionary']
			final_data[0]["concentrates"]  += parent_row['concentrates']
			final_data[0]['19ltr'] += parent_row['19ltr']
			final_data[0]['other'] += parent_row['other']
			for row in child_rows:
				final_data.append(row)
	return final_data