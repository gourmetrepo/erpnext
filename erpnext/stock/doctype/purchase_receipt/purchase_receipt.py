# Copyright (c) 2015, Frappe Technologies Pvt. Ltd. and Contributors
# License: GNU General Public License v3. See license.txt

from __future__ import unicode_literals
import frappe

from frappe.utils import flt, cint, nowdate

from frappe import throw, _
import frappe.defaults
import json
import requests
from frappe.utils import getdate
from erpnext.controllers.buying_controller import BuyingController
from erpnext.accounts.utils import get_account_currency
from frappe.desk.notifications import clear_doctype_notifications
from frappe.model.mapper import get_mapped_doc
from erpnext.buying.utils import check_on_hold_or_closed_status
from erpnext.assets.doctype.asset.asset import get_asset_account, is_cwip_accounting_enabled
from erpnext.assets.doctype.asset_category.asset_category import get_asset_category_account
from nrp_manufacturing.utils import get_config_by_name, json_error_response
from nrp_manufacturing.constants.globals import PERMISSION_ERROR_MSG, ERROR_MSG
from frappe.exceptions import ValidationError
from six import iteritems

form_grid_templates = {
	"items": "templates/form_grid/item_grid.html"
}

class PurchaseReceipt(BuyingController):
	def __init__(self, *args, **kwargs):
		super(PurchaseReceipt, self).__init__(*args, **kwargs)
		self.status_updater = [{
			'target_dt': 'Purchase Order Item',
			'join_field': 'purchase_order_item',
			'target_field': 'received_qty',
			'target_parent_dt': 'Purchase Order',
			'target_parent_field': 'per_received',
			'target_ref_field': 'qty',
			'source_dt': 'Purchase Receipt Item',
			'source_field': 'received_qty',
			'second_source_dt': 'Purchase Invoice Item',
			'second_source_field': 'received_qty',
			'second_join_field': 'po_detail',
			'percent_join_field': 'purchase_order',
			'overflow_type': 'receipt',
			'second_source_extra_cond': """ and exists(select name from `tabPurchase Invoice`
				where name=`tabPurchase Invoice Item`.parent and update_stock = 1)"""
		},
		{
			'source_dt': 'Purchase Receipt Item',
			'target_dt': 'Material Request Item',
			'join_field': 'material_request_item',
			'target_field': 'received_qty',
			'target_parent_dt': 'Material Request',
			'target_parent_field': 'per_received',
			'target_ref_field': 'stock_qty',
			'source_field': 'stock_qty',
			'percent_join_field': 'material_request'
		}]
		if cint(self.is_return):
			self.status_updater.append({
				'source_dt': 'Purchase Receipt Item',
				'target_dt': 'Purchase Order Item',
				'join_field': 'purchase_order_item',
				'target_field': 'returned_qty',
				'source_field': '-1 * qty',
				'second_source_dt': 'Purchase Invoice Item',
				'second_source_field': '-1 * qty',
				'second_join_field': 'po_detail',
				'extra_cond': """ and exists (select name from `tabPurchase Receipt`
					where name=`tabPurchase Receipt Item`.parent and is_return=1)""",
				'second_source_extra_cond': """ and exists (select name from `tabPurchase Invoice`
					where name=`tabPurchase Invoice Item`.parent and is_return=1 and update_stock=1)"""
			})

	def validate(self):
		# Subcontracting valuation rate configurations
		# if self.subcontracted:
		# 	update_valuation_rate_for_subcontracting(self)

		self.validate_posting_time()
		super(PurchaseReceipt, self).validate()

		if self._action=="submit":
			self.make_batches('warehouse')
		else:
			self.set_status()

		self.po_required()
		self.validate_with_previous_doc()
		self.validate_uom_is_integer("uom", ["qty", "received_qty"])
		self.validate_uom_is_integer("stock_uom", "stock_qty")
		self.validate_cwip_accounts()

		self.check_on_hold_or_closed_status()

		if getdate(self.posting_date) > getdate(nowdate()):
			throw(_("Posting Date cannot be future date"))

		# Subcontracting valuation rate configurations
		# if self.subcontracted:
		# 	update_valuation_rate_for_subcontracting(self)


	def validate_cwip_accounts(self):
		for item in self.get('items'):
			if item.is_fixed_asset and is_cwip_accounting_enabled(item.asset_category):
				# check cwip accounts before making auto assets
				# Improves UX by not giving messages of "Assets Created" before throwing error of not finding arbnb account
				arbnb_account = self.get_company_default("asset_received_but_not_billed")
				cwip_account = get_asset_account("capital_work_in_progress_account", asset_category = item.asset_category, \
					company = self.company)
				break

	def validate_with_previous_doc(self):
		super(PurchaseReceipt, self).validate_with_previous_doc({
			"Purchase Order": {
				"ref_dn_field": "purchase_order",
				"compare_fields": [["supplier", "="], ["company", "="],	["currency", "="]],
			},
			"Purchase Order Item": {
				"ref_dn_field": "purchase_order_item",
				"compare_fields": [["project", "="], ["uom", "="], ["item_code", "="]],
				"is_child_table": True,
				"allow_duplicate_prev_row_id": True
			}
		})

		if cint(frappe.db.get_single_value('Buying Settings', 'maintain_same_rate')) and not self.is_return:
			self.validate_rate_with_reference_doc([["Purchase Order", "purchase_order", "purchase_order_item"]])

	def po_required(self):
		if frappe.db.get_value("Buying Settings", None, "po_required") == 'Yes':
			for d in self.get('items'):
				if not d.purchase_order:
					frappe.throw(_("Purchase Order number required for Item {0}").format(d.item_code))

	def get_already_received_qty(self, po, po_detail):
		qty = frappe.db.sql("""select sum(qty) from `tabPurchase Receipt Item`
			where purchase_order_item = %s and docstatus = 1
			and purchase_order=%s
			and parent != %s""", (po_detail, po, self.name))
		return qty and flt(qty[0][0]) or 0.0

	def get_po_qty_and_warehouse(self, po_detail):
		po_qty, po_warehouse = frappe.db.get_value("Purchase Order Item", po_detail,
			["qty", "warehouse"])
		return po_qty, po_warehouse

	# Check for Closed status
	def check_on_hold_or_closed_status(self):
		check_list =[]
		for d in self.get('items'):
			if (d.meta.get_field('purchase_order') and d.purchase_order
				and d.purchase_order not in check_list):
				check_list.append(d.purchase_order)
				check_on_hold_or_closed_status('Purchase Order', d.purchase_order)

	# on submit
	def on_submit(self):
		super(PurchaseReceipt, self).on_submit()

		# Check for Approving Authority
		frappe.get_doc('Authorization Control').validate_approving_authority(self.doctype,
			self.company, self.base_grand_total)

		self.update_prevdoc_status()
		if flt(self.per_billed) < 100:
			self.update_billing_status()
		else:
			self.db_set("status", "Completed")


		# Updating stock ledger should always be called after updating prevdoc status,
		# because updating ordered qty, reserved_qty_for_subcontract in bin
		# depends upon updated ordered qty in PO
		self.update_stock_ledger()

		from erpnext.stock.doctype.serial_no.serial_no import update_serial_nos_after_submit
		update_serial_nos_after_submit(self, "items")

		# Check for sub contractor
		if self.supplier == "SUP-IU-00005" and self.company in ["Unit 5", "Unit 8", "Unit 11"]:
			try:
				frappe.enqueue("erpnext.stock.doctype.purchase_receipt.purchase_receipt.create_documents_flow", docname=self.name, queue="long", enqueue_after_commit=True)
				frappe.db.commit()
			except Exception as e:
				frappe.db.rollback()
				traceback = frappe.get_traceback()
				frappe.log_error(message=traceback, title=f"Error while enqueue create_documents_flow from purchase receipt: {self.name}.")
				self.add_comment('Comment', _('Action Failed') + '<br><br>' + str(e))
		
		# Create purchase invoice for subcontractor
		if self.request_from == "SubContractor":
			try:
				frappe.enqueue("erpnext.stock.doctype.purchase_receipt.purchase_receipt.create_purchase_invoice", docname=self.name, queue="long", enqueue_after_commit=True)
				frappe.db.commit()
			except Exception as e:
				frappe.db.rollback()
				traceback = frappe.get_traceback()
				frappe.log_error(message=traceback, title=f"Error while enqueue create_purchase_invoice from purchase receipt: {self.name}.")
				self.add_comment('Comment', _('Action Failed') + '<br><br>' + str(e))

		# self.make_gl_entries()
		try:
			frappe.enqueue("nrp_manufacturing.nrp_manufacturing.doctype.stock_gl_queue.stock_gl_queue.process_single_stock_gl_queue",doc_name=self.name,doc_type=self.doctype,queue="gl",enqueue_after_commit=True)
		except Exception as e:
			traceback = frappe.get_traceback()
			frappe.log_error(message=traceback,title='Exc GL entry Adding Queue'+str(self.name))
			self.add_comment('Comment', _('Action Failed') + '<br><br>' + traceback)

		try:
			from datetime import datetime
			baseurl = get_config_by_name("THIRD_PARTY_SUPPLIER_APP")
			if baseurl:
				if frappe.db.get_value('Supplier', self.supplier, 'third_party_warehouse'):
					url = baseurl + 'PostNrpData'
					data = []
					for it in self.get('items'):
						data.append({
							"ProductCode": it.item_code,
							"SupplierCode": self.supplier if self.supplier else '',
							"Qty": it.qty,
							"nrpInvoiceNo": self.name if self.name else ''
							})
					
					payload = {
						"data": data
					}

					# Maintain logs
					nrp_integeration = {
						"ref_doctype": "Purchase Receipt",
						"doctype": "Nrp Integration",
						"request": str(payload)
					}

					nrp_integeration["title"] = "Purchase Receipt Sync with GSSM " + str(datetime.now())
					nrp_logs = frappe.get_doc(nrp_integeration)
					nrp_logs.save(ignore_permissions=True)
					response_gssm = []

					data = json.dumps(payload, default=str)
					headers = {'Content-Type': 'application/json'}
					response = requests.request("POST", url , headers=headers, data=data)
					response_gssm.append(response.text)
					
					# Maintain logs
					frappe.db.set_value('Nrp Integration', nrp_logs.name, 'response', str(response_gssm))
		except ValidationError as error:
			return json_error_response(str(error))
		except frappe.PermissionError as error:
			return json_error_response(PERMISSION_ERROR_MSG)
		except Exception as error:
			traceback = frappe.get_traceback()
			frappe.log_error(message=traceback, title="Error While Purchase Receipt Sync with GSSM.")
			return json_error_response(ERROR_MSG)
	
	def check_next_docstatus(self):
		submit_rv = frappe.db.sql("""select t1.name
			from `tabPurchase Invoice` t1,`tabPurchase Invoice Item` t2
			where t1.name = t2.parent and t2.purchase_receipt = %s and t1.docstatus = 1""",
			(self.name))
		if submit_rv:
			frappe.throw(_("Purchase Invoice {0} is already submitted").format(self.submit_rv[0][0]))

	def on_cancel(self):
		super(PurchaseReceipt, self).on_cancel()

		self.check_on_hold_or_closed_status()
		# Check if Purchase Invoice has been submitted against current Purchase Order
		submitted = frappe.db.sql("""select t1.name
			from `tabPurchase Invoice` t1,`tabPurchase Invoice Item` t2
			where t1.name = t2.parent and t2.purchase_receipt = %s and t1.docstatus = 1""",
			self.name)
		if submitted:
			frappe.throw(_("Purchase Invoice {0} is already submitted").format(submitted[0][0]))

		self.update_prevdoc_status()
		self.update_billing_status()

		# Updating stock ledger should always be called after updating prevdoc status,
		# because updating ordered qty in bin depends upon updated ordered qty in PO
		self.update_stock_ledger()
		self.make_gl_entries_on_cancel()
		self.delete_auto_created_batches()

	def get_current_stock(self):
		for d in self.get('supplied_items'):
			if self.supplier_warehouse:
				bin = frappe.db.sql("select actual_qty from `tabBin` where item_code = %s and warehouse = %s", (d.rm_item_code, self.supplier_warehouse), as_dict = 1)
				d.current_stock = bin and flt(bin[0]['actual_qty']) or 0

	def get_gl_entries(self, warehouse_account=None):
		from erpnext.accounts.general_ledger import process_gl_map

		stock_rbnb = self.get_company_default("stock_received_but_not_billed")
		stock_rbnb_currency = get_account_currency(stock_rbnb)
		landed_cost_entries = get_item_account_wise_additional_cost(self.name)
		expenses_included_in_valuation = self.get_company_default("expenses_included_in_valuation")

		gl_entries = []
		warehouse_with_no_account = []
		negative_expense_to_be_booked = 0.0
		stock_items = self.get_stock_items()
		for d in self.get("items"):
			if d.item_code in stock_items and flt(d.valuation_rate) and flt(d.qty):
				if warehouse_account.get(d.warehouse):
					stock_value_diff = frappe.db.get_value("Stock Ledger Entry",
						{"voucher_type": "Purchase Receipt", "voucher_no": self.name,
						"voucher_detail_no": d.name, "warehouse": d.warehouse}, "stock_value_difference")

					if not stock_value_diff:
						continue

					# If PR is sub-contracted and fg item rate is zero
					# in that case if account for shource and target warehouse are same,
					# then GL entries should not be posted
					if flt(stock_value_diff) == flt(d.rm_supp_cost) \
						and warehouse_account.get(self.supplier_warehouse) \
						and warehouse_account[d.warehouse]["account"] == warehouse_account[self.supplier_warehouse]["account"]:
							continue

					gl_entries.append(self.get_gl_dict({
						"account": warehouse_account[d.warehouse]["account"],
						"against": stock_rbnb,
						"cost_center": d.cost_center,
						"remarks": self.get("remarks") or _("Accounting Entry for Stock"),
						"debit": stock_value_diff
					}, warehouse_account[d.warehouse]["account_currency"], item=d))

					# stock received but not billed
					if d.base_net_amount:
						gl_entries.append(self.get_gl_dict({
							"account": stock_rbnb,
							"against": warehouse_account[d.warehouse]["account"],
							"cost_center": d.cost_center,
							"remarks": self.get("remarks") or _("Accounting Entry for Stock"),
							"credit": flt(d.base_net_amount, d.precision("base_net_amount")),
							"credit_in_account_currency": flt(d.base_net_amount, d.precision("base_net_amount")) \
								if stock_rbnb_currency==self.company_currency else flt(d.net_amount, d.precision("net_amount"))
						}, stock_rbnb_currency, item=d))

					negative_expense_to_be_booked += flt(d.item_tax_amount)

					# Amount added through landed-cost-voucher
					if d.landed_cost_voucher_amount and landed_cost_entries:
						for account, amount in iteritems(landed_cost_entries[(d.item_code, d.name)]):
							gl_entries.append(self.get_gl_dict({
								"account": account,
								"against": warehouse_account[d.warehouse]["account"],
								"cost_center": d.cost_center,
								"remarks": self.get("remarks") or _("Accounting Entry for Stock"),
								"credit": flt(amount),
								"project": d.project
							}, item=d))

					# sub-contracting warehouse
					if flt(d.rm_supp_cost) and warehouse_account.get(self.supplier_warehouse):
						gl_entries.append(self.get_gl_dict({
							"account": warehouse_account[self.supplier_warehouse]["account"],
							"against": warehouse_account[d.warehouse]["account"],
							"cost_center": d.cost_center,
							"remarks": self.get("remarks") or _("Accounting Entry for Stock"),
							"credit": flt(d.rm_supp_cost)
						}, warehouse_account[self.supplier_warehouse]["account_currency"], item=d))

					# divisional loss adjustment
					valuation_amount_as_per_doc = flt(d.base_net_amount, d.precision("base_net_amount")) + \
						flt(d.landed_cost_voucher_amount) + flt(d.rm_supp_cost) + flt(d.item_tax_amount)

					divisional_loss = flt(valuation_amount_as_per_doc - stock_value_diff,
						d.precision("base_net_amount"))

					if divisional_loss:
						if self.is_return or flt(d.item_tax_amount):
							loss_account = expenses_included_in_valuation
						else:
							cogs_account = self.get_company_default("default_expense_account")
							loss_account = cogs_account

						gl_entries.append(self.get_gl_dict({
							"account": loss_account,
							"against": warehouse_account[d.warehouse]["account"],
							"cost_center": d.cost_center,
							"remarks": self.get("remarks") or _("Accounting Entry for Stock"),
							"debit": divisional_loss,
							"project": d.project
						}, stock_rbnb_currency, item=d))

				elif d.warehouse not in warehouse_with_no_account or \
					d.rejected_warehouse not in warehouse_with_no_account:
						warehouse_with_no_account.append(d.warehouse)

		self.get_asset_gl_entry(gl_entries)
		# Cost center-wise amount breakup for other charges included for valuation
		valuation_tax = {}
		for tax in self.get("taxes"):
			if tax.category in ("Valuation", "Valuation and Total") and flt(tax.base_tax_amount_after_discount_amount):
				if not tax.cost_center:
					frappe.throw(_("Cost Center is required in row {0} in Taxes table for type {1}").format(tax.idx, _(tax.category)))
				valuation_tax.setdefault(tax.name, 0)
				valuation_tax[tax.name] += \
					(tax.add_deduct_tax == "Add" and 1 or -1) * flt(tax.base_tax_amount_after_discount_amount)

		if negative_expense_to_be_booked  and valuation_tax:
			# Backward compatibility:
			# If expenses_included_in_valuation account has been credited in against PI
			# and charges added via Landed Cost Voucher,
			# post valuation related charges on "Stock Received But Not Billed"
			# introduced in 2014 for backward compatibility of expenses already booked in expenses_included_in_valuation account

			negative_expense_booked_in_pi = frappe.db.sql("""select name from `tabPurchase Invoice Item` pi
				where docstatus = 1 and purchase_receipt=%s
				and exists(select name from `tabGL Entry` where voucher_type='Purchase Invoice'
					and voucher_no=pi.parent and account=%s)""", (self.name, expenses_included_in_valuation))

			against_account = ", ".join([d.account for d in gl_entries if flt(d.debit) > 0])
			total_valuation_amount = sum(valuation_tax.values())
			amount_including_divisional_loss = negative_expense_to_be_booked
			i = 1
			for tax in self.get("taxes"):
				if valuation_tax.get(tax.name):

					if negative_expense_booked_in_pi:
						account = stock_rbnb
					else:
						account = tax.account_head

					if i == len(valuation_tax):
						applicable_amount = amount_including_divisional_loss
					else:
						applicable_amount = negative_expense_to_be_booked * (valuation_tax[tax.name] / total_valuation_amount)
						amount_including_divisional_loss -= applicable_amount

					gl_entries.append(
						self.get_gl_dict({
							"account": account,
							"cost_center": tax.cost_center,
							"credit": applicable_amount,
							"remarks": self.remarks or _("Accounting Entry for Stock"),
							"against": against_account
						}, item=tax)
					)

					i += 1

		if warehouse_with_no_account:
			frappe.msgprint(_("No accounting entries for the following warehouses") + ": \n" +
				"\n".join(warehouse_with_no_account))
		if (self.doctype == 'Purchase Receipt' and self.purchase_order_type == 'Import' and self.import_costing_sheet): # in case of landed cost import costing tax separate
			for d in gl_entries:
				if flt(d.debit) > 0:
					against_account = d.account
					break
			for tax in self.get("taxes"):
				if valuation_tax.get(tax.name):
					account = tax.account_head
					account_currency = get_account_currency(account)
					applicable_amount = tax.tax_amount
					#credit side
					gl_entries.append(
						self.get_gl_dict({
							"account": account,
							"cost_center": tax.cost_center,
							"credit": applicable_amount,
							"remarks": self.remarks or _("Accounting Entry for Stock"),
							"against": against_account
						}, item=tax, account_currency=account_currency)
					)
					# debit side
					gl_entries.append(
						self.get_gl_dict({
							"account": against_account,
							"cost_center": tax.cost_center,
							"debit": applicable_amount,
							"remarks": self.remarks or _("Accounting Entry for Stock"),
							"against": account
						}, item=tax, account_currency=account_currency)
					)
			
		return process_gl_map(gl_entries)

	def get_asset_gl_entry(self, gl_entries):
		for item in self.get("items"):
			if item.is_fixed_asset:
				if is_cwip_accounting_enabled(item.asset_category):
					self.add_asset_gl_entries(item, gl_entries)
				if flt(item.landed_cost_voucher_amount):
					self.add_lcv_gl_entries(item, gl_entries)
					# update assets gross amount by its valuation rate
					# valuation rate is total of net rate, raw mat supp cost, tax amount, lcv amount per item
					self.update_assets(item, item.valuation_rate)
		return gl_entries

	def add_asset_gl_entries(self, item, gl_entries):
		arbnb_account = self.get_company_default("asset_received_but_not_billed")
		# This returns category's cwip account if not then fallback to company's default cwip account
		cwip_account = get_asset_account("capital_work_in_progress_account", asset_category = item.asset_category, \
			company = self.company)

		if (self.doctype == 'Purchase Receipt' and self.purchase_order_type == 'Import' and self.import_costing_sheet): # in case of landed cost import costing tax separate
			base_asset_amount = flt(item.net_amount)
		else:
			asset_amount = flt(item.net_amount) + flt(item.item_tax_amount/self.conversion_rate)
			base_asset_amount = flt(item.base_net_amount + item.item_tax_amount)

		cwip_account_currency = get_account_currency(cwip_account)
		# debit cwip account
		gl_entries.append(self.get_gl_dict({
			"account": cwip_account,
			"against": arbnb_account,
			"cost_center": item.cost_center,
			"remarks": self.get("remarks") or _("Accounting Entry for Asset"),
			"debit": base_asset_amount,
			"debit_in_account_currency": (base_asset_amount
				if cwip_account_currency == self.company_currency else asset_amount)
		}, item=item))

		asset_rbnb_currency = get_account_currency(arbnb_account)
		# credit arbnb account
		gl_entries.append(self.get_gl_dict({
			"account": arbnb_account,
			"against": cwip_account,
			"cost_center": item.cost_center,
			"remarks": self.get("remarks") or _("Accounting Entry for Asset"),
			"credit": base_asset_amount,
			"credit_in_account_currency": (base_asset_amount
				if asset_rbnb_currency == self.company_currency else asset_amount)
		}, item=item))

	def add_lcv_gl_entries(self, item, gl_entries):
		expenses_included_in_asset_valuation = self.get_company_default("expenses_included_in_asset_valuation")
		if not is_cwip_accounting_enabled(item.asset_category):
			asset_account = get_asset_category_account(asset_category=item.asset_category, \
					fieldname='fixed_asset_account', company=self.company)
		else:
			# This returns company's default cwip account
			asset_account = get_asset_account("capital_work_in_progress_account", company=self.company)

		gl_entries.append(self.get_gl_dict({
			"account": expenses_included_in_asset_valuation,
			"against": asset_account,
			"cost_center": item.cost_center,
			"remarks": self.get("remarks") or _("Accounting Entry for Stock"),
			"credit": flt(item.landed_cost_voucher_amount),
			"project": item.project
		}, item=item))

		gl_entries.append(self.get_gl_dict({
			"account": asset_account,
			"against": expenses_included_in_asset_valuation,
			"cost_center": item.cost_center,
			"remarks": self.get("remarks") or _("Accounting Entry for Stock"),
			"debit": flt(item.landed_cost_voucher_amount),
			"project": item.project
		}, item=item))

	def update_assets(self, item, valuation_rate):
		assets = frappe.db.get_all('Asset',
			filters={ 'purchase_receipt': self.name, 'item_code': item.item_code }
		)

		for asset in assets:
			frappe.db.set_value("Asset", asset.name, "gross_purchase_amount", flt(valuation_rate))
			frappe.db.set_value("Asset", asset.name, "purchase_receipt_amount", flt(valuation_rate))

	def update_status(self, status):
		self.set_status(update=True, status = status)
		self.notify_update()
		clear_doctype_notifications(self)

	def update_billing_status(self, update_modified=True):
		updated_pr = [self.name]
		for d in self.get("items"):
			if d.purchase_order_item:
				updated_pr += update_billed_amount_based_on_po(d.purchase_order_item, update_modified)

		for pr in set(updated_pr):
			pr_doc = self if (pr == self.name) else frappe.get_doc("Purchase Receipt", pr)
			pr_doc.update_billing_percentage(update_modified=update_modified)

		self.load_from_db()

