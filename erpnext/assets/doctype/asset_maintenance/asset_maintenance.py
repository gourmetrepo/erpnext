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
		self.validate_item_replacement_and_scrap()
		self.validate_assets()
	
	def before_save(self):
		""""
		1. If the document is not project based, it's Annual General Project and in that case maintenance tasks would be added by the user itself.
		Asset maintenance reference would be assigned to tasks in this case using sync maintenance tasks.
		2. If the document is project based, asset maintenance reference is assigned to tasks when fetching using Fetch Project Tasks button
		3. Load Project would be executed only the first time document is being created
		4. Tasks would be validated only if document state has not gone to In Process yet
		5. Section details would keep loading from the database unless all warehouses are fetched from the section master data
		"""
		if self.project_based == "No":
			if self.is_new():
				self.load_project()
			self.sync_maintenance_tasks()
		self.validate_tasks()
		self.load_section_details()

	def load_project(self):
		"""
		Load the most recent 'Annual General' project for the company.
		If no such project exists, raise an exception.
		"""
		# Query to fetch the latest 'Annual General' project for the given company
		annual_general_project = frappe.db.sql(f"""
			SELECT `name` FROM `tabProject` 
			WHERE `project_type`="Annual General" 
			AND `company`="{self.company}"
			AND `status`="Open"
			ORDER BY creation DESC LIMIT 1;
			""", as_dict=True)

		# Check if any project was found
		if annual_general_project and annual_general_project[0].get('name'):
			self.project = annual_general_project[0].get('name')
		else:
			frappe.throw(
				f"Please create an Annual General Project to proceed for company {self.company}"
			)

	def before_submit(self):
		"""
		Validations before submitting the Asset Maintenance document.
		- Raises an exception if the clearing account is not set for non project based asset maintenance.
		- Creates Damage and Scrap stock entries.
		"""
		if self.project_based == "No" and not self.clearing_account:
			frappe.throw("Please set clearing account to proceed for non project based asset maintenance. Contact support team for more information.")

		if self.status != "Closed" or self.status != "Finished":
			frappe.throw("Asset Maintenance cannot be submitted if its status is not Closed or Finished.")
		
		# Create Damage and Scrap stock entries
		self.create_damage_and_scrap_stock_entries()

		# Logging closing time in the document
		self.closed_time = frappe.utils.now_datetime()
	
	def on_submit(self):
		"""
		Creates a project based journal entry if the document is not project based.
		"""
		if self.project_based == "No":
			# Create a project based journal entry if the document is not project based
			self.create_project_based_journal_entry()
		
		# Update repair count at assets
		self.update_repair_count()

		
	def sync_maintenance_tasks(self):
		tasks_names = [task.get('maintenance_task') for task in self.get('asset_maintenance_tasks')]
		if tasks_names:
			tasks_with_no_reference_tuple = f"({', '.join(frappe.db.escape(name) for name in tasks_names)})"
			
			frappe.db.sql(f"""
				Update `tabTask` SET `asset_maintenance`="{self.name}" where `name` in {tasks_with_no_reference_tuple} and asset_maintenance IS NULL;
			""")
			
			users_task = frappe.db.sql(
			f"""
				SELECT `employee`, `parent` FROM `tabTask Assigned Employee` WHERE `parent` in {tasks_with_no_reference_tuple};
			""", as_dict=True
			)

			mapped_task_users = {}
			for user_task in users_task:
				if user_task.get('parent') not in mapped_task_users:
					mapped_task_users[user_task.get('parent')] = ""
				mapped_task_users[user_task.get('parent')] += user_task.get('employee') + ", "

			for task in self.get('asset_maintenance_tasks'):
				task.assigned_users = mapped_task_users.get(task.get('maintenance_task'))	
			
			frappe.db.commit()

	
	def issue_mr_for_bill_of_material_and_services(self):
		"""
		This method would be used to issue Material Requests for the services and materials which are part of the Bill of Materials for the maintenance tasks.
		It will update the status of the document to MR Generated if the status is Draft.
		"""
		try:
			mr_reference = make_issue_material_request(self)
			if self.status == "Draft":
				self.status = "MR Generated"
			# Update the Asset Maintenance document with the Material Request reference
			update_issue_material(self, mr_reference)
			return {'mr_reference': mr_reference.name}
		except Exception as e:
			frappe.log_error(e, "Plant Maintenance Issue Material Request Failed")
			frappe.throw("Issue Material Request Failed")
		
	def load_section_details(self):
		# Load section details if all warehouses are not fetched from the section master data
		if self.company and self.section:
			if not self.wip_warehouse or not self.damage_warehouse or not self.scrap_warehouse:
				data = frappe.db.sql(
					f"""
					SELECT `wip_warehouse`, `damage_warehouse`, `scrap_warehouse` FROM `tabSection Warehouse`
					WHERE `parent`="{self.section}"
					AND `company`="{self.company}"
					""", as_dict=True
				)

				if len(data) > 0 and data[0].get('wip_warehouse'):
					if not self.wip_warehouse:
						self.wip_warehouse = data[0].get('wip_warehouse', None)
					if not self.damage_warehouse:
						self.damage_warehouse = data[0].get('damage_warehouse', None)
					if not self.scrap_warehouse:
						self.scrap_warehouse = data[0].get('scrap_warehouse', None)
				else:
					frappe.throw(f"Please do warehouse configuration for section {self.section} in company {self.company}")
		else:
			frappe.throw("Please select a company and a section")
	

	# Called on Fetch Project Tasks button and would be called only for Project based 'Yes'
	def load_tasks(self):
		if self.get('project'):
			tasks = frappe.db.sql(
				f"""
				SELECT `name`, `exp_start_date`
				FROM `tabTask`
				WHERE `project`="{self.get('project')}" and `status`="Open" and `asset_maintenance` IS NULL;
				""", as_dict=True
			)

			tasks_names = tuple([task.get('name') for task in tasks])
			if tasks_names:
				formatted_tasks_names = f"""({', '.join([f"'{name}'" for name in tasks_names])})"""
				users_task = frappe.db.sql(
					f"""
					SELECT `employee`, `parent` FROM `tabTask Assigned Employee` WHERE `parent` in {formatted_tasks_names};
					""", as_dict=True
				)

				mapped_task_users = {}
				for user_task in users_task:
					if user_task.get('parent') not in mapped_task_users:
						mapped_task_users[user_task.get('parent')] = ""
					mapped_task_users[user_task.get('parent')] += user_task.get('employee') + ", "


				tasks_names_references_to_be_updated = [task.get('name') for task in tasks]
				if tasks_names_references_to_be_updated:
					task_names_tuple = f"({', '.join(frappe.db.escape(name) for name in tasks_names_references_to_be_updated)})"
					frappe.db.sql(f"""
						Update `tabTask` set `asset_maintenance`="{self.name}" where `name` in {task_names_tuple};
					""")
					frappe.db.commit()
				
				for task in tasks:
					task['assigned_users'] = mapped_task_users.get(task.get('name'))
				
				return {'tasks': tasks}
			else:
				frappe.throw("No tasks available for this project")

	def validate_tasks(self):
		# Validate tasks duplication
		distinct_tasks = set()
		for task in self.get('asset_maintenance_tasks'):
			if task.get('maintenance_task') in distinct_tasks:
				frappe.throw(f"Task {task.get('maintenance_task')} is already added in the above rows and can be assigned only once. Please check Row#: {task.idx}")
			distinct_tasks.add(task.get('maintenance_task'))
			
		# Validate tasks if document has not gone in process state
		if self.status not in ("Draft", "MR Generated", "Not Started"):
			tasks_names = [task.get('maintenance_task') for task in self.get('asset_maintenance_tasks')]
			
			if tasks_names:
				task_names_referenece = f"({', '.join(frappe.db.escape(name) for name in tasks_names)})"
				asset_maintenance_references = frappe.db.sql(f"""
					SELECT distinct(`asset_maintenance`), `name` FROM `tabTask` WHERE `name` in {task_names_referenece};
				""", as_dict=True)

				for asset_maintenance_reference in asset_maintenance_references:
					if not asset_maintenance_reference.get('asset_maintenance'):
						frappe.throw(f"Task {asset_maintenance_reference.get('name')} is not assigned to any Asset Maintenance. Please use Get Project Tasks button to fetch this task")
					elif asset_maintenance_reference.get('asset_maintenance') != self.name:
						frappe.throw(f"Task {asset_maintenance_reference.get('name')} is already assigned to another Asset Maintenance {asset_maintenance_reference.get('asset_maintenance')}")

	def validate_assets(self):
		# Validate assets duplication
		distinct_assets = set()
		for asset in self.get('plant_maintenance_assets'):
			if asset.get('asset') in distinct_assets:
				frappe.throw(f"Asset {asset.get('asset')} is already added in the above rows and can be assigned only once. Please check Row#: {asset.idx}")
			distinct_assets.add(asset.get('asset'))

	def validate_item_replacement_and_scrap(self):
		"""
		Validate items for replacement and scrap.

		This function checks the items listed for replacement and repair.
		It ensures that each item has the necessary details filled out and 
		that appropriate warehouse configurations are set up for damaged and scrap items.

		Raises:
			frappe.exceptions.ValidationError: If any required field is missing or 
			if warehouse configurations are not set for damaged or scrap items.
		"""
		for item in self.get('items_replacement_and_repair'):
			# Ensure 'item', 'qty', and 'remarks' fields are filled
			if not item.get('item') or not item.get('qty') or not item.get('remarks'):
				frappe.throw(f"Item, Qty and Remarks are mandatory if you are adding items for replacement and repair. Please check Row#: {item.idx}")

			# Check for damage warehouse configuration if item is marked as damaged
			if item.get('remarks') == "Damaged" and not self.get('damage_warehouse'):
				frappe.throw("Please setup damage warehouse configuration at section master data to proceed with damaged items")

			# Check for scrap warehouse configuration if item is marked as scrap
			if item.get('remarks') == "Scrap" and not self.get('scrap_warehouse'):
				frappe.throw("Please setup scrap warehouse configuration at section master data to proceed with scrap items")


	def create_damage_and_scrap_stock_entries(self):
		"""
		Create stock entries for items marked as 'Damaged' or 'Scrap'.

		This function iterates through the items listed for replacement and repair.
		If any item is marked as 'Damaged', it triggers the creation of a damage stock entry.
		If any item is marked as 'Scrap', it triggers the creation of a scrap stock entry.
		Commits the transaction to the database after each stock entry creation.
		"""
		create_damage_stock_entry = False
		create_scrap_stock_entry = False

		# Determine if there are any items marked as 'Damaged' or 'Scrap'
		for item in self.get('items_replacement_and_repair'):
			if item.get('remarks') == "Damaged":
				create_damage_stock_entry = True
			if item.get('remarks') == "Scrap":
				create_scrap_stock_entry = True
		
		# Create a stock entry for damaged items if any exist
		if create_damage_stock_entry:
			make_damage_stock_entry(self)
			frappe.db.commit()
		
		# Create a stock entry for scrap items if any exist
		if create_scrap_stock_entry:
			make_scrap_stock_entry(self)
			frappe.db.commit()
	
	def create_project_based_journal_entry(self):
		"""
		Create a journal entry for project-based asset maintenance.

		This function creates a system-generated journal entry for plant maintenance if a clearing account is specified.
		It calculates the total cost from GL entries related to stock entries marked for material issue and associates 
		them with the asset maintenance document. The calculated total cost is then used to create debit and credit entries.
		"""
		if self.clearing_account:
			# Initialize a new Journal Entry document
			jv_doc = frappe.new_doc('Journal Entry')
			jv_doc.voucher_type = "Journal Entry"
			jv_doc.company = self.company
			jv_doc.generated = "System Generated"
			jv_doc.plant_maintenance_reference = self.name
			jv_doc.user_remark = "Journal Entry for Plant Maintenance"

			# Query total cost from GL Entry based on stock entries associated with this maintenance
			total_cost_from_db = frappe.db.sql(
				f""" 
				SELECT SUM(gl.`debit`) as total_amount
				FROM `tabGL Entry` gl
				WHERE gl.`voucher_no` IN (
					SELECT DISTINCT se.`name`
					FROM `tabStock Entry` se
					JOIN `tabStock Entry Detail` sed ON se.`name` = sed.`parent`
					WHERE sed.`asset_maintenance` = "{self.name}"
					AND se.`stock_entry_type` = "Material Issue"
					AND se.`docstatus` = 1
				);
				""", as_dict=True
			)

			# Check if any cost was retrieved and proceed with journal entry creation
			if len(total_cost_from_db) > 0 and total_cost_from_db[0].get('total_amount'):
				total_cost = total_cost_from_db[0].get('total_amount')

				# Create a debit entry in the journal
				debit_account_entry = frappe.new_doc('Journal Entry Account')
				debit_account_entry.update({
					'account': self.clearing_account,
					'debit_in_account_currency': total_cost,
				})
				jv_doc.append('accounts', debit_account_entry)

				# Create a credit entry in the journal
				credit_account_entry = frappe.new_doc('Journal Entry Account')
				credit_account_entry.update({
					'account': self.clearing_account,
					'credit_in_account_currency': total_cost,
				})
				jv_doc.append('accounts', credit_account_entry)

				# Save the journal entry document
				jv_doc.save()
				frappe.db.commit()
			else:
				# Delete the journal entry document if no cost was retrieved
				del jv_doc
	
	def update_repair_count(self):
		"""
		Update the repair count for each asset in the asset maintenance document.
		"""

		asset_names = [asset.get('asset') for asset in self.get('plant_maintenance_assets')]
		
		if asset_names:
			asset_names_referenece = f"({', '.join(frappe.db.escape(name) for name in asset_names)})"
			frappe.db.sql(f"""
				Update `tabAsset` set `repair_count`=(`repair_count` + 1) where `name` in {asset_names_referenece};
			""", as_dict=True)
		



