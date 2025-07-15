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
		company = f"""= and  m.company='{filters.get('company')}'"""
	data = []
	data = frappe.db.sql(
                f"""SELECT * FROM (SELECT pmodiffstock.*,gl.account,SUM(credit-debit) AS balance FROM (SELECT PMOdiff.*,ROUND(SUM(`actual_qty`*sle.`valuation_rate`)) AS stockvalue FROM `tabStock Ledger Entry` AS sle
INNER JOIN `tabBatch` AS btch ON btch.`batch_id` = sle.`batch_no` AND btch.`supplier` IS NOT NULL 
INNER JOIN (
SELECT m.posting_date,CONCAT(
        TIMESTAMPDIFF(MONTH, m.posting_date, CURDATE()), 'M-',
        DATEDIFF(CURDATE(), m.posting_date) % 30, 'D'
    )  AS day_diff,m.company,d.parent as ref_doc,d.`supplier`,d.`supplier_name`,ROUND(d.`amount`) AS amount,ROUND(d.`amount_paid`) AS amount_paid FROM `tabPayment Order Detail` AS d
INNER JOIN `tabPayment Order` AS m ON m.name = d.parent 
 WHERE d.amount_paid!=d.amount AND m.docstatus=1  {company} 
 GROUP BY m.posting_date,m.company,d.`supplier`
 ) AS PMOdiff ON PMOdiff.supplier = btch.`supplier` AND PMOdiff.company = btch.`company`
 GROUP BY PMOdiff.supplier,PMOdiff.company ) AS pmodiffstock
 INNER JOIN `tabGL Entry` AS gl ON gl.`party` = pmodiffstock.supplier  AND pmodiffstock.company = gl.`company`
  INNER JOIN `tabAccount` ON `tabAccount`.`name` = gl.account AND account_type IN ('Payable','Receivable')
 GROUP BY gl.account,pmodiffstock.supplier,pmodiffstock.company
 UNION ALL 
 SELECT pmodiffstock.*,gl.account,SUM(credit-debit) AS balance FROM (SELECT expdiff.*,ROUND(SUM(`actual_qty`*sle.`valuation_rate`)) AS stockvalue FROM `tabStock Ledger Entry` AS sle
INNER JOIN `tabBatch` AS btch ON btch.`batch_id` = sle.`batch_no` AND btch.`supplier` IS NOT NULL 
INNER JOIN (
SELECT m.posting_date,CONCAT(
        TIMESTAMPDIFF(MONTH, m.posting_date, CURDATE()), 'M-',
        DATEDIFF(CURDATE(), m.posting_date) % 30, 'D'
    )  AS day_diff,m.company,d.parent as ref_doc,d.`party`AS supplier,sup.`supplier_name` AS supplier_name,ROUND(d.`amount`) AS amount, 0 AS amount_paid FROM `tabExpense Entry Item` AS d
INNER JOIN `tabExpense Entry` AS m ON m.name = d.parent 
 INNER JOIN `tabSupplier` sup ON sup.name =  d.`party` 
 WHERE  m.docstatus!=1 AND m.`management_approval_date` IS NOT NULL {company} 
 GROUP BY m.posting_date,m.company,d.`party`
 ) AS expdiff 
 ON expdiff.supplier = btch.`supplier` AND expdiff.company = btch.`company`
 GROUP BY expdiff.supplier,expdiff.company ) AS pmodiffstock
 INNER JOIN `tabGL Entry` AS gl ON gl.`party` = pmodiffstock.supplier  AND pmodiffstock.company = gl.`company`
  INNER JOIN `tabAccount` ON `tabAccount`.`name` = gl.account AND account_type IN ('Payable','Receivable')
 GROUP BY gl.account,pmodiffstock.supplier,pmodiffstock.company
 ) AS datanotpaid 
 ORDER BY day_diff DESC""",as_dict=True)
	columns = get_columns(filters)
	
	return columns, data

def get_columns(filters):
    """return columns based on filters"""

    columns = (
        [_("posting Date") + "::200"]
        + [_("Day Diff") + "::120"]
        + [_("Company") + "::120"]
        + [_("Ref Doc") + "::120"]
        + [_("Supplier") + "::120"]
        + [_("Supplier Name") + "::120"]
        + [_("amount") + "::120"]
        + [_("amount_paid") + "::120"]
        + [_("stockvalue") + "::120"]
        + [_("Account") + "::120"]
        + [_("Balance") + "::120"]
    )

    return columns