def update_billed_amount_based_on_po(po_detail, update_modified=True):
	# Billed against Sales Order directly
	billed_against_po = frappe.db.sql("""select sum(amount) from `tabPurchase Invoice Item`
		where po_detail=%s and (pr_detail is null or pr_detail = '') and docstatus=1""", po_detail)
	billed_against_po = billed_against_po and billed_against_po[0][0] or 0

	# Get all Delivery Note Item rows against the Sales Order Item row
	pr_details = frappe.db.sql("""select pr_item.name, pr_item.amount, pr_item.parent
		from `tabPurchase Receipt Item` pr_item, `tabPurchase Receipt` pr
		where pr.name=pr_item.parent and pr_item.purchase_order_item=%s
			and pr.docstatus=1 and pr.is_return = 0
		order by pr.posting_date asc, pr.posting_time asc, pr.name asc""", po_detail, as_dict=1)

	updated_pr = []
	for pr_item in pr_details:
		# Get billed amount directly against Purchase Receipt
		billed_amt_agianst_pr = frappe.db.sql("""select sum(amount) from `tabPurchase Invoice Item`
			where pr_detail=%s and docstatus=1""", pr_item.name)
		billed_amt_agianst_pr = billed_amt_agianst_pr and billed_amt_agianst_pr[0][0] or 0

		# Distribute billed amount directly against PO between PRs based on FIFO
		if billed_against_po and billed_amt_agianst_pr < pr_item.amount:
			pending_to_bill = flt(pr_item.amount) - billed_amt_agianst_pr
			if pending_to_bill <= billed_against_po:
				billed_amt_agianst_pr += pending_to_bill
				billed_against_po -= pending_to_bill
			else:
				billed_amt_agianst_pr += billed_against_po
				billed_against_po = 0

		frappe.db.set_value("Purchase Receipt Item", pr_item.name, "billed_amt", billed_amt_agianst_pr, update_modified=update_modified)

		updated_pr.append(pr_item.parent)

	return updated_pr

