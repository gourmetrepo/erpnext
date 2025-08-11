# -*- coding: utf-8 -*-
# Copyright (c) 2015, Frappe Technologies Pvt. Ltd. and Contributors
# License: GNU General Public License v3. See license.txt

from __future__ import unicode_literals

import frappe, erpnext
import frappe.defaults
from frappe.utils import nowdate, cstr, flt, cint, now, getdate
from frappe import throw, _
from frappe.utils import formatdate, get_number_format_info
from six import iteritems
# imported to enable erpnext.accounts.utils.get_account_currency
from erpnext.accounts.doctype.account.account import get_account_currency

from erpnext.stock.utils import get_stock_value_on
from erpnext.stock import get_warehouse_account_map
from frappe.utils import nowdate
from nrp_manufacturing.utils import get_config_by_name


class FiscalYearError(frappe.ValidationError): pass

@frappe.whitelist()
def get_fiscal_year(date=None, fiscal_year=None, label="Date", verbose=1, company=None, as_dict=False):
	return get_fiscal_years(date, fiscal_year, label, verbose, company, as_dict=as_dict)[0]

def get_fiscal_years(transaction_date=None, fiscal_year=None, label="Date", verbose=1, company=None, as_dict=False):
	fiscal_years = frappe.cache().hget("fiscal_years", company) or []

	if not fiscal_years:
		# if year start date is 2012-04-01, year end date should be 2013-03-31 (hence subdate)
		cond = ""
		if fiscal_year:
			cond += " and fy.name = {0}".format(frappe.db.escape(fiscal_year))
		if company:
			cond += """
				and (not exists (select name
					from `tabFiscal Year Company` fyc
					where fyc.parent = fy.name)
				or exists(select company
					from `tabFiscal Year Company` fyc
					where fyc.parent = fy.name
					and fyc.company=%(company)s)
				)
			"""

		fiscal_years = frappe.db.sql("""
			select
				fy.name, fy.year_start_date, fy.year_end_date
			from
				`tabFiscal Year` fy
			where
				disabled = 0 {0}
			order by
				fy.year_start_date desc""".format(cond), {
				"company": company
			}, as_dict=True)

		frappe.cache().hset("fiscal_years", company, fiscal_years)

	if transaction_date:
		transaction_date = getdate(transaction_date)

	for fy in fiscal_years:
		matched = False
		if fiscal_year and fy.name == fiscal_year:
			matched = True

		if (transaction_date and getdate(fy.year_start_date) <= transaction_date
			and getdate(fy.year_end_date) >= transaction_date):
			matched = True

		if matched:
			if as_dict:
				return (fy,)
			else:
				return ((fy.name, fy.year_start_date, fy.year_end_date),)

	error_msg = _("""{0} {1} is not in any active Fiscal Year""").format(label, formatdate(transaction_date))
	if company:
		error_msg = _("""{0} for {1}""").format(error_msg, frappe.bold(company))
		
	if verbose==1: frappe.msgprint(error_msg)
	raise FiscalYearError(error_msg)

def validate_fiscal_year(date, fiscal_year, company, label="Date", doc=None):
	years = [f[0] for f in get_fiscal_years(date, label=_(label), company=company)]
	if fiscal_year not in years:
		if doc:
			doc.fiscal_year = years[0]
		else:
			throw(_("{0} '{1}' not in Fiscal Year {2}").format(label, formatdate(date), fiscal_year))

@frappe.whitelist()
def get_balance_on(account=None, date=None, party_type=None, party=None, company=None,
	in_account_currency=True, cost_center=None, ignore_account_permission=False):
	if not account and frappe.form_dict.get("account"):
		account = frappe.form_dict.get("account")
	if not date and frappe.form_dict.get("date"):
		date = frappe.form_dict.get("date")
	if not party_type and frappe.form_dict.get("party_type"):
		party_type = frappe.form_dict.get("party_type")
	if not party and frappe.form_dict.get("party"):
		party = frappe.form_dict.get("party")
	if not cost_center and frappe.form_dict.get("cost_center"):
		cost_center = frappe.form_dict.get("cost_center")


	cond = []
	if date:
		cond.append("posting_date <= %s" % frappe.db.escape(cstr(date)))
	else:
		# get balance of all entries that exist
		date = nowdate()

	if account:
		acc = frappe.get_doc("Account", account)

	try:
		year_start_date = get_fiscal_year(date, company=company, verbose=0)[1]
	except FiscalYearError:
		if getdate(date) > getdate(nowdate()):
			# if fiscal year not found and the date is greater than today
			# get fiscal year for today's date and its corresponding year start date
			year_start_date = get_fiscal_year(nowdate(), verbose=1)[1]
		else:
			# this indicates that it is a date older than any existing fiscal year.
			# hence, assuming balance as 0.0
			return 0.0

	if account:
		report_type = acc.report_type
	else:
		report_type = ""

	if cost_center and report_type == 'Profit and Loss':
		cc = frappe.get_doc("Cost Center", cost_center)
		if cc.is_group:
			cond.append(""" exists (
				select 1 from `tabCost Center` cc where cc.name = gle.cost_center
				and cc.lft >= %s and cc.rgt <= %s
			)""" % (cc.lft, cc.rgt))

		else:
			cond.append("""gle.cost_center = %s """ % (frappe.db.escape(cost_center, percent=False), ))


	if account:

		if not (frappe.flags.ignore_account_permission
			or ignore_account_permission):
			acc.check_permission("read")

		if report_type == 'Profit and Loss':
			# for pl accounts, get balance within a fiscal year
			cond.append("posting_date >= '%s' and voucher_type != 'Period Closing Voucher'" \
				% year_start_date)
		# different filter for group and ledger - improved performance
		if acc.is_group:
			cond.append("""exists (
				select name from `tabAccount` ac where ac.name = gle.account
				and ac.lft >= %s and ac.rgt <= %s
			)""" % (acc.lft, acc.rgt))

			# If group and currency same as company,
			# always return balance based on debit and credit in company currency
			if acc.account_currency == frappe.get_cached_value('Company',  acc.company,  "default_currency"):
				in_account_currency = False
		else:
			cond.append("""gle.account = %s """ % (frappe.db.escape(account, percent=False), ))

	if party_type and party:
		cond.append("""gle.party_type = %s and gle.party = %s """ %
			(frappe.db.escape(party_type), frappe.db.escape(party, percent=False)))

	if company:
		cond.append("""gle.company = %s """ % (frappe.db.escape(company, percent=False)))

	if account or (party_type and party):
		if in_account_currency:
			select_field = "sum(debit_in_account_currency) - sum(credit_in_account_currency)"
		else:
			select_field = "sum(debit) - sum(credit)"
		bal = frappe.db.sql("""
			SELECT {0}
			FROM `tabGL Entry` gle
			WHERE {1}""".format(select_field, " and ".join(cond)))[0][0]

		# if bal is None, return 0
		return flt(bal)

