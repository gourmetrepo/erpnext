# Copyright (c) 2013, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt


from __future__ import unicode_literals
import frappe

def execute(filters=None):
	from_date = filters.get('from_date')
	company = filters.get('company')
	columns = [
		("Shop Name") + "::120",
		("Section") + "::120",
		("Order Count") + "::100",
		("Sales Order") + "::500",
		
    ]
	data = frappe.db.sql(f"""SELECT 
    soi.customer_name as `shop_name`,
    soi.item_section as `section`,
    COUNT(DISTINCT soi.parent) AS order_count,
    GROUP_CONCAT(DISTINCT soi.parent) AS sales_order
FROM (
    SELECT 
        so.name AS parent,
        so.customer_name,
        soi.item_section
    FROM 
        `tabSales Order` so
    JOIN 
        `tabSales Order Item` soi ON so.name = soi.parent
    WHERE 
        so.transaction_date = '{from_date}'
        AND so.company = '{company}'
		AND so.request_from ='RMS'
) AS soi
GROUP BY 
    soi.customer_name, soi.item_section
HAVING 
    COUNT(DISTINCT soi.parent) > 1
ORDER BY 
    soi.customer_name, soi.item_section;
""".format(from_date=from_date, company=company), as_dict=True,debug=True)
	data = []
	columns, data = [], []
	return columns, data