@frappe.whitelist()
def make_purchase_invoice(source_name, target_doc=None):
	from frappe.model.mapper import get_mapped_doc
	from erpnext.accounts.party import get_payment_terms_template

	doc = frappe.get_doc('Purchase Receipt', source_name)
	returned_qty_map = get_returned_qty_map(source_name)
	invoiced_qty_map = get_invoiced_qty_map(source_name)

	def set_missing_values(source, target):
		if len(target.get("items")) == 0:
			frappe.throw(_("All items have already been Invoiced/Returned"))

		doc = frappe.get_doc(target)
		doc.ignore_pricing_rule = 1
		doc.payment_terms_template = get_payment_terms_template(source.supplier, "Supplier", source.company)
		doc.run_method("onload")
		doc.run_method("set_missing_values")
		doc.run_method("calculate_taxes_and_totals")

	def update_item(source_doc, target_doc, source_parent):
		target_doc.qty, returned_qty = get_pending_qty(source_doc)
		returned_qty_map[source_doc.name] = returned_qty

	def get_pending_qty(item_row):
		pending_qty = item_row.qty - invoiced_qty_map.get(item_row.name, 0)
		returned_qty = flt(returned_qty_map.get(item_row.name, 0))
		if returned_qty:
			if returned_qty >= pending_qty:
				pending_qty = 0
				returned_qty -= pending_qty
			else:
				pending_qty -= returned_qty
				returned_qty = 0
		return pending_qty, returned_qty


	doclist = get_mapped_doc("Purchase Receipt", source_name,	{
		"Purchase Receipt": {
			"doctype": "Purchase Invoice",
			"field_map": {
				"supplier_warehouse":"supplier_warehouse",
				"is_return": "is_return",
				"bill_date": "bill_date"
			},
			"validation": {
				"docstatus": ["=", 1],
			},
		},
		"Purchase Receipt Item": {
			"doctype": "Purchase Invoice Item",
			"field_map": {
				"name": "pr_detail",
				"parent": "purchase_receipt",
				"purchase_order_item": "po_detail",
				"purchase_order": "purchase_order",
				"is_fixed_asset": "is_fixed_asset",
				"asset_location": "asset_location",
				"asset_category": 'asset_category'
			},
			"postprocess": update_item,
			"filter": lambda d: get_pending_qty(d)[0] <= 0 if not doc.get("is_return") else get_pending_qty(d)[0] > 0
		},
		"Purchase Taxes and Charges": {
			"doctype": "Purchase Taxes and Charges",
			"add_if_empty": True
		}
	}, target_doc, set_missing_values)

	return doclist

