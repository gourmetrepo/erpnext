# Copyright (c) 2013, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

from __future__ import unicode_literals
import frappe

def execute(filters=None):
	columns = get_columns(filters)
	data = get_data(filters)
	
	return columns, data


def get_columns(filters):
	if not filters:
		filters = {}
		return []
	return [
		{
			"label": "Stock Entry Number", 
			"fieldname": "stock_entry_no", 
			"fieldtype": "Data", 
			"width": 150
		},
		{
			"label": "Stock Entry Type", 
			"fieldname": "stock_entry_type", 
			"fieldtype": "Data", 
			"width": 150
		},
		{
			"label": "Item Code",
			"fieldname": "item_code",
			"fieldtype": "Data",
			"width": 100,
		},
		{
			"label": "Item Name",
			"fieldname": "item_name",
			"fieldtype": "Data",
			"width": 200,
		},
		{
			"label": "UOM", 
			"fieldname": "uom", 
			"fieldtype": "Data", 
			"width": 80
		},
		{
			"label": "Qty", 
			"fieldname": "qty", 
			"fieldtype": "Float", 
			"width": 100
		},
		{
			"label": "Rate", 
			"fieldname": "rate", 
			"fieldtype": "Float", 
			"width": 100
		},
		{
			"label": "Amount", 
			"fieldname": "amount", 
			"fieldtype": "Currency", 
			"width": 150
		},
		{
			"label": "Warehouse", 
			"fieldname": "warehouse", 
			"fieldtype": "Data", 
			"width": 150
		},
		{
			"label": "Sub Type", 
			"fieldname": "sub_type", 
			"fieldtype": "Data", 
			"width": 150
		},
		{
			"label": "Sub Branch", 
			"fieldname": "sub_branch", 
			"fieldtype": "Data", 
			"width": 250
		}
	]


def get_data(filters):
	if not filters:
		filters = {}
		return []
	conditions = get_conditions(filters)
	if not conditions:
		return []
	query = f"""
	SELECT 
		se.name AS stock_entry_no, 
		se.stock_entry_type, 
		sed.item_code, 
		sed.item_name, 
		sed.uom, 
		sed.qty, 
		sed.valuation_rate AS rate,
		sed.qty * sed.valuation_rate AS amount,
		sed.t_warehouse AS warehouse, 
		se.mr_sub_type AS sub_type, 
		se.sub_branch 
	FROM 
		`tabStock Entry` se
	INNER JOIN 
		`tabStock Entry Detail` sed ON sed.parent=se.name
	WHERE {conditions}
	ORDER BY se.name;"""

	return frappe.db.sql(query, as_dict=True)


def get_conditions(filters):
	conditions = ""
	mapping = get_department_mapping()
	
	company = filters.get("company")
	department = filters.get("department")
	
	stock_entry_type = mapping.get(company, {}).get(department, {}).get("Stock Entry Type", None)
	sub_branch = mapping.get(company, {}).get(department, {}).get("Sub Branch", None)
	target_warehouse = mapping.get(company, {}).get(department, {}).get("Target Warehouse", None)
	
	if company:
		conditions = f"se.company = {frappe.db.escape(company)}"
	if stock_entry_type:
		conditions = f"{conditions} AND se.stock_entry_type = {frappe.db.escape(stock_entry_type)}"
	if sub_branch:
		conditions = f"{conditions} AND se.sub_branch = {frappe.db.escape(sub_branch)}"
	if filters.get("posting_date"):
		conditions = f"{conditions} AND se.posting_date >= {frappe.db.escape(filters.get('posting_date'))} AND se.posting_date <= {frappe.db.escape(filters.get('posting_date'))}"
	if target_warehouse:
		warehouse_cond = 'sed.t_warehouse IN (' + ', '.join(f'"{w}"' for w in target_warehouse) + ')'
		conditions = f"{conditions} AND {warehouse_cond}"
	
	return conditions


def get_department_mapping():
	return {
		"Unit 6": {
			"Langer": {
				"Stock Entry Type": "Material Issue",
				"Sub Branch": "Food Cooking U-3 - U6"
			},
			"Mess-Issue": {
				"Stock Entry Type": "Material Issue",
				"Sub Branch": "Mess-U6"
			},
			"Mess-Transfer":{
				"Stock Entry Type": "Material Transfer",
				"Target Warehouse": [
					"Mess Store - U6", 
					"Mess ODS RM - U6"
				]
			},
			"Other Unit": {
				"Stock Entry Type": "Send to warehouse",
				"Target Warehouse": [
					"In-Transit HS to Faisalabad - U6", 
					"In-Transit HS to Islamabad - U6", 
					"In-Transit HS to Multan - U6", 
					"In-Transit ODS Main Bulk Water - U6", 
					"In-Transit Warehouse - U6"
				]
			},
			"Live Shops": {
				"Stock Entry Type": "Material Transfer",
				"Target Warehouse": [
					"HS Kot Abdul Malik - U6", 
					"HS Qadrabad - U6"
				]
			},
			"Production-Transfer": {
				"Stock Entry Type": "Material Transfer",
				"Target Warehouse": [
					"DCS ODS RM - U6", 
					"DCS ODS PM - U6",
					"ODS BON RM - U6",
					"ODS BON PM - U6",
					"MTH ODS RM - U6",
					"MTH ODS PM - U6",
					"NMK ODS RM - U6",
					"NMK ODS PM - U6",
					"BRD ODS RM - U6",
					"BRD ODS PM - U6",
					"ODS FCC RM - U6",
					"ODS FCC PM - U6",
					"ODS Bulk Water RM - U6",
					"ODS Bulk Water PM - U6",
					"KCN ODS RM - U6",
					"KCN ODS PM - U6",
					"SNK ODS RM - U6",
					"SNK ODS PM - U6",
					"PUFF ODS RM - U6",
					"PUFF ODS PM - U6",
					"BCS ODS RM - U6",
					"BCS ODS PM - U6",
					"Bakery Export ODS RM - U6",
					"Bakery Export ODS PM - U6",
					"ODS R&D RM - U6",
					"ODS R&D PM - U6",
					"ODS RSK RM - U6",
					"ODS RSK PM - U6"
				]
			}
		},
		"Unit 6IC": {
			"Production-Issue": {
				"Stock Entry Type": "Material Issue",
				"Sub Branch": "Production - 6IC"
			},
			"Production-Transfer": {
				"Stock Entry Type": "Material Transfer",
				"Target Warehouse": [
					"Work In Progress - 6IC"
				]
			}
		}
	}
