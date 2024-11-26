# Copyright (c) 2015, Frappe Technologies Pvt. Ltd. and Contributors
# License: GNU General Public License v3. See license.txt

from __future__ import unicode_literals
import frappe
from frappe.model.document import Document
from erpnext.stock.doctype.quality_inspection_template.quality_inspection_template \
	import get_template_details
from frappe.model.mapper import get_mapped_doc

class QualityInspection(Document):
	def validate(self):
		if not self.readings and self.item_code:
			self.get_item_specification_details()

		parameters = get_template_details(self.quality_inspection_template)
		for reading in self.readings:
			matching_parameter = next((d for d in parameters if d["specification"] == reading.specification), None)

			if not matching_parameter:
				frappe.throw(f"Specification {reading.specification} not found in the template parameters.")

			expected_type = matching_parameter["type"]
			actual_type = type(reading.reading_1).__name__.capitalize()
			if expected_type == "String":
				if actual_type == "Str":
					actual_type = "String"

				if expected_type != actual_type:
					frappe.throw(f"Invalid type for {reading.specification}: expected {expected_type}, got {actual_type}.")

			if expected_type in ["Int", "Float"]:
				min_value = matching_parameter.get("min_value")
				max_value = matching_parameter.get("max_value")


				if min_value is not None:
					min_value = float(min_value) if expected_type == "Float" else int(min_value)
				if max_value is not None:
					max_value = float(max_value) if expected_type == "Float" else int(max_value)
					
				if expected_type != type(min_value).__name__.capitalize() or expected_type != type(max_value).__name__.capitalize():
					frappe.throw(f"Invalid type for {reading.specification}: expected {expected_type}, got {actual_type}.")

				if min_value is not None and max_value is not None:
					if expected_type == "Int":
						try:
							reading.reading_1 = float(reading.reading_1) if expected_type == "Float" else int(reading.reading_1)
						except ValueError:
							frappe.throw(f"Invalid value for {reading.specification}: {reading.reading_1} cannot be interpreted as an integer.")

					if expected_type != type(reading.reading_1).__name__.capitalize():
						frappe.throw(f"Invalid type for {reading.specification}: expected {expected_type}, got {actual_type}.")
     
					if not (min_value <= reading.reading_1 <= max_value):
						frappe.throw(f"Value for {reading.specification} is out of range: {reading.reading_1} not between {min_value} and {max_value}.")

	def get_item_specification_details(self):
		if not self.quality_inspection_template:
			self.company = frappe.db.get_value(self.reference_type, self.reference_name, 'company')

			purchase_check, delivery_check = frappe.db.get_value('Item', self.item_code, ['inspection_required_before_purchase', 'inspection_required_before_delivery'])

			# Fetch company wise quality inspection template from Item master
			if purchase_check or delivery_check:
				self.quality_inspection_template = frappe.db.get_value('Item Quality Inspection', {'parent': self.item_code, 'company': self.company}, 'quality_inspection_template')
			else:
				self.quality_inspection_template = ""

		if not self.quality_inspection_template: return

		self.set('readings', [])
		parameters = get_template_details(self.quality_inspection_template)
		for d in parameters:
			child = self.append('readings', {})
			child.specification = d.specification
			child.value = d.value
			child.status = "Accepted"

	def get_quality_inspection_template(self):
		template = ''
		if self.bom_no:
			template = frappe.db.get_value('BOM', self.bom_no, 'quality_inspection_template')

		if not template:
			template = frappe.db.get_value('BOM', self.item_code, 'quality_inspection_template')

		self.quality_inspection_template = template
		self.get_item_specification_details()

	def on_submit(self):
		self.update_qc_reference()

	def on_cancel(self):
		self.update_qc_reference()

	def update_qc_reference(self):
		quality_inspection = self.name if self.docstatus == 1 else ""
		doctype = self.reference_type + ' Item'
		if self.reference_type == 'Stock Entry':
			doctype = 'Stock Entry Detail'

		if self.reference_type and self.reference_name:
			conditions = ""
			if self.batch_no and self.docstatus == 1:
				conditions += " and t1.batch_no = '%s'"%(self.batch_no)

			if self.docstatus == 2: # if cancel, then remove qi link wherever same name
				conditions += " and t1.quality_inspection = '%s'"%(self.name)

			frappe.db.sql("""
				UPDATE
					`tab{child_doc}` t1, `tab{parent_doc}` t2
				SET
					t1.quality_inspection = %s, t2.modified = %s
				WHERE
					t1.parent = %s
					and t1.item_code = %s
					and t1.parent = t2.name
					{conditions}
			""".format(parent_doc=self.reference_type, child_doc=doctype, conditions=conditions),
				(quality_inspection, self.modified, self.reference_name, self.item_code))

	# Add method to avoid fetch_from in supplier and supplier_name fields
	def set_supplier_fields(self):
		if self.reference_type in ("Purchase Receipt", "Purchase Invoice", "Stock Entry"):
			sup_info = frappe.db.sql(f""" SELECT supplier, supplier_name FROM `tab{self.reference_type}` WHERE name="{self.reference_name}";""", as_dict=True)

			if sup_info:
				self.supplier = sup_info[0].get("supplier", "")
				self.supplier_name = sup_info[0].get("supplier_name", "")