def get_invoiced_qty_map(purchase_receipt):
	"""returns a map: {pr_detail: invoiced_qty}"""
	invoiced_qty_map = {}

	for pr_detail, qty in frappe.db.sql("""select pr_detail, qty from `tabPurchase Invoice Item`
		where purchase_receipt=%s and docstatus=1""", purchase_receipt):
			if not invoiced_qty_map.get(pr_detail):
				invoiced_qty_map[pr_detail] = 0
			invoiced_qty_map[pr_detail] += qty

	return invoiced_qty_map

def get_returned_qty_map(purchase_receipt):
	"""returns a map: {so_detail: returned_qty}"""
	returned_qty_map = frappe._dict(frappe.db.sql("""select pr_item.purchase_receipt_item, abs(pr_item.qty) as qty
		from `tabPurchase Receipt Item` pr_item, `tabPurchase Receipt` pr
		where pr.name = pr_item.parent
			and pr.docstatus = 1
			and pr.is_return = 1
			and pr.return_against = %s
	""", purchase_receipt))

	return returned_qty_map

@frappe.whitelist()
def make_purchase_return(source_name, target_doc=None):
	from erpnext.controllers.sales_and_purchase_return import make_return_doc
	return make_return_doc("Purchase Receipt", source_name, target_doc)


