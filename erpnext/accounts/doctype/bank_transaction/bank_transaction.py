# -*- coding: utf-8 -*-
# Copyright (c) 2019, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

from __future__ import unicode_literals
import frappe
import csv
from erpnext.controllers.status_updater import StatusUpdater
from frappe.utils import flt
from six.moves import reduce
from frappe import throw, _
from datetime import datetime

class BankTransaction(StatusUpdater):
	def after_insert(self):
		self.unallocated_amount = abs(flt(self.credit) - flt(self.debit))

	def on_submit(self):
		self.clear_linked_payment_entries()
		self.set_status()

	def on_update_after_submit(self):
		self.validate_amount()
		self.update_allocations()
		self.clear_linked_payment_entries()
		self.set_status(update=True)
		self.set_br_amount()

	def update_allocations(self):
		if self.payment_entries:
			allocated_amount = reduce(lambda x, y: flt(x) + flt(y), [x.allocated_amount for x in self.payment_entries])
		else:
			allocated_amount = 0

		if allocated_amount:
			frappe.db.set_value(self.doctype, self.name, "allocated_amount", flt(allocated_amount))
			frappe.db.set_value(self.doctype, self.name, "unallocated_amount", abs(flt(self.credit) - flt(self.debit)) - flt(allocated_amount))

		else:
			frappe.db.set_value(self.doctype, self.name, "allocated_amount", 0)
			frappe.db.set_value(self.doctype, self.name, "unallocated_amount", abs(flt(self.credit) - flt(self.debit)))

		amount = self.debit or self.credit
		if amount == self.allocated_amount:
			frappe.db.set_value(self.doctype, self.name, "status", "Reconciled")

		self.reload()

	def clear_linked_payment_entries(self):
		for payment_entry in self.payment_entries:
			allocated_amount = get_total_allocated_amount(payment_entry)
			paid_amount = get_paid_amount(payment_entry, self.currency)

			if paid_amount and allocated_amount:
				if  flt(allocated_amount[0]["allocated_amount"]) > flt(paid_amount):
					frappe.throw(_("The total allocated amount ({0}) is greated than the paid amount ({1}).".format(flt(allocated_amount[0]["allocated_amount"]), flt(paid_amount))))
				else:
					if payment_entry.payment_document in ["Payment Entry", "Journal Entry", "Purchase Invoice", "Expense Claim"]:
						self.clear_simple_entry(payment_entry)

					elif payment_entry.payment_document == "Sales Invoice":
						self.clear_sales_invoice(payment_entry)

	def clear_simple_entry(self, payment_entry):
		frappe.db.set_value(payment_entry.payment_document, payment_entry.payment_entry, "clearance_date", self.date)

	def clear_sales_invoice(self, payment_entry):
		frappe.db.set_value("Sales Invoice Payment", dict(parenttype=payment_entry.payment_document,
			parent=payment_entry.payment_entry), "clearance_date", self.date)
	
	def set_br_amount(self):
		if self.payment_entries:
			if self.docstatus == 2:
				for pe in self.payment_entries:
					frappe.db.set_value("GL Entry", pe.payment_entry, "br_amount", 0)
			else:
				for pe in self.payment_entries:
					if pe.allocated_amount > 0:
						br_amount = flt(pe.allocated_amount) + flt(pe.gl_br_amount)
						frappe.db.set_value("GL Entry", pe.payment_entry, "br_amount", br_amount)

	def validate_amount(self):
		total_amount = 0
		for pe in self.payment_entries:
			total_amount += pe.allocated_amount
			if pe.allocated_amount + pe.gl_br_amount > pe.gl_amount:
				frappe.throw(_(f"BR amount not matching against {pe.voucher_no}"))

		if total_amount > self.unallocated_amount:
			frappe.throw(_(f"Total BR amount {total_amount} is greater than unallocated amount {self.unallocated_amount}"))

	def on_cancel(self):
		self.set_br_amount()


def get_total_allocated_amount(payment_entry):
	return frappe.db.sql("""
		SELECT
			SUM(btp.allocated_amount) as allocated_amount,
			bt.name
		FROM
			`tabBank Transaction Payments` as btp
		LEFT JOIN
			`tabBank Transaction` bt ON bt.name=btp.parent
		WHERE
			btp.payment_document = %s
		AND
			btp.payment_entry = %s
		AND
			bt.docstatus = 1""", (payment_entry.payment_document, payment_entry.payment_entry), as_dict=True)

def get_paid_amount(payment_entry, currency):
	if payment_entry.payment_document in ["Payment Entry", "Sales Invoice", "Purchase Invoice"]:

		paid_amount_field = "paid_amount"
		if payment_entry.payment_document == 'Payment Entry':
			doc = frappe.get_doc("Payment Entry", payment_entry.payment_entry)
			paid_amount_field = ("base_paid_amount"
				if doc.paid_to_account_currency == currency else "paid_amount")

		return frappe.db.get_value(payment_entry.payment_document,
			payment_entry.payment_entry, paid_amount_field)

	elif payment_entry.payment_document == "Journal Entry":
		return frappe.db.get_value(payment_entry.payment_document, payment_entry.payment_entry, "total_credit")

	elif payment_entry.payment_document == "Expense Claim":
		return frappe.db.get_value(payment_entry.payment_document, payment_entry.payment_entry, "total_amount_reimbursed")
	elif payment_entry.payment_document == "GL Entry":
		gl_value = frappe.db.get_value(payment_entry.payment_document, payment_entry.payment_entry, ["credit", "debit"], as_dict=True)
		if gl_value:
			if gl_value.get("credit", 0) > 0:
				return gl_value.get("credit")
			else:
				return gl_value.get("debit")
	else:
		frappe.throw("Please reconcile {0}: {1} manually".format(payment_entry.payment_document, payment_entry.payment_entry))

