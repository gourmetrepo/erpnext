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
        ("CSD") + ":Currency:120",
        ("JUICES") + ":Currency:120",
        ("WATER") + ":Currency:120",
        ("CandyConfectionary") + ":Currency:150",
        ("Concentrates") + ":Currency:120",
        ("19LTR") + ":Currency:120",
		("Other") + ":Currency:120",
		("Total") + ":Currency:120"
    ]
	f_data = []
	data = []
	# from_date='2023-03-01'
	# to_date='2023-03-05'
	r_data = frappe.db.sql("""SELECT head,account,csd,juices,water,candyconfectionary,concentrates,19ltr,other,(csd+juices+water+candyconfectionary+concentrates+19ltr+other) AS total FROM (
SELECT head,account,
			SUM(IF (`segment`='CSD (Carbonated Soft Drinks)' , `account_value`,0)) AS csd, 
			SUM(IF (`segment`='Juice' , `account_value` ,0))AS juices,
			SUM(IF (`segment`='Water' , `account_value`,0))AS  water,
			SUM(IF (`segment`='Confectionery' , `account_value`,0)) AS  candyconfectionary,
			SUM(IF (`segment`='Concentrate' , `account_value` ,0)) AS concentrates,
			SUM(IF (`segment`='19 Ltr'  ,`account_value`,0) ) AS 19ltr,
			SUM(IF (`segment`='Other' , `account_value` ,0)) AS other
		FROM `tabAccount Segment Data`
		WHERE DATE BETWEEN '{from_date}' and '{to_date}' 
		AND company = '{company}'
			GROUP BY head,`account` order by creation ASC
   ) AS A 
	""".format(from_date=from_date, to_date=to_date,company=company), as_dict=True, debug =1)
	data = prepare_data(r_data)
#  ORDER BY CASE
#          WHEN A.head = 'Revenue' THEN 1
#          WHEN A.head = 'Cost Of Goods Sold' THEN 2 
#          WHEN A.head = 'Other Income' THEN 3
#          WHEN A.head = 'Administrative Expenses' THEN 4
#          WHEN A.head= 'Selling And Distribution Expenses' THEN 5
#          WHEN A.head= 'Markup Long Term Loans' THEN 6
#           WHEN A.head= 'Taxation' THEN 7
#          END ASC  

	return columns, data
def prepare_data(r_data):	
	import copy
	other_total=total_total =ltr_total=csd_total=juices_total=water_total=candyconfectionary_total=concentrates_total=concentrates_total=0.00
	data = []
	parent_head =""
	for k, d in enumerate(r_data):
		if parent_head != d.head:
			parent_head = d.head
			child_rows=[]
			parent_row = copy.copy(d)
			parent_row["concentrates"]=parent_row["csd"]=parent_row["juices"]=parent_row["water"]=parent_row["candyconfectionary"]=parent_row["19ltr"]=parent_row["other"]=0
			account =""
			parent_row["total"] =0.00
			for _k, _d in enumerate(r_data[k:]):
				
				if parent_head == _d.head:
					parent_row["csd"] += round(float(_d["csd"] or 0),2)
					parent_row["juices"] += round(float(_d["juices"] or 0),2)
					parent_row["water"] += round(float(_d["water"] or 0),2)
					parent_row["candyconfectionary"] += round(float(_d["candyconfectionary"] or 0),2)
					parent_row["concentrates"] += round(float(_d["concentrates"] or 0),2)
					parent_row["19ltr"] += round(float(_d["19ltr"] or 0),2)
					parent_row["other"] += round(float(_d["other"] or 0),2)
					parent_row["total"] += round(float(_d["total"] or 0),2)
					parent_row['account']=''
					head=""
					if account != _d.account:
						account = _d.account
						child_row = copy.copy(_d)
						child_row['csd'] = round(float(_d["csd"] or 0),2)
						child_row['juices'] = round(float(_d["juices"] or 0),2)
						child_row['water'] = round(float(_d["water"] or 0),2)
						child_row['candyconfectionary'] = round(float(_d["candyconfectionary"] or 0),2)
						child_row["concentrates"] = round(float(_d["concentrates"] or 0),2)
						child_row['19ltr'] = round(float(_d["19ltr"] or 0),2)
						child_row['other'] = round(float(_d["other"] or 0),2)
						child_row["total"] = round(float(_d["total"] or 0),2)
						child_row['head'] = ''
						child_row['parent_item_group'] = _d["head"]
						child_row['indent'] = 1
						child_row['has_value'] = True
						grand_child = []
						child_rows.append(child_row)
				
						csd_total += _d['csd']
						juices_total += _d['juices']
						water_total += _d['water']
						candyconfectionary_total += _d['candyconfectionary']
						concentrates_total  += _d['concentrates']
						ltr_total += _d['19ltr']
						other_total += _d['other']
						total_total += _d['total']
			parent_row['indent'] = 0
			# parent_row['parent_item_group'] ='Total Profit'
			#parent_row['has_value'] = True
			data.append(parent_row)
				
			for row in child_rows:
				data.append(row)

	data.append({'head': 'Net Profit Segment Wise', 'account': '', 'csd':  round(csd_total,2), 'juices':  round(juices_total,2),
             'water':  round(water_total,2), 'candyconfectionary': round(candyconfectionary_total,2), 'concentrates':  round(concentrates_total,2), '19ltr':  round(ltr_total,2), 'other': round(other_total,2),'total': round(total_total,2), })
	data.append({'head': 'Net Profit Total', 'account': '','csd': '',  'juices':'',
             'water': '', 'candyconfectionary':'', 'concentrates': '', '19ltr':  '', 'other': '','total':round(candyconfectionary_total+ltr_total+other_total+concentrates_total+csd_total+juices_total+water_total,2) })
	

	return data