@frappe.whitelist()
def update_purchase_receipt_status(docname, status):
	pr = frappe.get_doc("Purchase Receipt", docname)
	pr.update_status(status)

@frappe.whitelist()
def make_stock_entry(source_name,target_doc=None):
	def set_missing_values(source, target):
		target.stock_entry_type = "Material Transfer"
		target.purpose =  "Material Transfer"

	doclist = get_mapped_doc("Purchase Receipt", source_name,{
		"Purchase Receipt": {
			"doctype": "Stock Entry",
		},
		"Purchase Receipt Item": {
			"doctype": "Stock Entry Detail",
			"field_map": {
				"warehouse": "s_warehouse",
				"parent": "reference_purchase_receipt"
			},
		},
	}, target_doc, set_missing_values)

	return doclist

def get_item_account_wise_additional_cost(purchase_document):
	landed_cost_vouchers = frappe.get_all("Landed Cost Purchase Receipt", fields=["parent"],
		filters = {"receipt_document": purchase_document, "docstatus": 1})

	if not landed_cost_vouchers:
		return

	item_account_wise_cost = {}

	for lcv in landed_cost_vouchers:
		landed_cost_voucher_doc = frappe.get_doc("Landed Cost Voucher", lcv.parent)
		based_on_field = frappe.scrub(landed_cost_voucher_doc.distribute_charges_based_on)
		total_item_cost = 0

		for item in landed_cost_voucher_doc.items:
			total_item_cost += item.get(based_on_field)

		for item in landed_cost_voucher_doc.items:
			if item.receipt_document == purchase_document:
				for account in landed_cost_voucher_doc.taxes:
					item_account_wise_cost.setdefault((item.item_code, item.purchase_receipt_item), {})
					item_account_wise_cost[(item.item_code, item.purchase_receipt_item)].setdefault(account.expense_account, 0.0)
					item_account_wise_cost[(item.item_code, item.purchase_receipt_item)][account.expense_account] += \
						account.amount * item.get(based_on_field) / total_item_cost

	return item_account_wise_cost