@frappe.whitelist()
def assign_tasks(asset_maintenance_name, assign_to_member, maintenance_task, next_due_date):
	team_member = frappe.db.get_value('Employee', assign_to_member, "user_id")
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




# Code by Moeiz
@frappe.whitelist()
def get_available_stock_for_bill_and_services(item_code, company):
	"""
	Fetch the total available stock quantity for a given item code and company.

	Args:
	item_code (str): The code of the item to check stock for.
	company (str): The name of the company to check stock within.

	Returns:
	float: The total available stock quantity for the specified item and company.
	"""

	if not item_code:
		frappe.throw("Please add an item code to issue bill and services")
	
	# Execute a SQL query to get the total stock for the specified item code and company
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
	"""
	Create a Material Request for the items in the Bill of Materials table of the Asset Maintenance document.

	This function is called when the Asset Maintenance document is submitted.
	"""
	mr = frappe.new_doc("Material Request")
	mr.material_request_type = "Material Transfer"
	mr.company = doc.company
	mr.title="Material Issue for Asset Maintenance"
	mr.naming_series="MAT-MR-.YYYY.-"
	mr_items_list = []

	if not doc.get('wip_warehouse', None):
		frappe.throw("Please set WIP warehouse in Asset Maintenance")

	# Get the expense account for the WIP warehouse
	warehouse_expense_account = frappe.db.sql(f"""
	SELECT `account` FROM `tabWarehouse` WHERE `name`="{doc.get('wip_warehouse')}";
	""", as_dict=True)

	expense_account = None

	if len(warehouse_expense_account) > 0 and warehouse_expense_account[0].get('account'):
		expense_account = warehouse_expense_account[0].get('account')

	if not expense_account:
		frappe.throw(f"Please set account for warehouse: {doc.wip_warehouse} in warehouse master data")

	# Loop through the items in the Bill of Materials table
	for item in doc.bill_of_material_and_services:
		# If the item does not have a Material Request reference, create a new Material Request item
		if not item.mr_reference:
			# Get the warehouse for the item
			warehouse=get_warehouse(item.item,doc.company)

			i={}
			i['item_code']= item.item
			i["qty"]= item.demand_qty
			i["uom"]= item.uom 
			i["conversion_factor"]= 1
			i["warehouse"]=warehouse[1]
			i["asset_maintenance"] = doc.name
			i["warehouse"] = doc.wip_warehouse
			i["source_warehouse"] = doc.source_warehouse
			i["expense_account"] = expense_account

			# If the document is project-based and has a project set, add the project to the Material Request item
			if doc.project_based == "Yes" and \
				(doc.project is not None and doc.project != ""):
				i["project"] = doc.project

			# Add the item to the Material Request items list
			mr_items_list.append(i)
		else:
			continue
	
	# If there are items in the Material Request items list, create a new Material Request document
	if mr_items_list:
		mr.extend("items", mr_items_list)
		mr.insert(ignore_permissions=True)
		mr.submit()
		return mr
	else:
		# If there are no items in the Material Request items list, throw an error
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
			WHERE tmr.docstatus = 1 AND tmri.parent in ({mr_ref_query});""", as_dict=True)
	
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

@frappe.whitelist()
def make_material_consumption_stock_entry(asset_maintenance_doc_ref):
	"""
	Create a stock entry to record the consumption of materials for the asset maintenance
	"""
	try:
		# Fetch the Asset Maintenance document
		asset_maintenance_doc = frappe.get_doc("Asset Maintenance", asset_maintenance_doc_ref)

		stock_entry = frappe.new_doc('Stock Entry')
		stock_entry.stock_entry_type = 'Material Issue'
		stock_entry.sub_branch = "Plant Maintenance"
		stock_entry.cost_association = "Plant Maintenance"
		# stock_entry
		stock_entry.company = asset_maintenance_doc.get('company')
		stock_entry.asset_maintenance = asset_maintenance_doc.get('name')
		stock_entry.from_warehouse = asset_maintenance_doc.get('wip_warehouse')

		difference_account = None

		# Determine the account to use for the difference
		if asset_maintenance_doc.get('project_based') == "Yes" and asset_maintenance_doc.get('project'):
			if asset_maintenance_doc.get('project_type') == "ADP" and asset_maintenance_doc.get('cwip_account'):
				difference_account = asset_maintenance_doc.get('cwip_account')
			elif asset_maintenance_doc.get('cogs_account'):
				difference_account = asset_maintenance_doc.get('cogs_account')
		elif asset_maintenance_doc.get('project_based') == "No" and asset_maintenance_doc.get('project'):
			difference_account = asset_maintenance_doc.get('clearing_account')

		# Throw an error if the account is not set
		if difference_account is None:
			if asset_maintenance_doc.get('project_based') == "Yes":
				frappe.throw("Please set CWIP or COGS account in project for project based asset maintenance")
			else:
				frappe.throw("Please set clearing account in asset maintenance for non project based asset maintenance in current Annual General Project")

		# Loop through the consumed items and create a stock entry detail for each one
		for item in asset_maintenance_doc.consumed_items:
			i = frappe.new_doc('Stock Entry Detail')
			i.s_warehouse =  asset_maintenance_doc.get('wip_warehouse')
			i.item_code =  item.get('item')
			i.qty = item.get('issued_qty') - item.get('consumed_qty')
			i.uom = item.get('uom')
			i.stock_uom = item.get('uom')
			i.asset_maintenance = asset_maintenance_doc.get('name')
			i.expense_account = difference_account
			i.project = asset_maintenance_doc.get('project', None)
			stock_entry.append('items',i)
		
		# Return the stock entry
		return stock_entry

	except Exception as e:
		frappe.log_error(frappe.get_traceback(), "Material Consumption Stock Entry Error")
		frappe.throw(_("An error occurred while creating the stock entry: {0}").format(str(e)))



@frappe.whitelist()
def make_return_stock_entry(asset_maintenance_doc_ref):
	"""
	Create a stock entry to transfer back the unused materials to the source warehouse

	Args:
		asset_maintenance_doc_ref (str): The name of the Asset Maintenance document

	Returns:
		dict: A dictionary containing the stock entry document and a flag indicating if a new stock entry was created
	"""
	try:
		# Fetch the Asset Maintenance document
		asset_maintenance_doc = frappe.get_doc("Asset Maintenance", asset_maintenance_doc_ref)

		# Create a new stock entry
		stock_entry = frappe.new_doc('Stock Entry')
		stock_entry.stock_entry_type = 'Material Transfer'
		stock_entry.company = asset_maintenance_doc.get('company')
		stock_entry.asset_maintenance = asset_maintenance_doc.get('name')
		stock_entry.from_warehouse = asset_maintenance_doc.get('wip_warehouse')

		return_stock_entry_flag = False

		# Loop through the consumed items and create a stock entry detail for each one
		for item in asset_maintenance_doc.consumed_items:
			# Calculate the quantity to return
			qty_to_return = (item.get('issued_qty') - item.get('consumed_qty')) - item.get('return_qty')
			if qty_to_return > 0:
				# Create a new stock entry detail
				i = frappe.new_doc('Stock Entry Detail')
				i.s_warehouse =  asset_maintenance_doc.get('wip_warehouse')
				i.item_code =  item.get('item')
				i.qty = qty_to_return
				i.uom = item.get('uom')
				i.stock_uom = item.get('uom')
				i.asset_maintenance = asset_maintenance_doc.get('name')
				i.project = asset_maintenance_doc.get('project', None)
				stock_entry.append('items',i)

				# Set the return stock entry flag to True
				return_stock_entry_flag = True

		# If no new stock entry was created, set the status of the Asset Maintenance document to the closing status
		if not return_stock_entry_flag:
			asset_maintenance_doc.status = get_closing_status(asset_maintenance_doc)
			asset_maintenance_doc.save()
			asset_maintenance_doc.submit()

		# Return the stock entry and the return stock entry flag
		return {'stock_entry': stock_entry, 'return_stock_entry_flag': return_stock_entry_flag}

	except Exception as e:
		frappe.log_error(frappe.get_traceback(), "Material Return Stock Entry Error")
		frappe.throw(_("An error occurred while creating the stock entry: {0}").format(str(e)))




def update_issue_material(asset_maintenance_doc, material_request_doc):

	for item in material_request_doc.items:
		item_exists = False
		for consumed_item in asset_maintenance_doc.consumed_items:
			if consumed_item.get('item') == item.get('item_code'):
				consumed_item.required_qty += item.get('qty')
				item_exists = True

		if not item_exists:
			child_doc = frappe.new_doc("Plant Maintenance Consumed Items")
			child_doc.item = item.get('item_code')
			child_doc.item_name = item.get('item_name')
			child_doc.required_qty = item.get('qty')
			child_doc.uom = item.get('uom')
			asset_maintenance_doc.append('consumed_items', child_doc)


@frappe.whitelist()
def get_assets(company, cost_center):
	if cost_center:
		assets = frappe.db.sql(
			f"""
			SELECT `name`, `asset_name`, `repair_count`, `cost_center`
			FROM `tabAsset`
			WHERE `cost_center` IN (
			SELECT `name`
			FROM `tabCost Center`
			WHERE `parent_cost_center`="{cost_center}" AND `company`="{company}");
			""", as_dict=True
		)
		return assets

def get_closing_status(asset_maintenance_doc):
	final_status = 'Finished'
	for task in asset_maintenance_doc.get('asset_maintenance_tasks'):
		if task.get('maintenance_status') != "Completed" and task.get('maintenance_status') != "Cancelled":
			final_status = 'Closed'
	return final_status


def make_damage_stock_entry(doc):
	damaged_items = []
	for item in doc.get('items_replacement_and_repair'):
		if item.get('remarks') == "Damaged":
			damaged_items.append(item)
	
	if damaged_items:
		stock_entry = frappe.new_doc('Stock Entry')
		stock_entry.stock_entry_type = 'Material Receipt'
		stock_entry.company = doc.get('company')
		stock_entry.asset_maintenance = doc.get('name')

		for item in damaged_items:
			i = frappe.new_doc('Stock Entry Detail')
			i.t_warehouse = doc.get('damage_warehouse')
			i.item_code =  item.get('item')
			i.qty = item.get('qty')
			i.uom = item.get('uom')
			i.stock_uom = item.get('uom')
			i.asset_maintenance = doc.get('name')
			i.project = doc.get('project', None)
			stock_entry.append('items',i)
			
		stock_entry.save()
		stock_entry.submit()



def make_scrap_stock_entry(doc):
	scrapping_items = []
	for item in doc.get('items_replacement_and_repair'):
		if item.get('remarks') == "Scrap":
			scrapping_items.append(item)
	
	if scrapping_items:
		stock_entry = frappe.new_doc('Stock Entry')
		stock_entry.stock_entry_type = 'Material Receipt'
		stock_entry.company = doc.get('company')
		stock_entry.asset_maintenance = doc.get('name')

		for item in scrapping_items:
			i = frappe.new_doc('Stock Entry Detail')
			i.t_warehouse = doc.get('scrap_warehouse')
			i.item_code =  item.get('item')
			i.qty = item.get('qty')
			i.uom = item.get('uom')
			i.stock_uom = item.get('uom')
			i.asset_maintenance = doc.get('name')
			i.project = doc.get('project', None)
			stock_entry.append('items',i)
			
		stock_entry.save()
		stock_entry.submit()


@frappe.whitelist()
def get_tasks(doctype, txt, searchfield, start, page_len, filters):
	company = filters.get("company", None)
	if company is None:
		frappe.throw(_("Please select a company before fetching tasks"))

	project_based = filters.get("project_based", None)
	if project_based is None:
		frappe.throw(_("Please selected if asset maintenance is project based or not"))
	
	if project_based == "Yes":
		project = filters.get("project", None)
		if project is None:
			frappe.throw(_("Please select a project before fetching tasks"))
					
		tasks = frappe.db.sql(f"""
			SELECT `name`, `subject` FROM `tabTask` 
			WHERE project="{project}"
			AND asset_maintenance IS NULL
		""")
	else:
		tasks = frappe.db.sql(f"""
			SELECT `name`, `subject` FROM `tabTask` 
			WHERE project=(SELECT `name` FROM `tabProject` 
			WHERE `project_type`="Annual General" 
			AND `company`="{company}"
			AND `status`="Open"
			ORDER BY creation DESC LIMIT 1)
			AND asset_maintenance IS NULL
		""")

	
	return tasks
@frappe.whitelist()
def create_jv_for_asset_maintenance(asset_maintenance_name):
	asset_maintenance_doc = frappe.get_doc("Asset Maintenance", asset_maintenance_name)
	asset_maintenance_doc.create_project_based_journal_entry()