def get_count_on(account, fieldname, date):
	cond = []
	if date:
		cond.append("posting_date <= %s" % frappe.db.escape(cstr(date)))
	else:
		# get balance of all entries that exist
		date = nowdate()

	try:
		year_start_date = get_fiscal_year(date, verbose=0)[1]
	except FiscalYearError:
		if getdate(date) > getdate(nowdate()):
			# if fiscal year not found and the date is greater than today
			# get fiscal year for today's date and its corresponding year start date
			year_start_date = get_fiscal_year(nowdate(), verbose=1)[1]
		else:
			# this indicates that it is a date older than any existing fiscal year.
			# hence, assuming balance as 0.0
			return 0.0

	if account:
		acc = frappe.get_doc("Account", account)

		if not frappe.flags.ignore_account_permission:
			acc.check_permission("read")

		# for pl accounts, get balance within a fiscal year
		if acc.report_type == 'Profit and Loss':
			cond.append("posting_date >= '%s' and voucher_type != 'Period Closing Voucher'" \
				% year_start_date)

		# different filter for group and ledger - improved performance
		if acc.is_group:
			cond.append("""exists (
				select name from `tabAccount` ac where ac.name = gle.account
				and ac.lft >= %s and ac.rgt <= %s
			)""" % (acc.lft, acc.rgt))
		else:
			cond.append("""gle.account = %s """ % (frappe.db.escape(account, percent=False), ))

		entries = frappe.db.sql("""
			SELECT name, posting_date, account, party_type, party,debit,credit,
				voucher_type, voucher_no, against_voucher_type, against_voucher
			FROM `tabGL Entry` gle
			WHERE {0}""".format(" and ".join(cond)), as_dict=True)

		count = 0
		for gle in entries:
			if fieldname not in ('invoiced_amount','payables'):
				count += 1
			else:
				dr_or_cr = "debit" if fieldname == "invoiced_amount" else "credit"
				cr_or_dr = "credit" if fieldname == "invoiced_amount" else "debit"
				select_fields = "ifnull(sum(credit-debit),0)" \
					if fieldname == "invoiced_amount" else "ifnull(sum(debit-credit),0)"

				if ((not gle.against_voucher) or (gle.against_voucher_type in ["Sales Order", "Purchase Order"]) or
				(gle.against_voucher==gle.voucher_no and gle.get(dr_or_cr) > 0)):
					payment_amount = frappe.db.sql("""
						SELECT {0}
						FROM `tabGL Entry` gle
						WHERE docstatus < 2 and posting_date <= %(date)s and against_voucher = %(voucher_no)s
						and party = %(party)s and name != %(name)s"""
						.format(select_fields),
						{"date": date, "voucher_no": gle.voucher_no,
							"party": gle.party, "name": gle.name})[0][0]

					outstanding_amount = flt(gle.get(dr_or_cr)) - flt(gle.get(cr_or_dr)) - payment_amount
					currency_precision = get_currency_precision() or 2
					if abs(flt(outstanding_amount)) > 0.1/10**currency_precision:
						count += 1

		return count

@frappe.whitelist()
def add_ac(args=None):
	from frappe.desk.treeview import make_tree_args

	if not args:
		args = frappe.local.form_dict

	args.doctype = "Account"
	args = make_tree_args(**args)

	ac = frappe.new_doc("Account")

	if args.get("ignore_permissions"):
		ac.flags.ignore_permissions = True
		args.pop("ignore_permissions")

	ac.update(args)

	if not ac.parent_account:
		ac.parent_account = args.get("parent")

	ac.old_parent = ""
	ac.freeze_account = "No"
	if cint(ac.get("is_root")):
		ac.parent_account = None
		ac.flags.ignore_mandatory = True

	ac.insert()

	return ac.name

@frappe.whitelist()
def add_cc(args=None):
	from frappe.desk.treeview import make_tree_args

	if not args:
		args = frappe.local.form_dict

	args.doctype = "Cost Center"
	args = make_tree_args(**args)

	if args.parent_cost_center == args.company:
		args.parent_cost_center = "{0} - {1}".format(args.parent_cost_center,
			frappe.get_cached_value('Company',  args.company,  'abbr'))

	cc = frappe.new_doc("Cost Center")
	cc.update(args)

	if not cc.parent_cost_center:
		cc.parent_cost_center = args.get("parent")

	cc.old_parent = ""
	cc.insert()
	return cc.name

def reconcile_against_document(args):
	"""
		Cancel JV, Update aginst document, split if required and resubmit jv
	"""
	for d in args:

		check_if_advance_entry_modified(d)
		validate_allocated_amount(d)

		# cancel advance entry
		doc = frappe.get_doc(d.voucher_type, d.voucher_no)

		doc.make_gl_entries(cancel=1, adv_adj=1)

		# update ref in advance entry
		if d.voucher_type == "Journal Entry":
			update_reference_in_journal_entry(d, doc)
		else:
			update_reference_in_payment_entry(d, doc)

		# re-submit advance entry
		doc = frappe.get_doc(d.voucher_type, d.voucher_no)
		doc.make_gl_entries(cancel = 0, adv_adj =1)

		if d.voucher_type in ('Payment Entry', 'Journal Entry'):
			doc.update_expense_claim()

def check_if_advance_entry_modified(args):
	"""
		check if there is already a voucher reference
		check if amount is same
		check if jv is submitted
	"""
	ret = None
	if args.voucher_type == "Journal Entry":
		ret = frappe.db.sql("""
			select t2.{dr_or_cr} from `tabJournal Entry` t1, `tabJournal Entry Account` t2
			where t1.name = t2.parent and t2.account = %(account)s
			and t2.party_type = %(party_type)s and t2.party = %(party)s
			and (t2.reference_type is null or t2.reference_type in ("", "Sales Order", "Purchase Order"))
			and t1.name = %(voucher_no)s and t2.name = %(voucher_detail_no)s
			and t1.docstatus=1 """.format(dr_or_cr = args.get("dr_or_cr")), args)
	else:
		party_account_field = ("paid_from"
			if erpnext.get_party_account_type(args.party_type) == 'Receivable' else "paid_to")

		if args.voucher_detail_no:
			ret = frappe.db.sql("""select t1.name
				from `tabPayment Entry` t1, `tabPayment Entry Reference` t2
				where
					t1.name = t2.parent and t1.docstatus = 1
					and t1.name = %(voucher_no)s and t2.name = %(voucher_detail_no)s
					and t1.party_type = %(party_type)s and t1.party = %(party)s and t1.{0} = %(account)s
					and t2.reference_doctype in ("", "Sales Order", "Purchase Order")
					and t2.allocated_amount = %(unadjusted_amount)s
			""".format(party_account_field), args)
		else:
			ret = frappe.db.sql("""select name from `tabPayment Entry`
				where
					name = %(voucher_no)s and docstatus = 1
					and party_type = %(party_type)s and party = %(party)s and {0} = %(account)s
					and unallocated_amount = %(unadjusted_amount)s
			""".format(party_account_field), args)

	if not ret:
		throw(_("""Payment Entry has been modified after you pulled it. Please pull it again."""))

def validate_allocated_amount(args):
	if args.get("allocated_amount") < 0:
		throw(_("Allocated amount cannot be negative"))
	elif args.get("allocated_amount") > args.get("unadjusted_amount"):
		throw(_("Allocated amount cannot be greater than unadjusted amount"))

def update_reference_in_journal_entry(d, jv_obj):
	"""
		Updates against document, if partial amount splits into rows
	"""
	jv_detail = jv_obj.get("accounts", {"name": d["voucher_detail_no"]})[0]
	jv_detail.set(d["dr_or_cr"], d["allocated_amount"])
	jv_detail.set('debit' if d['dr_or_cr']=='debit_in_account_currency' else 'credit',
		d["allocated_amount"]*flt(jv_detail.exchange_rate))

	original_reference_type = jv_detail.reference_type
	original_reference_name = jv_detail.reference_name

	jv_detail.set("reference_type", d["against_voucher_type"])
	jv_detail.set("reference_name", d["against_voucher"])

	if d['allocated_amount'] < d['unadjusted_amount']:
		jvd = frappe.db.sql("""
			select cost_center, balance, against_account, is_advance,
				account_type, exchange_rate, account_currency
			from `tabJournal Entry Account` where name = %s
		""", d['voucher_detail_no'], as_dict=True)

		amount_in_account_currency = flt(d['unadjusted_amount']) - flt(d['allocated_amount'])
		amount_in_company_currency = amount_in_account_currency * flt(jvd[0]['exchange_rate'])

		# new entry with balance amount
		ch = jv_obj.append("accounts")
		ch.account = d['account']
		ch.account_type = jvd[0]['account_type']
		ch.account_currency = jvd[0]['account_currency']
		ch.exchange_rate = jvd[0]['exchange_rate']
		ch.party_type = d["party_type"]
		ch.party = d["party"]
		ch.cost_center = cstr(jvd[0]["cost_center"])
		ch.balance = flt(jvd[0]["balance"])

		ch.set(d['dr_or_cr'], amount_in_account_currency)
		ch.set('debit' if d['dr_or_cr']=='debit_in_account_currency' else 'credit', amount_in_company_currency)

		ch.set('credit_in_account_currency' if d['dr_or_cr']== 'debit_in_account_currency'
			else 'debit_in_account_currency', 0)
		ch.set('credit' if d['dr_or_cr']== 'debit_in_account_currency' else 'debit', 0)

		ch.against_account = cstr(jvd[0]["against_account"])
		ch.reference_type = original_reference_type
		ch.reference_name = original_reference_name
		ch.is_advance = cstr(jvd[0]["is_advance"])
		ch.docstatus = 1

	# will work as update after submit
	jv_obj.flags.ignore_validate_update_after_submit = True
	jv_obj.save(ignore_permissions=True)