@frappe.whitelist()
def delete_items(data):
	frappe.db.sql("""DELETE FROM `tabPurchase Receipt Item` WHERE parent ='{name}';""".format(name =data))
	frappe.db.commit()


# def update_valuation_rate_for_subcontracting(doc):
# 	if not doc.subcontracted:
# 		return
	
# 	# Considering purchase receipt can be created against only one purchase order (not multiple purchase orders)
# 	purchase_order_reference = None
# 	for item in doc.items:
# 		if item.purchase_order:
# 			purchase_order_reference = item.purchase_order
# 			break

# 	valuation_rates = frappe.db.sql(
# 		f"""
# 		SELECT sed.`batch_no` as `batch_no`, sed.`item_code` as `item_code`, sed.`valuation_rate` as `valuation_rate` FROM `tabStock Entry` se
# 		INNER JOIN `tabStock Entry Detail` sed
# 		ON sed.`parent`=se.`name`
# 		WHERE se.`purchase_order`={frappe.db.escape(purchase_order_reference)}
# 		AND se.`stock_entry_type`="Send to Subcontractor";
# 		""", as_dict=True
# 	)

# 	valuation_batchwise_data = {}
# 	for valuation_rate in valuation_rates:
# 		if valuation_rate.get('item_code') not in valuation_batchwise_data:
# 			valuation_batchwise_data[valuation_rate.get('item_code')] = {}

