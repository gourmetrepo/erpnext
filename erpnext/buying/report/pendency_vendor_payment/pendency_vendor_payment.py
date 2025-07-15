# Copyright (c) 2013, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

from __future__ import unicode_literals
import frappe

def execute(filters=None):
	columns, data = [], []

	if not filters:
		filters = {}

	if filters.get("company") == "ALL":
		company = f" and m.company IN ('Unit 5', 'Unit 8', 'Unit 11')"
	else:
		company = f""" and  m.company='{filters.get('company')}'"""
	
	data = []
	data = frappe.db.sql(f"""
    SELECT * FROM (
        SELECT 
            pmodiffstock.*,
            IFNULL( ROUND(SUM(gl.credit - gl.debit)), 0) AS gl_balance


        FROM (
            SELECT 
                PMOdiff.posting_date,
                PMOdiff.day_diff,
                PMOdiff.company,
                PMOdiff.ref_doc,
                PMOdiff.supplier,
                PMOdiff.supplier_name,
                PMOdiff.amount,
                PMOdiff.amount_paid,
                ROUND(SUM(IFNULL(sle.actual_qty * sle.valuation_rate, 0))) AS stockvalue

            FROM (
                SELECT 
                    m.posting_date,
                    CONCAT(
                        TIMESTAMPDIFF(MONTH, m.posting_date, CURDATE()), 'M-',
                        DATEDIFF(CURDATE(), m.posting_date) % 30, 'D'
                    ) AS day_diff,
                    m.company,
                    d.parent AS ref_doc,
                    d.supplier,
                    d.supplier_name,
                    ROUND(d.amount) AS amount,
                    ROUND(d.amount_paid) AS amount_paid

                FROM `tabPayment Order Detail` AS d
                INNER JOIN `tabPayment Order` AS m ON m.name = d.parent
                WHERE 
                    d.amount_paid != d.amount
                    AND m.docstatus = 1
                    {company}

                GROUP BY m.posting_date, m.company, d.supplier
            ) AS PMOdiff

            LEFT JOIN `tabBatch` AS btch 
                ON PMOdiff.supplier = btch.supplier AND PMOdiff.company = btch.company

            LEFT JOIN `tabStock Ledger Entry` AS sle 
                ON btch.batch_id = sle.batch_no

            GROUP BY PMOdiff.supplier, PMOdiff.company
        ) AS pmodiffstock

        LEFT JOIN `tabGL Entry` AS gl 
            ON gl.party = pmodiffstock.supplier AND pmodiffstock.company = gl.company

        LEFT JOIN `tabAccount` AS acc 
            ON acc.name = gl.account AND acc.account_type IN ('Payable', 'Receivable')

        GROUP BY pmodiffstock.supplier, pmodiffstock.company

        UNION ALL
        SELECT 
            expdiffstock.*,
           IFNULL( ROUND(SUM(gl.credit - gl.debit)), 0) AS gl_balance


        FROM (
            SELECT 
                expdiff.posting_date,
                expdiff.day_diff,
                expdiff.company,
                expdiff.ref_doc,
                expdiff.supplier,
                expdiff.supplier_name,
                expdiff.amount,
                expdiff.amount_paid,
                ROUND(SUM(IFNULL(sle.actual_qty * sle.valuation_rate, 0))) AS stockvalue

            FROM (
                SELECT 
                    m.posting_date,
                    CONCAT(
                        TIMESTAMPDIFF(MONTH, m.posting_date, CURDATE()), 'M-',
                        DATEDIFF(CURDATE(), m.posting_date) % 30, 'D'
                    ) AS day_diff,
                    m.company,
                    d.parent AS ref_doc,
                    d.party AS supplier,
                    sup.supplier_name AS supplier_name,
                    ROUND(d.amount) AS amount,
                    0 AS amount_paid

                FROM `tabExpense Entry Item` AS d
                INNER JOIN `tabExpense Entry` AS m ON m.name = d.parent
                INNER JOIN `tabSupplier` AS sup ON sup.name = d.party

                WHERE 
                    m.docstatus != 1
                    AND m.management_approval_date IS NOT NULL
                    {company}

                GROUP BY m.posting_date, m.company, d.party
            ) AS expdiff

            LEFT JOIN `tabBatch` AS btch 
                ON expdiff.supplier = btch.supplier AND expdiff.company = btch.company

            LEFT JOIN `tabStock Ledger Entry` AS sle 
                ON btch.batch_id = sle.batch_no

            GROUP BY expdiff.supplier, expdiff.company
        ) AS expdiffstock

        LEFT JOIN `tabGL Entry` AS gl 
            ON gl.party = expdiffstock.supplier AND expdiffstock.company = gl.company

        LEFT JOIN `tabAccount` AS acc 
            ON acc.name = gl.account AND acc.account_type IN ('Payable', 'Receivable')

        GROUP BY gl.account, expdiffstock.supplier, expdiffstock.company

    ) AS datanotpaid

    ORDER BY day_diff DESC""", as_dict=True)

	columns = get_columns(filters)
	
	return columns, data

def get_columns(filters):
		"""return columns based on filters"""
		
		columns = [
		
			{"label": "Posting Date", "fieldname": "posting_date", "fieldtype": "Date",  "width": 120},
			{"label": "Day Diff", "fieldname": "day_diff", "fieldtype": "Data",  "width": 120},
			{"label": "Ref Doc", "fieldname": "ref_doc", "fieldtype": "Data", "width": 120},
			{"label": "Supplier", "fieldname": "Supplier", "fieldtype": "Data",  "width": 120},
			{"label": "Supplier Name", "fieldname": "supplier_name", "fieldtype": "Data", "precision":"0", "align": "right", "width": 320},
			{"label": "Amount", "fieldname": "amount", "fieldtype": "Currency", "precision":"0", "align": "right", "width": 120},
			{"label": "Amount Paid", "fieldname": "amount_paid", "fieldtype": "Currency", "precision":"0", "align": "right", "width": 120},
			{"label": "Stock Value", "fieldname": "stock_value", "fieldtype": "Currency", "precision":"0", "align": "right", "width": 120},
			{"label": "GL Balance", "fieldname": "gl_balance", "fieldtype": "Currency", "precision":"0", "align": "right", "width": 120}
		]
	

		return columns