def update_reference_in_payment_entry(d, payment_entry, do_not_save=False):
	reference_details = {
		"reference_doctype": d.against_voucher_type,
		"reference_name": d.against_voucher,
		"total_amount": d.grand_total,
		"outstanding_amount": d.outstanding_amount,
		"allocated_amount": d.allocated_amount,
		"exchange_rate": d.exchange_rate
	}

	if d.voucher_detail_no:
		existing_row = payment_entry.get("references", {"name": d["voucher_detail_no"]})[0]
		original_row = existing_row.as_dict().copy()
		existing_row.update(reference_details)

		if d.allocated_amount < original_row.allocated_amount:
			new_row = payment_entry.append("references")
			new_row.docstatus = 1
			for field in list(reference_details):
				new_row.set(field, original_row[field])

			new_row.allocated_amount = original_row.allocated_amount - d.allocated_amount
	else:
		new_row = payment_entry.append("references")
		new_row.docstatus = 1
		new_row.update(reference_details)

	payment_entry.flags.ignore_validate_update_after_submit = True
	payment_entry.setup_party_account_field()
	payment_entry.set_missing_values()
	payment_entry.set_amounts()

	if d.difference_amount and d.difference_account:
		payment_entry.set_gain_or_loss(account_details={
			'account': d.difference_account,
			'cost_center': payment_entry.cost_center or frappe.get_cached_value('Company',
				payment_entry.company, "cost_center"),
			'amount': d.difference_amount
		})

	if not do_not_save:
		payment_entry.save(ignore_permissions=True)

def unlink_ref_doc_from_payment_entries(ref_doc):
	remove_ref_doc_link_from_jv(ref_doc.doctype, ref_doc.name)
	remove_ref_doc_link_from_pe(ref_doc.doctype, ref_doc.name)

	frappe.db.sql("""update `tabGL Entry`
		set against_voucher_type=null, against_voucher=null,
		modified=%s, modified_by=%s
		where against_voucher_type=%s and against_voucher=%s
		and voucher_no != ifnull(against_voucher, '')""",
		(now(), frappe.session.user, ref_doc.doctype, ref_doc.name))

	if ref_doc.doctype in ("Sales Invoice", "Purchase Invoice"):
		ref_doc.set("advances", [])

		frappe.db.sql("""delete from `tab{0} Advance` where parent = %s"""
			.format(ref_doc.doctype), ref_doc.name)

def remove_ref_doc_link_from_jv(ref_type, ref_no):
	linked_jv = frappe.db.sql_list("""select parent from `tabJournal Entry Account`
		where reference_type=%s and reference_name=%s and docstatus < 2""", (ref_type, ref_no))

	if linked_jv:
		frappe.db.sql("""update `tabJournal Entry Account`
			set reference_type=null, reference_name = null,
			modified=%s, modified_by=%s
			where reference_type=%s and reference_name=%s
			and docstatus < 2""", (now(), frappe.session.user, ref_type, ref_no))

		frappe.msgprint(_("Journal Entries {0} are un-linked".format("\n".join(linked_jv))))

def remove_ref_doc_link_from_pe(ref_type, ref_no):
	linked_pe = frappe.db.sql_list("""select parent from `tabPayment Entry Reference`
		where reference_doctype=%s and reference_name=%s and docstatus < 2""", (ref_type, ref_no))

	if linked_pe:
		frappe.db.sql("""update `tabPayment Entry Reference`
			set allocated_amount=0, modified=%s, modified_by=%s
			where reference_doctype=%s and reference_name=%s
			and docstatus < 2""", (now(), frappe.session.user, ref_type, ref_no))

		for pe in linked_pe:
			pe_doc = frappe.get_doc("Payment Entry", pe)
			pe_doc.set_total_allocated_amount()
			pe_doc.set_unallocated_amount()
			pe_doc.clear_unallocated_reference_document_rows()

			frappe.db.sql("""update `tabPayment Entry` set total_allocated_amount=%s,
				base_total_allocated_amount=%s, unallocated_amount=%s, modified=%s, modified_by=%s
				where name=%s""", (pe_doc.total_allocated_amount, pe_doc.base_total_allocated_amount,
					pe_doc.unallocated_amount, now(), frappe.session.user, pe))

		frappe.msgprint(_("Payment Entries {0} are un-linked".format("\n".join(linked_pe))))

@frappe.whitelist()
def get_company_default(company, fieldname):
	value = frappe.get_cached_value('Company',  company,  fieldname)

	if not value:
		throw(_("Please set default {0} in Company {1}")
			.format(frappe.get_meta("Company").get_label(fieldname), company))

	return value

def fix_total_debit_credit():
	vouchers = frappe.db.sql("""select voucher_type, voucher_no,
		sum(debit) - sum(credit) as diff
		from `tabGL Entry`
		group by voucher_type, voucher_no
		having sum(debit) != sum(credit)""", as_dict=1)

	for d in vouchers:
		if abs(d.diff) > 0:
			dr_or_cr = d.voucher_type == "Sales Invoice" and "credit" or "debit"

			frappe.db.sql("""update `tabGL Entry` set %s = %s + %s
				where voucher_type = %s and voucher_no = %s and %s > 0 limit 1""" %
				(dr_or_cr, dr_or_cr, '%s', '%s', '%s', dr_or_cr),
				(d.diff, d.voucher_type, d.voucher_no))

def get_stock_and_account_balance(account=None, posting_date=None, company=None):
	if not posting_date: posting_date = nowdate()

	warehouse_account = get_warehouse_account_map(company)

	account_balance = get_balance_on(account, posting_date, in_account_currency=False, ignore_account_permission=True)

	related_warehouses = [wh for wh, wh_details in warehouse_account.items()
		if wh_details.account == account and not wh_details.is_group]

	total_stock_value = 0.0
	for warehouse in related_warehouses:
		value = get_stock_value_on(warehouse, posting_date)
		total_stock_value += value

	precision = frappe.get_precision("Journal Entry Account", "debit_in_account_currency")
	return flt(account_balance, precision), flt(total_stock_value, precision), related_warehouses

def get_currency_precision():
	precision = cint(frappe.db.get_default("currency_precision"))
	if not precision:
		number_format = frappe.db.get_default("number_format") or "#,###.##"
		precision = get_number_format_info(number_format)[2]

	return precision

def get_stock_rbnb_difference(posting_date, company):
	stock_items = frappe.db.sql_list("""select distinct item_code
		from `tabStock Ledger Entry` where company=%s""", company)

	pr_valuation_amount = frappe.db.sql("""
		select sum(pr_item.valuation_rate * pr_item.qty * pr_item.conversion_factor)
		from `tabPurchase Receipt Item` pr_item, `tabPurchase Receipt` pr
		where pr.name = pr_item.parent and pr.docstatus=1 and pr.company=%s
		and pr.posting_date <= %s and pr_item.item_code in (%s)""" %
		('%s', '%s', ', '.join(['%s']*len(stock_items))), tuple([company, posting_date] + stock_items))[0][0]

	pi_valuation_amount = frappe.db.sql("""
		select sum(pi_item.valuation_rate * pi_item.qty * pi_item.conversion_factor)
		from `tabPurchase Invoice Item` pi_item, `tabPurchase Invoice` pi
		where pi.name = pi_item.parent and pi.docstatus=1 and pi.company=%s
		and pi.posting_date <= %s and pi_item.item_code in (%s)""" %
		('%s', '%s', ', '.join(['%s']*len(stock_items))), tuple([company, posting_date] + stock_items))[0][0]

	# Balance should be
	stock_rbnb = flt(pr_valuation_amount, 2) - flt(pi_valuation_amount, 2)

	# Balance as per system
	stock_rbnb_account = "Stock Received But Not Billed - " + frappe.get_cached_value('Company',  company,  "abbr")
	sys_bal = get_balance_on(stock_rbnb_account, posting_date, in_account_currency=False)

	# Amount should be credited
	return flt(stock_rbnb) + flt(sys_bal)