# 		if valuation_rate.get('batch_no') not in valuation_batchwise_data[valuation_rate.get('item_code')]:
# 			valuation_batchwise_data[valuation_rate.get('item_code')][valuation_rate.get('batch_no')] = valuation_rate.get('valuation_rate')


# 	for supplied_item in doc.supplied_items:
# 		if supplied_item.rm_item_code in valuation_batchwise_data and supplied_item.batch_no in valuation_batchwise_data[supplied_item.rm_item_code]:
# 			supplied_item.rate = valuation_batchwise_data[supplied_item.rm_item_code][supplied_item.batch_no]
# 			supplied_item.amount = supplied_item.rate * supplied_item.consumed_qty


@frappe.whitelist()
def create_documents_flow(docname):
	from datetime import datetime
	items = {
		"po_items": [],
		"so_items": []
	}
	try:
		doc = frappe.get_doc("Purchase Receipt", docname)
		# Get appropriate company
		company = frappe.get_value("Supplier", doc.supplier, "represents_company")

		# Get appropriate customer
		customer, price_list = frappe.get_value("Customer", {"represents_company": doc.company}, ["name", "default_price_list"])

		for dt in doc.items:
			items["so_items"].append({
				"item_code": dt.get("item_code"),
				"qty": dt.get("qty"),
				"discount_percentage": 0.0,
				"doctype": "Sales Order Item"
			})
			items["po_items"].append({
				"item_code": dt.get("item_code"),
				"qty": dt.get("qty"),
				"discount_percentage": 0.0,
				"doctype": "Purchase Order Item"
			})

		# Create Purchase Order
		po_dict = {
			"doctype": "Purchase Order",
			"company": company,
			"supplier": doc.sub_contractor,
			"request_from": "SubContractor",
			"purchase_order_type": "Local",
			"subcontracted": 1,
			"is_subcontracted": "Yes",
			"schedule_date": datetime.today().strftime('%Y-%m-%d'),
			"items": items.get("po_items", []),
			"against_document": doc.name
		}
		
		purchase_order = frappe.get_doc(po_dict)
		purchase_order.save(ignore_permissions=True)
		purchase_order.submit()
		frappe.db.commit()

		# Create Sales Order
		so_dict = {
			"doctype": "Sales Order",
			"company": company,
			"customer": customer,
			"delivery_date": datetime.today().strftime('%Y-%m-%d'),
			"order_type": "Sales",
			"request_from": "SubContractor",
			"items": items.get("so_items", []),
			"against_document": doc.name,
			"sub_contractor": doc.sub_contractor,
			"selling_price_list": price_list
		}

		sales_order = frappe.get_doc(so_dict)
		sales_order.save(ignore_permissions=True)
		sales_order.submit()
		frappe.db.commit()

	except Exception as error:
		frappe.db.rollback()
		traceback = frappe.get_traceback()
		frappe.log_error(message=traceback, title=f"Error creating documents flow from Purchase Receipt: {doc.name}.")
		doc.add_comment('Comment', _('Action Failed') + '<br><br>' + str(error))


