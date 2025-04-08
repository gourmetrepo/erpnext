# Copyright (c) 2013, GICOH and contributors
# For license information, please see license.txt

from __future__ import unicode_literals
import frappe

def execute(filters=None):
	from_date = filters.get("from_date")
	to_date = filters.get("to_date")
	if filters.get("company") == "ALL":
		company = "IN ('Unit 5', 'Unit 8', 'Unit 11')"
	else:
		company = f"= '{filters.get('company')}'"
	if filters.get("warehouse"):
		warehouse = 'IN (' + ', '.join(f'"{w}"' for w in filters.get('warehouse')) + ')'
	else:
		return [], []

	columns = get_columns(filters)
	
	data = frappe.db.sql(
		f"""SELECT 
				rdata.item_code AS item_code,
				icsd.item_name AS item_name,
				icsd.reporting_variant AS packs,
				icsd.reporting_flavor AS flavors,
				SUM(`stock_unit_5`) AS stock_unit_5,
				SUM(`stock_unit_8`) AS stock_unit_8,
				SUM(`stock_unit_11`) AS stock_unit_11,
				SUM(`stock_total`) AS stock_total,
				SUM(`dn_unit_5`) AS dn_unit_5,
				SUM(`dn_unit_8`) AS dn_unit_8,
				SUM(`dn_unit_11`) AS dn_unit_11,
				SUM(`dn_total`) AS dn_total,
				SUM(`pending_unit_5`) AS pending_unit_5,
				SUM(`pending_unit_8`) AS pending_unit_8,
				SUM(`pending_unit_11`) AS pending_unit_11,
				SUM(`pending_total`) AS pending_total,
				SUM(`sor_unit_5`) AS sor_unit_5,
				SUM(`sor_unit_8`) AS sor_unit_8,
				SUM(`sor_unit_11`) AS sor_unit_11,
				SUM(`sor_total`) AS sor_total,
				SUM(`stock_unit_5`)-SUM(`pending_unit_5`) AS net_stock_unit_5,
				SUM(`stock_unit_8`)-SUM(`pending_unit_8`) AS net_stock_unit_8,
				SUM(`stock_unit_11`)-SUM(`pending_unit_11`) AS net_stock_unit_11,
				SUM(`stock_total`)-SUM(`pending_total`) AS net_stock_total
			FROM
			(
				SELECT 
					sle.item_code,
					SUM(CASE
						WHEN sle.company = 'Unit 5' THEN sle.actual_qty
						ELSE 0
					END) AS `stock_unit_5`,
					SUM(CASE
						WHEN sle.company = 'Unit 8' THEN sle.actual_qty
						ELSE 0
					END) AS `stock_unit_8`,
					SUM(CASE
						WHEN sle.company = 'Unit 11' THEN sle.actual_qty
						ELSE 0
					END) AS `stock_unit_11`,
					SUM(sle.actual_qty) AS `stock_total`,
					0 AS `dn_unit_5`,
					0 AS `dn_unit_8`,
					0 AS `dn_unit_11`,
					0 AS `dn_total`,
					0 AS `pending_unit_5`,
					0 AS `pending_unit_8`,
					0 AS `pending_unit_11`,
					0 AS `pending_total`,
					0 AS `sor_unit_5`,
					0 AS `sor_unit_8`,
					0 AS `sor_unit_11`,
					0 AS `sor_total`
				FROM 
					`tabStock Ledger Entry` sle
				WHERE
					sle.posting_date <= "{to_date}"
					AND sle.company {company} 
					AND sle.warehouse {warehouse}
					AND sle.item_code NOT LIKE 'RI%'
				GROUP BY sle.item_code

				UNION ALL

				SELECT 
					dni.item_code,
					0 AS `stock_unit_5`,
					0 AS `stock_unit_8`,
					0 AS `stock_unit_11`,
					0 AS `stock_total`,
					SUM(CASE
						WHEN dn.company = 'Unit 5' THEN dni.qty
						ELSE 0
					END) AS `dn_unit_5`,
					SUM(CASE
						WHEN dn.company = 'Unit 8' THEN dni.qty
						ELSE 0
					END) AS `dn_unit_8`,
					SUM(CASE
						WHEN dn.company = 'Unit 11' THEN dni.qty
						ELSE 0
					END) AS `dn_unit_11`,
					SUM(dni.qty) AS `dn_total`,
					0 AS `pending_unit_5`,
					0 AS `pending_unit_8`,
					0 AS `pending_unit_11`,
					0 AS `pending_total`,
					0 AS `sor_unit_5`,
					0 AS `sor_unit_8`,
					0 AS `sor_unit_11`,
					0 AS `sor_total`
				FROM 
					`tabDelivery Note` AS dn
				INNER JOIN 
					`tabDelivery Note Item` dni ON dni.parent = dn.name
				WHERE 
					dn.posting_date >= "{from_date}"
					AND dn.posting_date <= "{to_date}"
					AND dn.company {company}
					AND dn.section = "FG Beverages"
					AND dn.status NOT IN ("Draft", "Cancelled")
					AND (dn.customer LIKE 'CUST-DIS%' OR dn.customer LIKE 'CUST-KA%' OR dn.customer LIKE 'CUST-USC%')
					AND dni.item_code NOT LIKE 'RI%'
				GROUP BY dni.item_code

				UNION ALL

				SELECT 
					soi.item_code,
					0 AS `stock_unit_5`,
					0 AS `stock_unit_8`,
					0 AS `stock_unit_11`,
					0 AS `stock_total`,
					0 AS `dn_unit_5`,
					0 AS `dn_unit_8`,
					0 AS `dn_unit_11`,
					0 AS `dn_total`,
					SUM(CASE
						WHEN so.company = 'Unit 5' 
						AND so.status = "To Deliver and Bill"
						AND so.section = "FG Beverages" THEN soi.qty - soi.delivered_qty
						ELSE 0
					END) AS `pending_unit_5`,
					SUM(CASE
						WHEN so.company = 'Unit 8' 
						AND so.status = "To Deliver and Bill"
						AND so.section = "FG Beverages" THEN soi.qty - soi.delivered_qty
						ELSE 0
					END) AS `pending_unit_8`,
					SUM(CASE
						WHEN so.company = 'Unit 11' 
						AND so.status = "To Deliver and Bill"
						AND so.section = "FG Beverages" THEN soi.qty - soi.delivered_qty
						ELSE 0
					END) AS `pending_unit_11`,
					SUM(soi.qty - soi.delivered_qty) AS `pending_total`,
					SUM(CASE
						WHEN so.company = 'Unit 5' 
						AND so.workflow_state != "Rejected" THEN soi.qty
						ELSE 0
					END) AS `sor_unit_5`,
					SUM(CASE
						WHEN so.company = 'Unit 8' 
						AND so.workflow_state != "Rejected" THEN soi.qty
						ELSE 0
					END) AS `sor_unit_8`,
					SUM(CASE
						WHEN so.company = 'Unit 11' 
						AND so.workflow_state != "Rejected" THEN soi.qty
						ELSE 0
					END) AS `sor_unit_11`,
					SUM(soi.qty) AS `sor_total`
				FROM 
					`tabSales Order` AS so
				INNER JOIN 
					`tabSales Order Item` soi ON soi.parent = so.name
				WHERE 
					so.transaction_date >= "{from_date}"
					AND so.transaction_date <= "{to_date}"
					AND so.company {company}
					AND (so.customer LIKE 'CUST-DIS%' OR so.customer LIKE 'CUST-KA%' OR so.customer LIKE 'CUST-USC%')
					AND soi.item_code NOT LIKE 'RI%'
				GROUP BY soi.item_code
			) AS rdata
			INNER JOIN `tabItem CSD` icsd ON icsd.name = rdata.item_code
			GROUP BY rdata.item_code;""",
		as_dict=True
	)

	data = collapsable_data(data)

	return columns, data