@frappe.whitelist()
def unclear_reference_payment(doctype, docname):
	if frappe.db.exists(doctype, docname):
		doc = frappe.get_doc(doctype, docname)
		if doctype == "Sales Invoice":
			frappe.db.set_value("Sales Invoice Payment", dict(parenttype=doc.payment_document,
				parent=doc.payment_entry), "clearance_date", None)
		elif doctype == "GL Entry":
			frappe.db.set_value(doc.payment_document, doc.payment_entry, "br_amount", 0)
		else:
			frappe.db.set_value(doc.payment_document, doc.payment_entry, "clearance_date", None)

		return doc.payment_entry


@frappe.whitelist()
def get_payment_documents(doctype, txt, searchfield, start, page_len, filters):
	select_condition = "name, voucher_no"
	conditions = []

	if not filters.get("account") or not filters.get("type"):
		return []

	conditions.append(f"account = {frappe.db.escape(filters.get('account'))}")

	if not filters.get("type"):
		return []
	elif filters.get("type") == "Pay":
		conditions.append("credit > 0")
		select_condition += ", credit"
	elif filters.get("type") == "Receive":
		conditions.append("debit > 0")
		select_condition += ", debit"

	# Required for search to work
	if txt:
		conditions.append(f"(name LIKE {frappe.db.escape('%' + txt + '%')} OR voucher_no LIKE {frappe.db.escape('%' + txt + '%')} OR credit LIKE {frappe.db.escape('%' + txt + '%')} OR debit LIKE {frappe.db.escape('%' + txt + '%')})")

	where_clause = " AND ".join(conditions)

	return frappe.db.sql(f"""
		SELECT
			{select_condition}
		FROM
			`tab{doctype}`
		WHERE
			voucher_type IN ('Payment Entry', 'Journal Entry')
			AND br_amount < debit + credit
			AND {where_clause}
		ORDER BY name DESC;""")


@frappe.whitelist()
def create_doc_from_import(file_url):
	try:
		companies = []
		accounts = []
		file_doc = frappe.get_doc("File", {"file_url": file_url})
		filename = file_doc.get_full_path()

		# Check for mandatory columns
		mandatory_columns = ['Company', 'Account', 'Credit', 'Debit', 'Date', 'Description', 'Reference Number']
		file_data = csv_to_dict(filename, mandatory_columns)
		
		# Check for empty values
		for counter, fd in enumerate(file_data):
			for k, v in fd.items():
				if k == 'Company':
					companies.append(v)
				elif k == 'Account':
					accounts.append(v)
				elif k == 'Credit' or k == 'Debit':
					if float(v) < 0.0:
						frappe.throw(f"Value for '{k}' at row: {counter} must be greater than 0")	
				if not v:
					frappe.throw(f"No value found in: {k} at row: {counter}")

		# Check given Companies exists
		companies = list(set(companies))
		comps = frappe.db.get_list('Company',
			{"name": ["in", companies]}, ['name'])

		res_comps = []    
		for c in comps:
			if c.get("name"):
				res_comps.append(c.get("name"))
		
		res_company = list(set(companies) - set(res_comps))

		if res_company:
			frappe.throw(f"Company do not exist: {', '.join(res_company)}")

		# Check given Accounts exists
		accounts = list(set(accounts))
		accs = frappe.db.get_list('Account',
			{"name": ["in", accounts]}, ['name'])

		accts = []    
		for a in accs:
			if a.get("name"):
				accts.append(a.get("name"))

		res_accs = list(set(accounts) - set(accts))

		if res_accs:
			frappe.throw(f"Accounts do not exist: {', '.join(res_accs)}")

		for data in file_data:
			date_object = datetime.strptime(data.get("Date", ""), '%d/%m/%Y')

			# Convert to desired date format
			date = date_object.strftime('%Y-%m-%d')

			as_payload = {
				"doctype": "Bank Transaction",
				"company": data.get("Company", ""),
				"bank_account": data.get("Account", ""),
				"credit": float(data.get("Credit", "")),
				"debit": float(data.get("Debit", "")),
				"date": date
			}

			frappe.enqueue("erpnext.accounts.doctype.bank_transaction.bank_transaction.create_bank_transaction", queue='long', payload=as_payload)
		
		return {"success": "File uploaded successfully. Data is queued."}
	except Exception as error:
		frappe.db.rollback()
		traceback = frappe.get_traceback()
		frappe.log_error(message=f"Error: {error} \n Traceback: {traceback}", title="Bank Transaction from Import Data Button")
		return {"error": f"Error while uploading files. {error}"}


def csv_to_dict(csv_file_path, mandatory_columns):
	with open(csv_file_path, 'r', encoding='utf-8-sig') as file:
		csv_reader = csv.DictReader(file)
		
		# Check for mandatory cols
		missing_columns = [col for col in mandatory_columns if col not in csv_reader.fieldnames]
		if missing_columns:
			frappe.throw(f"Missing mandatory columns: {', '.join(missing_columns)}")

		# Convert data to dict
		dict_list = [row for row in csv_reader]
		dict_data = [dict(dl) for dl in dict_list]

	return dict_data


@frappe.whitelist()
def create_bank_transaction(payload):
	try:
		bank_transaction = frappe.get_doc(payload)
		bank_transaction.save(ignore_permissions=True)
	except Exception as error:
		traceback = frappe.get_traceback()
		frappe.log_error(message=f"Error: {error} \n Traceback: {traceback}", title="Create Bank Transaction from queue")