def get_held_invoices(party_type, party):
	"""
	Returns a list of names Purchase Invoices for the given party that are on hold
	"""
	held_invoices = None

	if party_type == 'Supplier':
		held_invoices = frappe.db.sql(
			'select name from `tabPurchase Invoice` where release_date IS NOT NULL and release_date > CURDATE()',
			as_dict=1
		)
		held_invoices = set([d['name'] for d in held_invoices])

	return held_invoices


def get_outstanding_invoices(party_type, party, account, condition=None, filters=None):
	outstanding_invoices = []
	precision = frappe.get_precision("Sales Invoice", "outstanding_amount") or 2

	if account:
		root_type, account_type = frappe.get_cached_value("Account", account, ["root_type", "account_type"])
		party_account_type = "Receivable" if root_type == "Asset" else "Payable"
		party_account_type = account_type or party_account_type
	else:
		party_account_type = erpnext.get_party_account_type(party_type)

	if party_account_type == 'Receivable':
		dr_or_cr = "debit_in_account_currency - credit_in_account_currency"
		payment_dr_or_cr = "credit_in_account_currency - debit_in_account_currency"
	else:
		dr_or_cr = "credit_in_account_currency - debit_in_account_currency"
		payment_dr_or_cr = "debit_in_account_currency - credit_in_account_currency"

	held_invoices = get_held_invoices(party_type, party)

	invoice_list = frappe.db.sql("""
		select
			voucher_no, voucher_type, posting_date, due_date,
			ifnull(sum({dr_or_cr}), 0) as invoice_amount,
			account_currency as currency
		from
			`tabGL Entry`
		where
			party_type = %(party_type)s and party = %(party)s
			and account = %(account)s and {dr_or_cr} > 0
			{condition}
			and ((voucher_type = 'Journal Entry'
					and (against_voucher = '' or against_voucher is null))
				or (voucher_type not in ('Journal Entry', 'Payment Entry')))
		group by voucher_type, voucher_no
		order by posting_date, name""".format(
			dr_or_cr=dr_or_cr,
			condition=condition or ""
		), {
			"party_type": party_type,
			"party": party,
			"account": account,
		}, as_dict=True)

	payment_entries = frappe.db.sql("""
		select against_voucher_type, against_voucher,
			ifnull(sum({payment_dr_or_cr}), 0) as payment_amount
		from `tabGL Entry`
		where party_type = %(party_type)s and party = %(party)s
			and account = %(account)s
			and {payment_dr_or_cr} > 0
			and against_voucher is not null and against_voucher != ''
		group by against_voucher_type, against_voucher
	""".format(payment_dr_or_cr=payment_dr_or_cr), {
		"party_type": party_type,
		"party": party,
		"account": account
	}, as_dict=True)

	pe_map = frappe._dict()
	for d in payment_entries:
		pe_map.setdefault((d.against_voucher_type, d.against_voucher), d.payment_amount)

	for d in invoice_list:
		payment_amount = pe_map.get((d.voucher_type, d.voucher_no), 0)
		outstanding_amount = flt(d.invoice_amount - payment_amount, precision)
		if outstanding_amount > 0.5 / (10**precision):
			if (filters and filters.get("outstanding_amt_greater_than") and
				not (outstanding_amount >= filters.get("outstanding_amt_greater_than") and
				outstanding_amount <= filters.get("outstanding_amt_less_than"))):
				continue

			if not d.voucher_type == "Purchase Invoice" or d.voucher_no not in held_invoices:
				outstanding_invoices.append(
					frappe._dict({
						'voucher_no': d.voucher_no,
						'voucher_type': d.voucher_type,
						'posting_date': d.posting_date,
						'invoice_amount': flt(d.invoice_amount),
						'payment_amount': payment_amount,
						'outstanding_amount': outstanding_amount,
						'due_date': d.due_date,
						'currency': d.currency
					})
				)

	outstanding_invoices = sorted(outstanding_invoices, key=lambda k: k['due_date'] or getdate(nowdate()))
	return outstanding_invoices


def get_account_name(account_type=None, root_type=None, is_group=None, account_currency=None, company=None):
	"""return account based on matching conditions"""
	return frappe.db.get_value("Account", {
		"account_type": account_type or '',
		"root_type": root_type or '',
		"is_group": is_group or 0,
		"account_currency": account_currency or frappe.defaults.get_defaults().currency,
		"company": company or frappe.defaults.get_defaults().company
	}, "name")

@frappe.whitelist()
def get_companies():
	"""get a list of companies based on permission"""
	return [d.name for d in frappe.get_list("Company", fields=["name"],
		order_by="name")]

@frappe.whitelist()
def get_children(doctype, parent, company, is_root=False):
	from erpnext.accounts.report.financial_statements import sort_accounts

	parent_fieldname = 'parent_' + doctype.lower().replace(' ', '_')
	fields = [
		'name as value',
		'is_group as expandable'
	]
	filters = [['docstatus', '<', 2]]

	filters.append(['ifnull(`{0}`,"")'.format(parent_fieldname), '=', '' if is_root else parent])
	# if not is_root:
	# 	filters.append(['`{0}`'.format(parent_fieldname), '=', parent])

	if is_root:
		fields += ['root_type', 'report_type', 'account_currency'] if doctype == 'Account' else []
		filters.append(['company', '=', company])

	else:
		fields += ['root_type', 'account_currency'] if doctype == 'Account' else []
		fields += [parent_fieldname + ' as parent']

	acc = frappe.get_list(doctype, fields=fields, filters=filters)

	if doctype == 'Account':
		sort_accounts(acc, is_root, key="value")
		company_currency = frappe.get_cached_value('Company',  company,  "default_currency")
		for each in acc:
			each["company_currency"] = company_currency
			each["balance"] = flt(get_balance_on(each.get("value"), in_account_currency=False, company=company))

			if each.account_currency != company_currency:
				each["balance_in_account_currency"] = flt(get_balance_on(each.get("value"), company=company))

	return acc

def create_payment_gateway_account(gateway):
	from erpnext.setup.setup_wizard.operations.company_setup import create_bank_account

	company = frappe.db.get_value("Global Defaults", None, "default_company")
	if not company:
		return

	# NOTE: we translate Payment Gateway account name because that is going to be used by the end user
	bank_account = frappe.db.get_value("Account", {"account_name": _(gateway), "company": company},
		["name", 'account_currency'], as_dict=1)

	if not bank_account:
		# check for untranslated one
		bank_account = frappe.db.get_value("Account", {"account_name": gateway, "company": company},
			["name", 'account_currency'], as_dict=1)

	if not bank_account:
		# try creating one
		bank_account = create_bank_account({"company_name": company, "bank_account": _(gateway)})

	if not bank_account:
		frappe.msgprint(_("Payment Gateway Account not created, please create one manually."))
		return

	# if payment gateway account exists, return
	if frappe.db.exists("Payment Gateway Account",
		{"payment_gateway": gateway, "currency": bank_account.account_currency}):
		return

	try:
		frappe.get_doc({
			"doctype": "Payment Gateway Account",
			"is_default": 1,
			"payment_gateway": gateway,
			"payment_account": bank_account.name,
			"currency": bank_account.account_currency
		}).insert(ignore_permissions=True)

	except frappe.DuplicateEntryError:
		# already exists, due to a reinstall?
		pass