@frappe.whitelist()
@frappe.validate_and_sanitize_search_inputs
def item_query(doctype, txt, searchfield, start, page_len, filters):
	if filters.get("from"):
		if filters.get("from") == "Work Order Item":
			return frappe.db.sql(f"""select production_item from `tabWork Order` where name="{filters.get("parent")}" and docstatus < 2;""")
		from frappe.desk.reportview import get_match_cond
		mcond = get_match_cond(filters["from"])
		cond, qi_condition = "", "and (quality_inspection is null or quality_inspection = '')"

		if filters.get('from') in ['Purchase Invoice Item', 'Purchase Receipt Item']\
				and filters.get("inspection_type") != "In Process":
			cond = """and item_code in (select name from `tabItem` where
				inspection_required_before_purchase = 1)"""
		elif filters.get('from') in ['Sales Invoice Item', 'Delivery Note Item']\
				and filters.get("inspection_type") != "In Process":
			cond = """and item_code in (select name from `tabItem` where
				inspection_required_before_delivery = 1)"""
		elif filters.get('from') == 'Stock Entry Detail':
			cond = """and s_warehouse is null"""

		if filters.get('from') in ['Supplier Quotation Item']:
			qi_condition = ""

		return frappe.db.sql(""" select item_code from `tab{doc}`
			where parent=%(parent)s and docstatus < 2 and item_code like %(txt)s
			{qi_condition} {cond} {mcond}
			order by item_code limit {start}, {page_len}""".format(doc=filters.get('from'),
			parent=filters.get('parent'), cond = cond, mcond = mcond, start = start,
			page_len = page_len, qi_condition = qi_condition),
			{'parent': filters.get('parent'), 'txt': "%%%s%%" % txt})

@frappe.whitelist()
@frappe.validate_and_sanitize_search_inputs
def wo_item_query(doctype, txt, searchfield, start, page_len, filters):
	if filters.get("doctype"):
		if filters.get("doctype") == "Work Order":
			return frappe.db.sql(f"""select production_item from `tabWork Order` where name="{filters.get("name")}" and docstatus < 2""")

@frappe.whitelist()
@frappe.validate_and_sanitize_search_inputs
def quality_inspection_query(doctype, txt, searchfield, start, page_len, filters):
	return frappe.get_all('Quality Inspection',
		limit_start=start,
		limit_page_length=page_len,
		filters = {
			'docstatus': 1,
			'name': ('like', '%%%s%%' % txt),
			'item_code': filters.get("item_code"),
			'reference_name': ('in', [filters.get("reference_name", ''), ''])
		}, as_list=1)

@frappe.whitelist()
def make_quality_inspection(source_name, target_doc=None):
	def postprocess(source, doc):
		doc.inspected_by = frappe.session.user
		doc.get_quality_inspection_template()

	doc = get_mapped_doc("BOM", source_name, {
		'BOM': {
			"doctype": "Quality Inspection",
			"validation": {
				"docstatus": ["=", 1]
			},
			"field_map": {
				"name": "bom_no",
				"item": "item_code",
				"stock_uom": "uom",
				"stock_qty": "qty"
			},
		}
	}, target_doc, postprocess)

	return doc
