# -*- coding: utf-8 -*-
# Copyright (c) 2017, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

from __future__ import unicode_literals
import frappe
from frappe.model.document import Document
from frappe.desk.form import assign_to
from frappe import throw, _
from frappe.utils import add_days, add_months, add_years, getdate, nowdate

class AssetMaintenance(Document):
	def validate(self):
		for task in self.get('asset_maintenance_tasks'):
			if task.end_date and (getdate(task.start_date) >= getdate(task.end_date)):
				throw(_("Start date should be less than end date for task {0}").format(task.maintenance_task))
			if getdate(task.next_due_date) < getdate(nowdate()):
				task.maintenance_status = "Overdue"
			if not task.assign_to and self.docstatus == 0:
				throw(_("Row #{}: Please asign task to a member.").format(task.idx))
	
	def before_save(self):
		self.load_section_details()

	def on_update(self):
		for task in self.get('asset_maintenance_tasks'):
			assign_tasks(self.name, task.assign_to, task.maintenance_task, task.next_due_date)
		self.sync_maintenance_tasks()

	def sync_maintenance_tasks(self):
		tasks_names = []
		for task in self.get('asset_maintenance_tasks'):
			tasks_names.append(task.name)
			update_maintenance_log(asset_maintenance = self.name, item_code = self.item_code, item_name = self.item_name, task = task)
		asset_maintenance_logs = frappe.get_all("Asset Maintenance Log", fields=["name"], filters = {"asset_maintenance": self.name,
			"task": ("not in", tasks_names)})
		if asset_maintenance_logs:
			for asset_maintenance_log in asset_maintenance_logs:
				maintenance_log = frappe.get_doc('Asset Maintenance Log', asset_maintenance_log.name)
				maintenance_log.db_set('maintenance_status', 'Cancelled')

	
	def issue_mr_for_bill_of_material_and_services(self):
		try:
			mr_reference = make_issue_material_request(self)
			if self.status == "Draft":
				self.status = "MR Generated"
			return {'mr_reference': mr_reference.name}
		except Exception as e:
			frappe.log_error(e, "Plant Maintenance Issue Material Request Failed")
			frappe.throw("Issue Material Request Failed")
		
	def load_section_details(self):
		if self.company and self.section:
			data = frappe.db.sql(
				f"""
				SELECT `wip_warehouse`, `damage_warehouse` FROM `tabSection Warehouse`
				WHERE `parent`="{self.section}"
				AND `company`="{self.company}"
				""", as_dict=True
			)

			if len(data) > 0 and data[0].get('wip_warehouse'):
				self.wip_warehouse = data[0].get('wip_warehouse', None)
				self.damage_warehouse = data[0].get('damage_warehouse', None)
			else:
				frappe.throw(f"Please do warehouse configuration for section {self.section} in company {self.company}")
		else:
			frappe.throw("Please select a company and a section")

@frappe.whitelist()
def assign_tasks(asset_maintenance_name, assign_to_member, maintenance_task, next_due_date):
	team_member = frappe.db.get_value('User', assign_to_member, "email")
	args = {
		'doctype' : 'Asset Maintenance',
		'assign_to' : team_member,
		'name' : asset_maintenance_name,
		'description' : maintenance_task,
		'date' : next_due_date
	}
	if not frappe.db.sql("""select owner from `tabToDo`
		where reference_type=%(doctype)s and reference_name=%(name)s and status="Open"
		and owner=%(assign_to)s""", args):
		assign_to.add(args)

@frappe.whitelist()
def calculate_next_due_date(periodicity, start_date = None, end_date = None, last_completion_date = None, next_due_date = None):
	if not start_date and not last_completion_date:
		start_date = frappe.utils.now()

	if last_completion_date and ((start_date and last_completion_date > start_date) or not start_date):
		start_date = last_completion_date
	if periodicity == 'Daily':
		next_due_date = add_days(start_date, 1)
	if periodicity == 'Weekly':
		next_due_date = add_days(start_date, 7)
	if periodicity == 'Monthly':
		next_due_date = add_months(start_date, 1)
	if periodicity == 'Yearly':
		next_due_date = add_years(start_date, 1)
	if periodicity == '2 Yearly':
		next_due_date = add_years(start_date, 2)
	if periodicity == 'Quarterly':
		next_due_date = add_months(start_date, 3)
	if end_date and ((start_date and start_date >= end_date) or (last_completion_date and last_completion_date >= end_date) or next_due_date):
		next_due_date = ""
	return next_due_date