@frappe.whitelist()
def update_cost_center(docname, cost_center_name, cost_center_number, company, merge):
	'''
		Renames the document by adding the number as a prefix to the current name and updates
		all transaction where it was present.
	'''
	validate_field_number("Cost Center", docname, cost_center_number, company, "cost_center_number")

	if cost_center_number:
		frappe.db.set_value("Cost Center", docname, "cost_center_number", cost_center_number.strip())
	else:
		frappe.db.set_value("Cost Center", docname, "cost_center_number", "")

	frappe.db.set_value("Cost Center", docname, "cost_center_name", cost_center_name.strip())

	new_name = get_autoname_with_number(cost_center_number, cost_center_name, docname, company)
	if docname != new_name:
		frappe.rename_doc("Cost Center", docname, new_name, force=1, merge=merge)
		return new_name

def validate_field_number(doctype_name, docname, number_value, company, field_name):
	''' Validate if the number entered isn't already assigned to some other document. '''
	if number_value:
		filters = {field_name: number_value, "name": ["!=", docname]}
		if company:
			filters["company"] = company

		doctype_with_same_number = frappe.db.get_value(doctype_name, filters)

		if doctype_with_same_number:
			frappe.throw(_("{0} Number {1} is already used in {2} {3}")
				.format(doctype_name, number_value, doctype_name.lower(), doctype_with_same_number))

def get_autoname_with_number(number_value, doc_title, name, company):
	''' append title with prefix as number and suffix as company's abbreviation separated by '-' '''
	if name:
		name_split=name.split("-")
		parts = [doc_title.strip(), name_split[len(name_split)-1].strip()]
	else:
		abbr = frappe.get_cached_value('Company',  company,  ["abbr"], as_dict=True)
		parts = [doc_title.strip(), abbr.abbr]
	if cstr(number_value).strip():
		parts.insert(0, cstr(number_value).strip())
	return ' - '.join(parts)

@frappe.whitelist()
def get_coa(doctype, parent, is_root, chart=None):
	from erpnext.accounts.doctype.account.chart_of_accounts.chart_of_accounts import build_tree_from_json

	# add chart to flags to retrieve when called from expand all function
	chart = chart if chart else frappe.flags.chart
	frappe.flags.chart = chart

	parent = None if parent==_('All Accounts') else parent
	accounts = build_tree_from_json(chart) # returns alist of dict in a tree render-able form

	# filter out to show data for the selected node only
	accounts = [d for d in accounts if d['parent_account']==parent]

	return accounts

def get_stock_accounts(company):
	return frappe.get_all("Account", filters = {
		"account_type": "Stock",
		"company": company
	})


@frappe.whitelist()
def make_inter_unit_overhead_journal_entry(sales_invoice=None):
	try:

		if not sales_invoice and hasattr(frappe.local, 'form_dict') and frappe.local.form_dict.get("args"):
			sales_invoice = frappe.local.form_dict.get("args", {}).get("sales_invoice")

		if not sales_invoice:
			frappe.throw("Sales Invoice is required.")


		inter_units_overhead = get_config_by_name("INTER_UNIT_SALE_PURCHASE", {})
		if not inter_units_overhead:
			frappe.throw("Inter Unit Sale Purchase config not found.")

		units = ", ".join(f"'{c}'" for c in inter_units_overhead.keys())

		qurey = f"""SELECT si.name AS name, si.company AS company, soi.item_category AS item_category, soi.item_group AS so_item_group,
					 si.customer AS customer, si.posting_date AS posting_date, 
					 si.customer_name AS customer_name, si.total AS total, 
					 sii.delivery_note AS delivery_note 
				FROM `tabSales Invoice` si
				INNER JOIN `tabSales Invoice Item` sii ON sii.parent=si.name
				LEFT JOIN `tabSales Order Item` soi ON soi.parent=sii.sales_order
				LEFT JOIN `tabSales Order` so ON so.name=soi.parent
				WHERE si.name="{sales_invoice}"
				AND si.customer_name IN ({units})
				AND si.company IN ({units})
				AND si.docstatus=1
				AND si.outstanding_amount != 0
				AND so.order_type = 'Inter Unit Sales'
				AND so.transaction_date >= '2025-05-05'
				GROUP BY si.name"""

		si = frappe.db.sql(qurey , as_dict=True)

		if not si:
			frappe.throw(f"No valid Sales Invoice found for {sales_invoice}")

		si = si[0]
		company = si.get("company")

		existing_jv = frappe.db.sql(
			f"""SELECT user_remark FROM `tabJournal Entry`
				WHERE posting_date="{si.get('posting_date')}"
				AND title LIKE ('%Inter Unit Overhead Sales%')
				AND docstatus=1""",
			as_dict=True
		)

		if existing_jv:
			for existing in existing_jv:
				remark = existing.get("user_remark", "")
				if ":" in remark:
					user_remark = remark.split(":", 1)[1]
					si_list = [si.strip() for si in user_remark.split(",") if si.strip()]
					if sales_invoice in si_list:
						frappe.log_error(f"Journal Entry already exists for Sales Invoice {sales_invoice}")


		comp = company.split(" ")
		company_no = comp[1]
		item_category = si.get("item_category")

		if item_category != "Finished Good" or si.get("so_item_group") == "FG Preforms":
			frappe.log_error(f"Invalid item category '{item_category}' in Sales Invoice {sales_invoice}. Only 'Finished Good' allowed.")
			return

		debt_account = f"7.01.01.001 - Gourmet Sales - U{company_no}"
		inter_company_receivables_credit_account = f"2.03.02.001 - Inter Company Receivables - U{company_no}"
		inter_unit_transfer_overheads_credit_account = f"9.01.22.001 - Inter Unit Transfer Overheads - U{company_no}"
		cogs_direct_cost_credit_account = f"9.01.01.003 - COGS - Direct Cost - U{company_no}"

		cogs_row = frappe.db.sql(
			f"""SELECT debit AS amount FROM `tabGL Entry` 
				WHERE voucher_no='{si.get("delivery_note")}' 
				AND ACCOUNT='{cogs_direct_cost_credit_account}'""",
			as_dict=True
		)
		if not cogs_row:
			frappe.throw("No COGS GL Entry found for Delivery Note.")

		cogs_amount = cogs_row[0].get("amount", 0)
		overhead_percent = inter_units_overhead.get(company)
		if not overhead_percent:
			frappe.throw(f"No overhead config for company: {company}")

		overhead_amount = cogs_amount * overhead_percent
		total_receivable = cogs_amount + overhead_amount

		receivable_entry = frappe.db.sql(
			f"""SELECT debit AS amount FROM `tabGL Entry` 
				WHERE voucher_no='{sales_invoice}' 
				AND ACCOUNT='{inter_company_receivables_credit_account}'""",
			as_dict=True
		)
		if not receivable_entry:
			frappe.throw("Receivable not found for Sales Invoice.")

		receivable_amount = receivable_entry[0].get("amount", 0)

		jv_accounts = [
			{
				"account": debt_account,
				"debit": si.get("total"),
				"credit": 0,
				"cost_center": f"Main - U{company_no}"
			},
			{
				"account": inter_company_receivables_credit_account,
				"party_type": "Customer",
				"party": si.get("customer"),
				"debit": total_receivable,
				"credit": 0,
				"cost_center": f"Main - U{company_no}"
			},
			{
				"account": inter_company_receivables_credit_account,
				"party_type": "Customer",
				"party": si.get("customer"),
				"debit": 0,
				"credit": receivable_amount,
				"reference_type": "Sales Invoice",
				"reference_name": si.get("name"),
				"cost_center": f"Main - U{company_no}"
			},
			{
				"account": inter_unit_transfer_overheads_credit_account,
				"debit": 0,
				"credit": overhead_amount,
				"cost_center": f"Main - U{company_no}"
			},
			{
				"account": cogs_direct_cost_credit_account,
				"debit": 0,
				"credit": cogs_amount,
				"cost_center": f"Main - U{company_no}"
			}
		]

		total_debit = sum(float(acc.get("debit", 0)) for acc in jv_accounts)
		total_credit = sum(float(acc.get("credit", 0)) for acc in jv_accounts)
		rounding_difference = round(total_debit - total_credit, 3)
  
  
		if abs(rounding_difference) > 0.001:
			round_off_account = f"10.01.16.002 - Round Off - U{company_no}"
			jv_accounts.append({
				"account": round_off_account,
				"debit": abs(rounding_difference) if rounding_difference < 0 else 0.0,
				"credit": abs(rounding_difference )if rounding_difference > 0 else 0.0,
				"debit_in_account_currency": abs(rounding_difference) if rounding_difference < 0 else 0.0,
				"credit_in_account_currency": abs(rounding_difference) if rounding_difference > 0 else 0.0,
				"cost_center": f"Main - U{company_no}",
				"doctype": "Journal Entry Account",
				"is_advance": "No",
				"user_remark": "Rounding Adjustment",
				"against_account": ""
			})

		for acc in jv_accounts:
			acc.setdefault("debit_in_account_currency", acc["debit"])
			acc.setdefault("credit_in_account_currency", acc["credit"])
			acc["doctype"] = "Journal Entry Account"
			acc["is_advance"] = "No"
			acc["user_remark"] = ""
			acc["against_account"] = ""

		jv_doc = frappe.get_doc({
			"doctype": "Journal Entry",
			"title": f"Inter Unit Overhead Sales JV for {company}",
			"generated": "System Generated",
			"voucher_type": "Inter Company Journal Entry",
			"naming_series": "ACC-IUJV-.YYYY.-",
			"posting_date": si.get("posting_date"),
			"company": company,
			"accounts": jv_accounts,
			"user_remark": f"Inter Unit Journal Entry Overhead for Sales Invoice(s): {sales_invoice}"
		})
		jv_doc.save(ignore_permissions=True)
		frappe.db.commit()

		frappe.enqueue(
			"nrp_manufacturing.utils.submit_jv_queue",
			journal_entry_name=jv_doc.name,
			queue="long",
			enqueue_after_commit=True
		)

	except Exception as e:
		frappe.log_error(f"Error in overhead_jv: {str(e)}", title="Inter Unit Overhead Sales JV Error")
		try:
			si = frappe.db.sql( qurey, as_dict=True)

			if not si:
				return

			invoice = frappe.get_doc("Sales Invoice", si)
			if invoice.docstatus == 1:
				invoice.cancel()
				frappe.db.commit()

			frappe.db.set_value("Sales Invoice", sales_invoice, "docstatus", 0)

			frappe.db.sql(
				"DELETE FROM `tabGL Entry` WHERE voucher_no=%s AND voucher_type='Sales Invoice'",
				sales_invoice
			)

			invoice.add_comment(
				"Comment",
				f"Inter Unit Overhead JV creation failed and invoice reverted to Draft.\nReason: {str(e)}"
			)
			frappe.db.commit()
		except Exception as revert_error:
			frappe.log_error(
				f"Failed to revert SI {sales_invoice} to draft: {revert_error}",
				title="SI Revert Failure"
			)

