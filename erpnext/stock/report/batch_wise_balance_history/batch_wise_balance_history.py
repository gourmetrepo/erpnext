# Copyright (c) 2015, Frappe Technologies Pvt. Ltd. and Contributors
# License: GNU General Public License v3. See license.txt

from __future__ import unicode_literals
import frappe
from frappe import _
from frappe.utils import flt, cint, getdate

def execute(filters=None):
	if not filters: filters = {}

	if filters.from_date > filters.to_date:
		frappe.throw(_("From Date must be before To Date"))

	float_precision = cint(frappe.db.get_default("float_precision")) or 3

	columns = get_columns(filters)
	item_map = get_item_details(filters)
	iwb_map = get_item_warehouse_batch_map(filters, float_precision)

	data = []
	for item in sorted(iwb_map):
		for wh in sorted(iwb_map[item]):
			for batch in sorted(iwb_map[item][wh]):
				qty_dict = iwb_map[item][wh][batch]
				if qty_dict.opening_qty or qty_dict.in_qty or qty_dict.out_qty or qty_dict.bal_qty:
					data.append([qty_dict.supplier_name,qty_dict.supplier_group,item, item_map[item]["item_name"], item_map[item]["description"], wh, batch,qty_dict.expiry_date,flt(qty_dict.incoming_rate),flt(qty_dict.outgoing_rate),flt(qty_dict.valuation_rate),
						flt(qty_dict.opening_qty, float_precision), flt(qty_dict.in_qty, float_precision),
						flt(qty_dict.out_qty, float_precision), flt(qty_dict.bal_qty, float_precision),
						 item_map[item]["stock_uom"]
					])

	return columns, data

def get_columns(filters):
	"""return columns based on filters"""

	columns = [_("Supplier") + ":Link/Supplier:100"] +[_("Supplier Group") + ":Link/Supplier Group:100"] +[_("Item") + ":Link/Item:100"] + [_("Item Name") + "::150"] + [_("Description") + "::150"] + \
	[_("Warehouse") + ":Link/Warehouse:100"] + [_("Batch") + ":Link/Batch:100"] + [_("Expiry Date") + "::150"] + [_("Incoming Rate") + ":Float:120"]+ [_("Outgoing Rate") + ":Float:120"]+ [_("Valuation Rate") + ":Float:120"] + [_("Opening Qty") + ":Float:120"] + \
	[_("In Qty") + ":Float:80"] + [_("Out Qty") + ":Float:80"] + [_("Balance Qty") + ":Float:90"] + \
	[_("UOM") + "::90"]


	return columns

def get_conditions(filters):
	conditions = ""
	if not filters.get("from_date"):
		frappe.throw(_("'From Date' is required"))

	if filters.get("to_date"):
		conditions += " and sle.posting_date <= '%s'" % filters["to_date"]
	else:
		frappe.throw(_("'To Date' is required"))

	for field in ["item_code", "warehouse", "batch_no", "company"]:
		if filters.get(field):
			conditions += " and sle.{0} = {1}".format(field, frappe.db.escape(filters.get(field)))

	if filters.get("supplier"):
		conditions += " and s.name = '%s'" % filters["supplier"]

	if filters.get("supplier_group"):
		conditions += " and s.supplier_group = '%s'" % filters["supplier_group"]

	return conditions

#get all details
def get_stock_ledger_entries(filters):
	conditions = get_conditions(filters)
	return frappe.db.sql("""
		select s.supplier_name,s.supplier_group,sle.item_code, sle.valuation_rate,sle.batch_no, 
					  IF(pri.expiry_date IS NOT NULL, 
        CONCAT(
            TIMESTAMPDIFF(MONTH, pri.expiry_date, CURDATE()), ' M, ', 
            DATEDIFF(CURDATE(), DATE_ADD(pri.expiry_date, INTERVAL TIMESTAMPDIFF(MONTH, pri.expiry_date, CURDATE()) MONTH)), ' D'
        ), 
        'No Expiry Date'
    ) AS expiry_date,sle.outgoing_rate,sle.incoming_rate, sle.warehouse, sle.posting_date, sum(sle.actual_qty) as actual_qty
		from `tabStock Ledger Entry` as sle
		INNER JOIN `tabBatch` as b ON b.name = sle.batch_no
		LEFT JOIN `tabSupplier` as s on s.name = b.supplier
		LEFT JOIN `tabPurchase Receipt Item` as pri on pri.parent = sle.voucher_no and pri.item_code = sle.item_code and pri.batch_no = sle.batch_no and sle.voucher_type='Purchase Receipt'
		where sle.docstatus != 2  %s
		group by sle.voucher_no, sle.batch_no, sle.item_code, sle.warehouse
		order by sle.item_code, sle.warehouse""" %
		conditions, as_dict=1,debug=True)

def get_item_warehouse_batch_map(filters, float_precision):
	sle = get_stock_ledger_entries(filters)
	iwb_map = {}

	from_date = getdate(filters["from_date"])
	to_date = getdate(filters["to_date"])

	for d in sle:
		iwb_map.setdefault(d.item_code, {}).setdefault(d.warehouse, {})\
			.setdefault(d.batch_no, frappe._dict({
				"opening_qty": 0.0, "in_qty": 0.0, "out_qty": 0.0, "bal_qty": 0.0, "incoming_rate": 0.0, "outgoing_rate": 0.0, "valuation_rate": 0.0,"supplier_name":d.supplier_name,"supplier_group": d.supplier_group,"expiry_date":d.expiry_date
			}))
		qty_dict = iwb_map[d.item_code][d.warehouse][d.batch_no]
		if d.posting_date < from_date:
			qty_dict.opening_qty = flt(qty_dict.opening_qty, float_precision) \
				+ flt(d.actual_qty, float_precision)
		elif d.posting_date >= from_date and d.posting_date <= to_date:
			if flt(d.actual_qty) > 0:
				qty_dict.in_qty = flt(qty_dict.in_qty, float_precision) + flt(d.actual_qty, float_precision)
			else:
				qty_dict.out_qty = flt(qty_dict.out_qty, float_precision) \
					+ abs(flt(d.actual_qty, float_precision))

		qty_dict.bal_qty = flt(qty_dict.bal_qty, float_precision) + flt(d.actual_qty, float_precision)
		qty_dict.incoming_rate = flt(d.incoming_rate)
		qty_dict.outgoing_rate = flt(d.outgoing_rate)
		qty_dict.valuation_rate = flt(d.valuation_rate)

	return iwb_map

def get_item_details(filters):
	item_map = {}
	for d in frappe.db.sql("select name, item_name, description, stock_uom from tabItem", as_dict=1):
		item_map.setdefault(d.name, d)

	return item_map