@frappe.whitelist()
def create_purchase_invoice(docname):
	from datetime import datetime
	try:
		frappe.db.commit()
		doc = frappe.get_doc("Purchase Receipt", docname)

		pi_items = []
		for dt in doc.items:
			pi_items.append({
				"item_code": dt.get("item_code"),
				"qty": dt.get("qty"),
				"discount_percentage": 0.0,
				"purchase_order": dt.purchase_order,
				"purchase_receipt": doc.name,
				"doctype": "Purchase Invoice Item"
			})

		pi_dict = {
			"doctype": "Purchase Invoice",
			"company": doc.company,
			"supplier": doc.supplier,
			"is_subcontracted": "Yes",
			"posting_date": datetime.today().strftime('%Y-%m-%d'),
			"due_date": datetime.today().strftime('%Y-%m-%d'),
			"posting_time": datetime.today().strftime('%H:%M:%S.%f'),
			"items": pi_items,
			"supplier_warehouse": doc.supplier_warehouse
		}

		purchase_invoice = frappe.get_doc(pi_dict)
		purchase_invoice.save(ignore_permissions=True)
		frappe.db.commit()
	except Exception as e:
		frappe.db.rollback()
		traceback = frappe.get_traceback()
		frappe.log_error(message=traceback, title=f"Error while creating PI from purchase receipt: {doc.name}.")
		doc.add_comment('Comment', _('Action Failed') + '<br><br>' + str(e))