@frappe.whitelist()
def make_inter_unit_sales_journal_entry(sales_invoice=None):
	try:

		payload = {}
		if hasattr(frappe.local, 'form_dict') and frappe.local.form_dict:
			payload = frappe.local.form_dict

		if payload.get("args"):
			sales_invoice = payload.get("args", {}).get("sales_invoice")

		if not sales_invoice:
			frappe.throw("Sales Invoice is required")

		inter_units_overhead = get_config_by_name("INTER_UNIT_SALE_PURCHASE", {})
		if not inter_units_overhead:
			frappe.throw("Inter Unit Sale Purchase config not found")

		units = ", ".join(f"'{c}'" for c in inter_units_overhead.keys())
		condition = f"AND si.company IN ({units})"

		query = f"""
			SELECT 
				si.name AS name,
				si.company AS company,
				si.customer AS customer,
				si.total AS total,
				sii.sales_order AS sales_order,
				soi.item_category AS so_item_category,
				soi.item_group AS so_item_group,
				soi.item_code AS so_item_code,
				soi.qty AS so_qty,
				soi.rate AS so_rate,
				soi.amount AS so_amount,
				si.posting_date AS posting_date
			FROM `tabSales Invoice` si
			INNER JOIN `tabSales Invoice Item` sii ON sii.parent = si.name
			LEFT JOIN `tabSales Order Item` soi ON soi.parent = sii.sales_order
			LEFT JOIN `tabSales Order` so ON so.name = soi.parent
			WHERE si.name = "{sales_invoice}"
			AND si.customer_name IN ({units})
			AND si.docstatus = 1
			AND so.order_type = 'Inter Unit Sales'
			AND so.transaction_date >= '2025-05-05'
			AND si.outstanding_amount != 0
			{condition}
			GROUP BY si.name
		"""

		sales_invoices = frappe.db.sql(query, as_dict=True)

		if not sales_invoices:
			frappe.throw(f"No Sales Invoice found or it doesn't qualify for Inter Unit Sales JV: {sales_invoice}")

		si = sales_invoices[0]
		posting_date = si.get("posting_date")

		existing_jv = frappe.db.sql(
			"""SELECT user_remark FROM `tabJournal Entry`
			   WHERE posting_date = %s AND title LIKE %s AND docstatus = 1""",
			(posting_date, "%Inter Unit Sales JV for%"),
			as_dict=True
		)

		if existing_jv:
			for existing in existing_jv:
				remark = existing.get("user_remark", "")
				if ":" in remark:
					user_remark = remark.split(":", 1)[1]
					si_list = [si.strip() for si in user_remark.split(",") if si.strip()]
					if sales_invoice in si_list:
						frappe.log_error(f"Journal Entry already exists for Sales Invoice {sales_invoice}")


		if si.get("so_item_category") == "Finished Good" or (si.get("so_item_category") == "Finished Good"  and si.get("so_item_group") != "FG Preforms"):
			frappe.log_error(f"Invalid item category '{si.get('so_item_category')}' in Sales Invoice {sales_invoice}. Only 'Non Finished Good' allowed.")
			return

		company = si.get("company")
		comp = company.split(" ")
		company_no = comp[1]

		gl_amount = fetch_sales_amount_from_gl_entry("Sales Invoice", si.get("name"))
		jv_amount = gl_amount.get("amount", 0.0)
		dn_data = get_delivery_note_from_sales_invoice(si)
		rce_amount = fetch_receviables_from_gl_entry("Sales Invoice", si.get("name"))

		jv_accounts = []

		jv_accounts.append({
			"account": gl_amount.get("account"),
			"party_type": "",
			"party": "",
			"credit_in_account_currency": "",
			"credit": 0.0,
			"debit_in_account_currency": jv_amount,
			"debit": jv_amount,
			"is_advance": "No",
			"against_account": "",
			"user_remark": "",
			"reference_type": "",
			"reference_name": "",
			"cost_center": f"Main - U{company_no}",
			"doctype": "Journal Entry Account",
		})

		jv_accounts.append({
			"account": dn_data.get("account"),
			"party_type": "",
			"party": "",
			"credit_in_account_currency": dn_data.get("amount", 0.0),
			"credit": dn_data.get("amount", 0.0),
			"debit_in_account_currency": "",
			"debit": 0.0,
			"is_advance": "No",
			"against_account": "",
			"user_remark": dn_data.get("name"),
			"cost_center": f"Main - U{company_no}",
			"doctype": "Journal Entry Account",
		})

		jv_accounts.append({
			"account": rce_amount.get("account"),
			"party_type": "Customer",
			"party": si.get("customer", ""),
			"credit_in_account_currency": rce_amount.get("amount", 0.0),
			"credit": rce_amount.get("amount", 0.0),
			"reference_type": "Sales Invoice",
			"reference_name": si.get("name"),
			"debit_in_account_currency": "",
			"debit": 0.0,
			"is_advance": "Yes",
			"against_account": "",
			"user_remark": rce_amount.get("name"),
			"cost_center": f"Main - U{company_no}",
			"doctype": "Journal Entry Account",
		})

		jv_accounts.append({
			"account": rce_amount.get("account"),
			"party_type": "Customer",
			"party": si.get("customer", ""),
			"credit_in_account_currency": "",
			"credit": 0.0,
			"reference_type": "",
			"reference_name": "",
			"debit_in_account_currency": dn_data.get("amount", 0.0),
			"debit": dn_data.get("amount", 0.0),
			"is_advance": "No",
			"against_account": "",
			"user_remark": rce_amount.get("name"),
			"cost_center": f"Main - U{company_no}",
			"doctype": "Journal Entry Account",
		})
  
  
		total_debit = sum(float(acc.get("debit", 0)) for acc in jv_accounts)
		total_credit = sum(float(acc.get("credit", 0)) for acc in jv_accounts)
		rounding_difference = round(total_debit - total_credit, 3)
  
  
		if abs(rounding_difference) > 0.001:
			round_off_account = f"10.01.16.002 - Round Off - U{company_no}"
			jv_accounts.append({
				"account": round_off_account,
				"debit": abs(rounding_difference) if rounding_difference < 0 else 0.0,
				"credit": abs(rounding_difference )if rounding_difference > 0 else 0.0,
				"debit_in_account_currency": abs(rounding_difference) if rounding_difference < 0 else 0.0,
				"credit_in_account_currency": abs(rounding_difference) if rounding_difference > 0 else 0.0,
				"cost_center": f"Main - U{company_no}",
				"doctype": "Journal Entry Account",
				"is_advance": "No",
				"user_remark": "Rounding Adjustment",
				"against_account": ""
			})

		jv_payload = {
			"title": f"Inter Unit Sales JV for {company}",
			"generated": "System Generated",
			"voucher_type": "Inter Company Journal Entry",
			"naming_series": "ACC-IUJV-.YYYY.-",
			"posting_date": posting_date,
			"company": company,
			"accounts": jv_accounts,
			"doctype": "Journal Entry",
			"user_remark": f"Inter Unit Journal Entry Overhead for Sales Invoice(s): {sales_invoice}",
		}
  

		journal_entry = frappe.get_doc(jv_payload)
		journal_entry.save(ignore_permissions=True, ignore_workflow=True)
		frappe.db.commit()

		frappe.enqueue(
			"nrp_manufacturing.utils.submit_jv_queue",
			journal_entry_name=journal_entry.name,
			queue="long",
			enqueue_after_commit=True,
		)

	except Exception as e:
		frappe.log_error(f"Error in Inter Unit Sales JV: {str(e)}", title="Inter Unit Sales JV Error")

		try:
			sales_invoices = frappe.db.sql(query, as_dict=True)
			if not sales_invoices:
				return

			sales_invoice = sales_invoices[0].get("name")
			invoice = frappe.get_doc("Sales Invoice", sales_invoice)
			if invoice.docstatus == 1:
				invoice.cancel()
				frappe.db.commit()

			frappe.db.set_value("Sales Invoice", sales_invoice, "docstatus", 0)

			frappe.db.sql(
				"DELETE FROM `tabGL Entry` WHERE voucher_no=%s AND voucher_type='Sales Invoice'",
				sales_invoice
			)

			invoice.add_comment(
				"Comment",
				f"Inter Unit Sales JV creation failed and invoice reverted to Draft.\nReason: {str(e)}"
			)

			frappe.db.commit()

		except Exception as revert_error:
			frappe.log_error(
				f"Failed to revert SI {sales_invoice} to draft: {revert_error}",
				title="SI Revert Failure"
			)