def collapsable_data(data):
    import copy

    final_data = []
    packs_set = set()

    for k, d in enumerate(data):
        # Check if packs are already added
        if d['packs'] not in packs_set:
            packs_set.add(d['packs'])
            packs_name = d['packs']

            # Packs row
            packs_row = copy.copy(d)
            packs_row['item_code'] = ''
            packs_row['item_name'] = ''
            packs_row['packs'] = packs_name
            packs_row['flavors'] = ''
            packs_row['stock_unit_5'] = packs_row['stock_unit_8'] = packs_row['stock_unit_11'] = packs_row['stock_total'] = 0
            packs_row['dn_unit_5'] = packs_row['dn_unit_8'] = packs_row['dn_unit_11'] = packs_row['dn_total'] = 0
            packs_row['pending_unit_5'] = packs_row['pending_unit_8'] = packs_row['pending_unit_11'] = packs_row['pending_total'] = 0
            packs_row['sor_unit_5'] = packs_row['sor_unit_8'] = packs_row['sor_unit_11'] = packs_row['sor_total'] = 0
            packs_row['net_stock_unit_5'] = packs_row['net_stock_unit_8'] = packs_row['net_stock_unit_11'] = packs_row['net_stock_total'] = 0
            packs_row['indent'] = 0

            # Flavors grouping within packs
            flavors_rows = []
            flavors_set = set()

            for _idd in data[k:]:
                if packs_name == _idd['packs']:
                    if _idd['flavors'] not in flavors_set:
                        flavors_set.add(_idd['flavors'])
                        flavors_name = _idd['flavors']

                        # Flavors row
                        flavors_row = copy.copy(_idd)
                        flavors_row['item_code'] = _idd['item_code']
                        flavors_row['item_name'] = _idd['item_name']
                        flavors_row['packs'] = ''
                        flavors_row['flavors'] = flavors_name
                        flavors_row['stock_unit_5'] = flavors_row['stock_unit_8'] = flavors_row['stock_unit_11'] = flavors_row['stock_total'] = 0
                        flavors_row['dn_unit_5'] = flavors_row['dn_unit_8'] = flavors_row['dn_unit_11'] = flavors_row['dn_total'] = 0
                        flavors_row['pending_unit_5'] = flavors_row['pending_unit_8'] = flavors_row['pending_unit_11'] = flavors_row['pending_total'] = 0
                        flavors_row['sor_unit_5'] = flavors_row['sor_unit_8'] = flavors_row['sor_unit_11'] = flavors_row['sor_total'] = 0
                        flavors_row['net_stock_unit_5'] = flavors_row['net_stock_unit_8'] = flavors_row['net_stock_unit_11'] = flavors_row['net_stock_total'] = 0
                        flavors_row['indent'] = 1

                        # Add the actual data rows to the flavors row
                        for item in data[k:]:
                            if item['packs'] == packs_name and item['flavors'] == flavors_name:
                                flavors_row['stock_unit_5'] += item['stock_unit_5']
                                flavors_row['stock_unit_8'] += item['stock_unit_8']
                                flavors_row['stock_unit_11'] += item['stock_unit_11']
                                flavors_row['stock_total'] += item['stock_total']
                                flavors_row['dn_unit_5'] += item['dn_unit_5']
                                flavors_row['dn_unit_8'] += item['dn_unit_8']
                                flavors_row['dn_unit_11'] += item['dn_unit_11']
                                flavors_row['dn_total'] += item['dn_total']
                                flavors_row['pending_unit_5'] += item['pending_unit_5']
                                flavors_row['pending_unit_8'] += item['pending_unit_8']
                                flavors_row['pending_unit_11'] += item['pending_unit_11']
                                flavors_row['pending_total'] += item['pending_total']
                                flavors_row['sor_unit_5'] += item['sor_unit_5']
                                flavors_row['sor_unit_8'] += item['sor_unit_8']
                                flavors_row['sor_unit_11'] += item['sor_unit_11']
                                flavors_row['sor_total'] += item['sor_total']
                                flavors_row['net_stock_unit_5'] += item['net_stock_unit_5']
                                flavors_row['net_stock_unit_8'] += item['net_stock_unit_8']
                                flavors_row['net_stock_unit_11'] += item['net_stock_unit_11']
                                flavors_row['net_stock_total'] += item['net_stock_total']

                        flavors_rows.append(flavors_row)

            # Calculate totals for packs
            for flavors_row in flavors_rows:
                packs_row['stock_unit_5'] += flavors_row['stock_unit_5']
                packs_row['stock_unit_8'] += flavors_row['stock_unit_8']
                packs_row['stock_unit_11'] += flavors_row['stock_unit_11']
                packs_row['stock_total'] += flavors_row['stock_total']
                packs_row['dn_unit_5'] += flavors_row['dn_unit_5']
                packs_row['dn_unit_8'] += flavors_row['dn_unit_8']
                packs_row['dn_unit_11'] += flavors_row['dn_unit_11']
                packs_row['dn_total'] += flavors_row['dn_total']
                packs_row['pending_unit_5'] += flavors_row['pending_unit_5']
                packs_row['pending_unit_8'] += flavors_row['pending_unit_8']
                packs_row['pending_unit_11'] += flavors_row['pending_unit_11']
                packs_row['pending_total'] += flavors_row['pending_total']
                packs_row['sor_unit_5'] += flavors_row['sor_unit_5']
                packs_row['sor_unit_8'] += flavors_row['sor_unit_8']
                packs_row['sor_unit_11'] += flavors_row['sor_unit_11']
                packs_row['sor_total'] += flavors_row['sor_total']
                packs_row['net_stock_unit_5'] += flavors_row['net_stock_unit_5']
                packs_row['net_stock_unit_8'] += flavors_row['net_stock_unit_8']
                packs_row['net_stock_unit_11'] += flavors_row['net_stock_unit_11']
                packs_row['net_stock_total'] += flavors_row['net_stock_total']

            # Append packs row and its corresponding flavors rows
            final_data.append(packs_row)
            final_data.extend(flavors_rows)

    return final_data


