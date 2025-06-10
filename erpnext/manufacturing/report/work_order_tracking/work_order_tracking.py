# Copyright (c) 2013, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

from __future__ import unicode_literals
import frappe

def execute(filters=None):
	columns, data = [], []
	work_order_names = []
	work_order_data = {}
	if not filters:
		filters = {}

	from_date = filters.get("from_date")
	to_date = filters.get("to_date")

	if filters.get("company") == "ALL":
		company = f"IN ('Unit 5', 'Unit 8', 'Unit 11')"
	else:
		company = f"""= '{filters.get('company')}'"""

	if filters.get("item_category") == "ALL":
		item_category = f"IN ('Finished Good', 'Semi Finished Good')"
	else:
		item_category = f"""= '{filters.get('item_category')}'"""

	if filters.get("work_order_status") == "ALL":
		work_order_status = "IN ('0', '1')"
	elif filters.get("work_order_status") == "Open":
		work_order_status = "= '0'"
	elif filters.get("work_order_status") == "Closed":
		work_order_status = "= '1'"

	
	
	
	data = get_work_order_data(company, from_date, to_date, item_category, work_order_status)
	
	work_order_names = [wo.work_order for wo in data]
	
	# Convert list to dict
	wo_data_dict = {wo.work_order: wo for wo in data}
	for wo in wo_data_dict.values():
		wo['se_details'] = {}

	se_data = get_stock_entry_data(company, work_order_names, from_date, to_date)

	for se in se_data:
		if se.work_order in wo_data_dict:
			if se.name not in wo_data_dict[se.work_order]['se_details']:
				wo_data_dict[se.work_order]['se_details'][se.name] = {
					'manufactured_qty': se.manufactured_qty,
					'posting_date': se.posting_date,
					'posting_time': se.posting_time
				}
	
	for wo_key, wo_val in wo_data_dict.items():
		if wo_key not in work_order_data:
			work_order_data[wo_key] = wo_val

	html = frappe.render_template(
		"nrp_manufacturing/templates/reports/work_order_tracking.html", 
		{
			"work_orders_data": work_order_data
			}
		)
	
	return columns, data, None, None, None, None, html


def get_work_order_data(company, from_date, to_date, item_category, work_order_status):
	wo_data = frappe.db.sql(f"""
		SELECT 
			wo.name AS work_order, 
			wo.company AS company,
			wo.item_name AS item_name, 
			wo.qty AS qty_to_manufacture, 
			wo.produced_qty AS manufactured_qty, 
			wo.creation, 
			wo.closing_date,
			wo.closed, 
			wo.production_line AS production_line,
			se.posting_date, 
			se.posting_time
		FROM 
			`tabWork Order` wo
		INNER JOIN (
			SELECT 
				se1.work_order, 
				se1.posting_date, 
				se1.posting_time, 
				se1.creation
			FROM 
				`tabStock Entry` se1
			INNER JOIN (
				SELECT 
					work_order, 
					MAX(creation) AS max_creation
				FROM 
					`tabStock Entry`
				WHERE 
					stock_entry_type = 'Material Transfer for Manufacture'
				GROUP BY 
					work_order
			) latest_se ON 
				se1.work_order = latest_se.work_order 
				AND se1.creation = latest_se.max_creation
			WHERE 
				se1.stock_entry_type = 'Material Transfer for Manufacture'
		) se ON 
			se.work_order = wo.name
		INNER JOIN 
			`tabItem` i ON i.name = wo.production_item
		WHERE 
			wo.company {company}
			AND DATE(wo.creation) >= "{from_date}"
			AND DATE(wo.creation) <= "{to_date}"
			AND i.item_category {item_category}
			AND wo.closed {work_order_status}
		ORDER BY 
			wo.item_name;""", as_dict=True)

	return wo_data

def get_stock_entry_data(company, work_orders, from_date, to_date):
	if work_orders:
		work_order_condition = 'AND se.work_order IN (' + ', '.join(f'"{w}"' for w in work_orders) + ')'

		se_data = frappe.db.sql(f"""
			SELECT 
				se.name,
				se.fg_completed_qty AS manufactured_qty,
				se.work_order, 
				se.posting_date, 
				se.posting_time
			FROM 
				`tabStock Entry` se 
			WHERE 
				se.stock_entry_type = 'Manufacture' 
				{work_order_condition};
		""", as_dict=True)

		return se_data
	else:
		return {}