def fetch_sales_amount_from_gl_entry(voucher_type, voucher_no):
	try:
		gl_data = frappe.db.sql(
			f"""
			SELECT credit AS amount, account 
			FROM `tabGL Entry`
			WHERE voucher_type = %s AND voucher_no = %s
			""",
			(voucher_type, voucher_no),
			as_dict=True
		)

		if gl_data:
			amount = [
				entry
				for entry in gl_data
				if "Gourmet Sales" in entry.get("account", "")
				and entry.get("amount") != 0.0
			]
			return amount[0]
		else:
			return {"amount": 0.0, "account": ""}
	except Exception as e:
		frappe.log_error(
			f"Error fetching amount from GL Entry: {str(e)}", title=voucher_type+" Fetch Amount Error" +voucher_no
		)
		return {"amount": 0.0, "account": ""}


def fetch_receviables_from_gl_entry(voucher_type, voucher_no):
	try:
		gl_data = frappe.db.sql(
			f"""
			SELECT debit AS amount, account 
			FROM `tabGL Entry`
			WHERE voucher_type = %s AND voucher_no = %s
			""",
			(voucher_type, voucher_no),
			as_dict=True
		)

		if gl_data:
			amount = [
				entry
				for entry in gl_data
				if "Inter Company Receivables" in entry.get("account", "")
				and entry.get("amount") != 0.0
			]
			return amount[0]
		else:
			return {"amount": 0.0, "account": ""}
	except Exception as e:
		frappe.log_error(
			f"Error fetching amount from GL Entry: {str(e)}", title=voucher_type +" Fetch Amount Error " + voucher_no
		)
		return {"amount": 0.0, "account": ""}


def get_delivery_note_from_sales_invoice(si_name):
	try:
		dn = frappe.db.sql(
			"""
		SELECT delivery_note  
		FROM `tabSales Invoice Item` 
		WHERE parent = %s 
		AND docstatus = 1
		""",
			(si_name["name"],),
			as_dict=True
		)
		dn_set = {d["delivery_note"] for d in dn if d.get("delivery_note")}
		if dn_set:
			dn_set = list(dn_set)[0]
			gl_data = frappe.db.sql(
				f"""SELECT debit AS amount, account FROM `tabGL Entry` WHERE voucher_type='Delivery Note' AND voucher_no='{dn_set}';""",
				as_dict=True
			)
			amount = [
				entry
				for entry in gl_data
				if "COGS - Direct Cost" in entry.get("account")
				and entry.get("amount") != 0.0
			]
			return {
				"amount": int(amount[0].get("amount")),
				"account": amount[0].get("account"),
				"name": si_name.name,
			}
		else:
			return None
	except Exception as e:
		frappe.log_error(
			f"Error fetching Purchase Invoice for Purchase Receipt {si_name}: {str(e)}",
			title="Fetch Purchase Invoice Error",
		)
		return None