def get_columns(filters):
	columns = [
		{
			"label": "Packs",
			"fieldname": "packs",
			"fieldtype": "Data",
			"width": 200,
		},
		{
			"label": "Flavors",
			"fieldname": "flavors",
			"fieldtype": "Data",
			"width": 200,
		},
		{
			"label": "Item Code",
			"fieldname": "item_code",
			"fieldtype": "Data",
			"width": 150,
		},
		{
			"label": "Item Name",
			"fieldname": "item_name",
			"fieldtype": "Data",
			"width": 150,
		},
		{
			"label": "Stock Unit 5",
			"fieldname": "stock_unit_5",
			"fieldtype": "Float",
			"precision": "0",
			"width": 100,
		},
		{
			"label": "Pending Unit 5",
			"fieldname": "pending_unit_5",
			"fieldtype": "Float",
			"precision": "0",
			"width": 100,
		},
		{
			"label": "Net Stock Unit 5",
			"fieldname": "net_stock_unit_5",
			"fieldtype": "Float",
			"precision": "0",
			"width": 100,
		},
		{
			"label": "Stock Unit 8",
			"fieldname": "stock_unit_8",
			"fieldtype": "Float",
			"precision": "0",
			"width": 100,
		},
		{
			"label": "Pending Unit 8",
			"fieldname": "pending_unit_8",
			"fieldtype": "Float",
			"precision": "0",
			"width": 100,
		},
		{
			"label": "Net Stock Unit 8",
			"fieldname": "net_stock_unit_8",
			"fieldtype": "Float",
			"precision": "0",
			"width": 100,
		},
		{
			"label": "Stock Unit 11",
			"fieldname": "stock_unit_11",
			"fieldtype": "Float",
			"precision": "0",
			"width": 100,
		},
		{
			"label": "Pending Unit 11",
			"fieldname": "pending_unit_11",
			"fieldtype": "Float",
			"precision": "0",
			"width": 100,
		},
		{
			"label": "Net Stock Unit 11",
			"fieldname": "net_stock_unit_11",
			"fieldtype": "Float",
			"precision": "0",
			"width": 100,
		},
		{
			"label": "Stock Total",
			"fieldname": "stock_total",
			"fieldtype": "Float",
			"precision": "0",
			"width": 100,
		},
		{
			"label": "Pending Total",
			"fieldname": "pending_total",
			"fieldtype": "Float",
			"precision": "0",
			"width": 100,
		},
		{
			"label": "Net Stock Total",
			"fieldname": "net_stock_total",
			"fieldtype": "Float",
			"precision": "0",
			"width": 100,
		},
		{
			"label": "DN Unit 5",
			"fieldname": "dn_unit_5",
			"fieldtype": "Float",
			"precision": "0",
			"width": 100,
		},
		{
			"label": "DN Unit 8",
			"fieldname": "dn_unit_8",
			"fieldtype": "Float",
			"precision": "0",
			"width": 100,
		},
		{
			"label": "DN Unit 11",
			"fieldname": "dn_unit_11",
			"fieldtype": "Float",
			"precision": "0",
			"width": 100,
		},
		{
			"label": "DN Total",
			"fieldname": "dn_total",
			"fieldtype": "Float",
			"precision": "0",
			"width": 100,
		},
		{
			"label": "SOR Unit 5",
			"fieldname": "sor_unit_5",
			"fieldtype": "Float",
			"precision": "0",
			"width": 100,
		},
		{
			"label": "SOR Unit 8",
			"fieldname": "sor_unit_8",
			"fieldtype": "Float",
			"precision": "0",
			"width": 100,
		},
		{
			"label": "SOR Unit 11",
			"fieldname": "sor_unit_11",
			"fieldtype": "Float",
			"precision": "0",
			"width": 100,
		},
		{
			"label": "SOR Total",
			"fieldname": "sor_total",
			"fieldtype": "Float",
			"precision": "0",
			"width": 100,
		}
	]

	company = filters.get('company')
	if company == "ALL":
		return columns
	else:
		cols = []
		company_number = company.split(' ')[1]

		for col in columns:
			if 'stock_unit_' in col['fieldname'] or 'pending_unit_' in col['fieldname'] or 'net_stock_unit_' in col['fieldname'] or 'dn_unit_' in col['fieldname'] or 'sor_unit_' in col['fieldname']:
				if col['fieldname'] in [f'stock_unit_{company_number}', f'pending_unit_{company_number}', f'net_stock_unit_{company_number}', f'dn_unit_{company_number}', f'sor_unit_{company_number}']:
					cols.append(col)
			else:
				cols.append(col)
		return cols