def update_maintenance_log(asset_maintenance, item_code, item_name, task):
	asset_maintenance_log = frappe.get_value("Asset Maintenance Log", {"asset_maintenance": asset_maintenance,
		"task": task.name, "maintenance_status": ('in',['Planned','Overdue'])})

	if not asset_maintenance_log:
		asset_maintenance_log = frappe.get_doc({
			"doctype": "Asset Maintenance Log",
			"asset_maintenance": asset_maintenance,
			"asset_name": asset_maintenance,
			"item_code": item_code,
			"item_name": item_name,
			"task": task.name,
			"has_certificate": task.certificate_required,
			"description": task.description,
			"assign_to_name": task.assign_to_name,
			"periodicity": str(task.periodicity),
			"maintenance_type": task.maintenance_type,
			"due_date": task.next_due_date
		})
		asset_maintenance_log.insert()
	else:
		maintenance_log = frappe.get_doc('Asset Maintenance Log', asset_maintenance_log)
		maintenance_log.assign_to_name = task.assign_to_name
		maintenance_log.has_certificate = task.certificate_required
		maintenance_log.description = task.description
		maintenance_log.periodicity = str(task.periodicity)
		maintenance_log.maintenance_type = task.maintenance_type
		maintenance_log.due_date = task.next_due_date
		maintenance_log.save()

@frappe.whitelist()
@frappe.validate_and_sanitize_search_inputs
def get_team_members(doctype, txt, searchfield, start, page_len, filters):
	return frappe.db.get_values('Maintenance Team Member', { 'parent': filters.get("maintenance_team") }, "team_member")

@frappe.whitelist()
def get_maintenance_log(asset_name):
    return frappe.db.sql("""
        select maintenance_status, count(asset_name) as count, asset_name
        from `tabAsset Maintenance Log`
        where asset_name=%s group by maintenance_status""",
        (asset_name), as_dict=1)




# Code by Moeiz
@frappe.whitelist()
def get_available_stock_for_bill_and_services(item_code, company):
    # Query to get the total stock for the specified item code and company
    stock_data = frappe.db.sql("""
        SELECT 
            SUM(actual_qty) AS total_qty
        FROM 
            `tabStock Ledger Entry`
        WHERE 
            item_code = %s AND company = %s
    """, (item_code, company), as_dict=True)
    
    # Return the total stock quantity, defaulting to 0 if no record is found
    total_qty = stock_data[0].get("total_qty", 0) if stock_data else 0
    return total_qty


def get_warehouse(item, company):
    warehouse = frappe.db.get_list('Item Default',
                                   filters={
                                       'company': company,
                                       'parent': item
                                   },
                                   fields=['company', 'default_warehouse'],
                                   as_list=True)
    if warehouse:
        return warehouse[0]
    else:
        frappe.throw(_("""Warehouse does not found in item {item} for company {company}""".format(item=item,company=company)))




def make_issue_material_request(doc):  
	mr = frappe.new_doc("Material Request")
	mr.material_request_type = "Material Transfer"
	mr.company = doc.company
	mr.title="Material Issue for Asset Maintenance"
	mr.naming_series="MAT-MR-.YYYY.-"
	mr_items_list = []
	for item in doc.bill_of_material_and_services:
		if not item.mr_reference:
			warehouse=get_warehouse(item.item,doc.company)
			i={}
			i['item_code']= item.item
			i["qty"]= item.demand_qty
			i["uom"]= item.uom 
			i["conversion_factor"]= 1
			i["warehouse"]=warehouse[1]
			i["asset_maintenance"] = doc.name
			i["warehouse"] = doc.wip_warehouse
			
			if doc.project_based == "Yes" and \
				(doc.project is not None and doc.project != ""):
				i["project"] = doc.project

			mr_items_list.append(i)
		else:
			continue
	
	if mr_items_list:
		mr.extend("items", mr_items_list)
		mr.insert(ignore_permissions=True)
		mr.submit()
		return mr
	else:
		frappe.throw("Please add new items to BOM to create material request for issue")


@frappe.whitelist()
def get_received_qty_from_material_request(mr_references):
	if isinstance(mr_references, str):
		import json
		mr_references = json.loads(mr_references)

	if not frappe.has_permission('Material Request Item', 'read'):
		frappe.throw(_("You do not have permission to access Material Request Items."))

	mr_ref_query = "'" + "','".join(mr_references) + "'"
	items = frappe.db.sql(f"""
			SELECT tmri.parent, tmri.item_code, tmri.qty FROM `tabMaterial Request` AS tmr
			LEFT JOIN `tabMaterial Request Item` AS tmri ON tmr.name = tmri.parent
			WHERE tmr.docstatus = 1 AND tmri.parent in ({mr_ref_query});""", as_dict=True, debug=True)
	
	return items


@frappe.whitelist()
def get_team_members(maintenance_teams):
    if isinstance(maintenance_teams, str):
        maintenance_teams = frappe.parse_json(maintenance_teams)
    
    team_members = frappe.get_all(
        'Maintenance Team Member',
        filters={'parent': ['in', maintenance_teams]},
        fields=['team_member']
    )
    return [member.team_member for member in team_members]