@frappe.whitelist()
def make_inter_unit_overhead_purchase_journal_entry(purchase_invoice=None):
	try:

		payload = {}
		if hasattr(frappe.local, 'form_dict') and frappe.local.form_dict:
			payload = frappe.local.form_dict

		if payload.get("args"):
			purchase_invoice = payload.get("args", {}).get("purchase_invoice")

		if not purchase_invoice:
			frappe.throw("Purchase Invoice is required.")

		inter_units_overhead = get_config_by_name("INTER_UNIT_SALE_PURCHASE", {})
		if not inter_units_overhead:
			frappe.throw("Inter Unit Sale Purchase configuration not found.")

		inter_units_overhead_companies = list(inter_units_overhead.keys())
		units = "IN ({})".format(", ".join(f"'{c}'" for c in inter_units_overhead_companies))

		qurey = f"""SELECT pi.name AS name, pi.company AS company, pri.item_category AS item_category,
					 pi.supplier AS supplier, pi.supplier_name AS supplier_name, pi.total AS total,
					 pii.purchase_order AS purchase_order, soi.item_group AS soi_item_group
				FROM `tabPurchase Invoice` pi
				INNER JOIN `tabPurchase Invoice Item` pii ON pii.parent=pi.name
				LEFT JOIN `tabPurchase Receipt Item` pri ON pri.parent=pii.purchase_receipt
				WHERE pi.name = "{purchase_invoice}"
				AND pi.supplier_name {units}
				AND pi.company {units}
				AND pi.outstanding_amount != 0
				AND pi.docstatus = 1
				GROUP BY pi.name"""

		pi = frappe.db.sql(qurey, as_dict=True)
  

		if not pi:
			frappe.throw(f"No valid Purchase Invoice found for {purchase_invoice}")

		pi = pi[0]
		company = pi.get("company")

		existing_jv = frappe.db.sql(
			"""SELECT user_remark FROM `tabJournal Entry`
				WHERE posting_date = %s AND title LIKE %s AND docstatus = 1""",
			(pi.get('posting_date'), "%Inter Unit Overhead Purchase%"),
			as_dict=True
		)

		if existing_jv:
			for jv in existing_jv:
				remark = jv.get("user_remark", "")
				if purchase_invoice in remark:
					frappe.throw(f"Journal Entry already exists for Purchase Invoice {purchase_invoice}")

		comp = company.split(" ")
		company_no = comp[1]

		if pi.get("item_category") != "Finished Good" or pi.get("soi_item_group") == "FG Preforms":
			frappe.log_error( title="Invalid item category", message = f"Invalid item category '{pi.get('item_category')}' in Purchase Invoice {purchase_invoice}. Only 'Finished Good' allowed.")
			return

		gl_amount = fetch_amount_from_gl_entry("Purchase Invoice", purchase_invoice)
		total_payable_amount = gl_amount.get("amount", 0.0)

		overhead_percent = inter_units_overhead.get(company)
		if not overhead_percent:
			frappe.throw(f"No overhead config for company: {company}")

		jv_amount = total_payable_amount * overhead_percent
		inter_unit_payable = total_payable_amount + jv_amount

		jv_accounts = []

		jv_accounts.append({
			"account": gl_amount.get("account"),
			"party_type": "Supplier",
			"party": pi.get("supplier"),
			"credit_in_account_currency": 0.0,
			"credit": 0.0,
			"debit_in_account_currency": total_payable_amount,
			"debit": total_payable_amount,
			"is_advance": "No",
			"against_account": "",
			"reference_type": "Purchase Invoice",
			"reference_name": purchase_invoice,
			"user_remark": "",
			"cost_center": f"Main - U{company_no}",
			"doctype": "Journal Entry Account",
		})

		jv_accounts.append({
			"account": gl_amount.get("account"),
			"party_type": "Supplier",
			"party": pi.get("supplier"),
			"credit_in_account_currency": inter_unit_payable,
			"credit": inter_unit_payable,
			"debit_in_account_currency": 0.0,
			"debit": 0.0,
			"is_advance": "No",
			"against_account": "",
			"user_remark": "",
			"cost_center": f"Main - U{company_no}",
			"doctype": "Journal Entry Account",
		})

		jv_accounts.append({
			"account": f"9.01.22.001 - Inter Unit Transfer Overheads - U{company_no}",
			"party_type": "",
			"party": "",
			"credit_in_account_currency": 0.0 ,
			"credit": 0.0,
			"debit_in_account_currency":jv_amount,
			"debit": jv_amount,
			"is_advance": "No",
			"against_account": "",
			"user_remark": purchase_invoice,
			"cost_center": f"Main - U{company_no}",
			"doctype": "Journal Entry Account",
		})

		total_debit = sum(float(acc.get("debit", 0)) for acc in jv_accounts)
		total_credit = sum(float(acc.get("credit", 0)) for acc in jv_accounts)
		rounding_difference = round(total_debit - total_credit, 3)
  
  
		if abs(rounding_difference) > 0.001:
			round_off_account = f"10.01.16.002 - Round Off - U{company_no}"
			jv_accounts.append({
				"account": round_off_account,
				"debit": abs(rounding_difference) if rounding_difference < 0 else 0.0,
				"credit": abs(rounding_difference )if rounding_difference > 0 else 0.0,
				"debit_in_account_currency": abs(rounding_difference) if rounding_difference < 0 else 0.0,
				"credit_in_account_currency": abs(rounding_difference) if rounding_difference > 0 else 0.0,
				"cost_center": f"Main - U{company_no}",
				"doctype": "Journal Entry Account",
				"is_advance": "No",
				"user_remark": "Rounding Adjustment",
				"against_account": ""
			})

		jv_payload = {
			"title": f"Inter Unit Overhead Purchase for {company}",
			"generated": "System Generated",
			"voucher_type": "Inter Company Journal Entry",
			"naming_series": "ACC-IUJV-.YYYY.-",
			"posting_date": pi.get("posting_date"),
			"company": company,
			"accounts": jv_accounts,
			"doctype": "Journal Entry",
			"user_remark": f"Inter Unit Journal Entry Overhead for Purchase Invoice(s): {purchase_invoice}",
		}

		journal_entry_overhead = frappe.get_doc(jv_payload)
		journal_entry_overhead.save(ignore_permissions=True, ignore_workflow=True)
		frappe.db.commit()

		frappe.enqueue(
			"nrp_manufacturing.utils.submit_jv_queue",
			journal_entry_name=journal_entry_overhead.name,
			queue="long",
			enqueue_after_commit=True,
		)

	except Exception as e:
		try:
			pi = frappe.db.sql(qurey, as_dict=True)
			if not pi:
				return
      
			invoice = frappe.get_doc("Purchase Invoice", purchase_invoice)
			if invoice.docstatus == 1:
				invoice.cancel()
				frappe.db.commit()

			frappe.db.set_value("Purchase Invoice", purchase_invoice, "docstatus", 0)

			workflow_name = frappe.get_value("Workflow", {"document_type": "Purchase Invoice", "is_active": 1}, "name")
			if workflow_name:
				valid_states = frappe.get_all("Workflow Document State", filters={"parent": workflow_name}, fields=["state"])
				valid_state_names = [s["state"] for s in valid_states]
				if "Pending" in valid_state_names:
					frappe.db.set_value("Purchase Invoice", purchase_invoice, "workflow_state", "Pending")

			frappe.db.sql(
				"DELETE FROM `tabGL Entry` WHERE voucher_no=%s AND voucher_type='Purchase Invoice'",
				purchase_invoice
			)

			invoice.add_comment(
				"Comment",
				f"Inter Unit Overhead JV creation failed and invoice reverted to Draft.\nReason: {str(e)}"
			)
			frappe.db.commit()

		except Exception as revert_error:
			frappe.log_error(
				f"Failed to revert PI {purchase_invoice} to draft: {revert_error}",
				title="PI Revert Failure"
			)
def fetch_amount_from_gl_entry(voucher_type, voucher_no):
	try:
		gl_data = frappe.db.sql(
			f"""SELECT credit AS amount, account FROM `tabGL Entry` WHERE voucher_type='{voucher_type}' AND voucher_no='{voucher_no}';""",
			as_dict=True
		)
		if gl_data:
			amount = [
				entry
				for entry in gl_data
				if "Inter Company Payables" in entry.get("account", "")
				and entry.get("amount") != 0.0
			]
			return amount[0]
		else:
			return 0.0
	except Exception as e:
		frappe.log_error(
			f"Error fetching amount from GL Entry: {str(e)}", title= voucher_type+" Fetch Amount Error "+voucher_no
		)
		return 0.0


def get_purchase_invoice_ledger(pi_name, inter_unit_overhead):
	try:
		if not pi_name:
			return None

		gl_data = frappe.db.sql(
			f"""SELECT debit AS amount, account FROM `tabGL Entry` WHERE voucher_type='Purchase Invoice' AND voucher_no='{pi_name}';""",
			as_dict=True
		)
		amount = [entry for entry in gl_data if entry.get("amount") != 0.0]
		return (
			amount[0].get("amount") * inter_unit_overhead,
			pi_name,
		)
	except Exception as e:
		frappe.log_error(
			f"Error fetching Purchase Invoice for Purchase Receipt {pi_name}: {str(e)}",
			title="Fetch Purchase Invoice Error",
		)
		return None
