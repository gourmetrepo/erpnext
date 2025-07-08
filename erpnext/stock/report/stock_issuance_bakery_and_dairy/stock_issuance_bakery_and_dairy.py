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
		if isinstance(sub_branch, list):
			sub_branch_cond = 'se.sub_branch IN (' + ', '.join(f'"{sb}"' for sb in sub_branch) + ')'
			conditions = f"{conditions} AND {sub_branch_cond}"
		else:
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
			},
			"Production-Issue": {
				"Stock Entry Type": "Material Issue",
				"Sub Branch": [
					"1005 - Liaqat Chowk - U6",
					"1008 - Youhannabad - U6",
					"1010 - Wahdat Road - U6",
					"1013 - Daroghawala - U6",
					"1019 - Kot Abdul Malik - U6",
					"1032 - Rahber Dha - U6",
					"1037 - Raiwind Road - U6",
					"1039 - FF-4 Dha - U6",
					"1047 - Kahna Now - U6",
					"1050 - Ferozpur Road - U6",
					"1053 - Jaurrey Pull - U6",
					"1061 - Military Accounts College Road Lhr - U6",
					"1062 - Faisal Town - U6",
					"1066 - Air Line - U6",
					"1068 - 12-G - U6",
					"1075 - Johar Town - U6",
					"1099 - Eme Society - U6",
					"1101 - Qadar Adab Chaowk Kasur - U6",
					"2010 - Bankers Co-operative H.Society - U6",
					"Auto Workshop - U6",
					"Bakery Shipping Lahore Region - U6",
					"Bakery Transportation Lahore Region - U6",
					"Barfi - U6",
					"Biscuit Finished Item - U6",
					"Biscuit Mixing - U6",
					"Biscuit Molding - U6",
					"BON Cakes - U6",
					"BON Sponge - U6",
					"Bread Mixing - U6",
					"Bread Molding - U6",
					"Bread Oven - U6",
					"Bread Packing - U6",
					"Bulk Water - U6",
					"Bulk Water Shipping - U6",
					"Chum Chum - U6",
					"Dry Cake Filling - U6",
					"Dry Cake Mixing - U6",
					"Dry Cake Molding - U6",
					"Dry Cake Packing - U6",
					"Executive Building - U6",
					"FC Cakes - U6",
					"FC Pastries - U6",
					"FC Sponge - U6",
					"Food Cooking U-3 - U6",
					"Gate Office - U6",
					"Jaman - U6",
					"Kitchen Finished Item - U6",
					"Kitchen Preparation - U6",
					"Laddo - U6",
					"Live Stock - U6",
					"Material Store - U6",
					"Nimko - U6",
					"Oil & Lubricant - U6",
					"Packing - U6",
					"Paramedics - U6",
					"Patisa - U6",
					"Pizza Mixing - U6",
					"Pizza Molding - U6",
					"Pizza Oven - U6",
					"Pizza Packing - U6",
					"Pizza Preparation - U6",
					"Production - U6",
					"Puff Pastry Mixing - U6",
					"Puff Pastry Molding - U6",
					"Puff Pastry Oven - U6",
					"Puff Pastry Packing - U6",
					"Quality Assurance - U6",
					"Quintech Sciences - U6",
					"Research & Development - U6",
					"Rusk Mixing - U6",
					"Rusk Oven - U6",
					"Rusk Packing - U6",
					"Sanitation & Hygiene - U6",
					"Supply Chain - U6",
					"Unit Accounts - U6",
					"Unit Administration - U6",
					"Unit Electrical - U6",
					"Unit Mechanical - U6",
					"Unit Rac Refrigeration - U6",
					"Unit Security - U6"
				]
			},
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
