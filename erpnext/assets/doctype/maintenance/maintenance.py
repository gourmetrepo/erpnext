# -*- coding: utf-8 -*-
# Copyright (c) 2024, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

from __future__ import unicode_literals
import math
import frappe
from frappe.model.document import Document
from erpnext.manufacturing.doctype.work_order.work_order import stop_unstop
from frappe.utils import get_datetime, time_diff

class Maintenance(Document):

	def before_save(self):
		"""
		Two categories of CIP:
			1. Planned CIP (Scheduled CIP)
			2. Unplanned CIP (Coming from work order)
		"""
		if self.task == "CIP":
			if self.cip_category == "Unplanned CIP":
				# get_flavour_and_pack_changes(self)
				self.setup_unplanned_cip()
			# elif self.cip_category == "Planned CIP":
			# 	self.setup_planned_cip()


	def setup_unplanned_cip(self):
		if self.cip_type == "Flavour Change":
			get_flavour_change_setup(self)
		elif self.cip_type == "Pack Change":
			get_pack_change_setup(self)
		elif self.cip_type == "Flavor & Pack Change":
			get_flavour_pack_change_setup(self)
		elif self.cip_type == "General":
			get_general_setup(self)
	

	def mark_cip_inprogress(self):
		try:
			# Check if already for the same line and company, a cip is already in progress
			inprocess_status = check_if_inprocess_cip(self)

			if inprocess_status:
				return "Already in progress"

			if not self.work_order_id:
				check_if_work_order_in_process(self)
			
			# Stop the work order if CIP document goes in progress
			if  self.workflow_state == "CIP Inprogress" and self.work_order_id:
				stop_unstop(self.work_order_id, "Stopped", self.name)
			
			self.cip_start_time = get_datetime()
			self.previous_workflow_state = self.workflow_state
			return self.workflow_state

		except Exception as e:
			# Rollback workflow state to Not Initiated
			frappe.db.sql(f"""UPDATE `tabMaintenance` SET workflow_state = 'Not Initiated' WHERE name = '{self.name}'""")
			frappe.db.commit()
			frappe.throw(str(e))
			frappe.log_error(frappe.get_traceback(), "Mark CIP Inprogress")

	def convert_minutes_to_hhmm(self, minutes):
		hours = minutes // 60
		remaining_minutes = minutes % 60

		formatted_hours = str(hours).zfill(2)
		formatted_minutes = str(remaining_minutes).zfill(2)

		return f"{formatted_hours}:{formatted_minutes}"

	def check_delay_before_submit(self):
		standard_time = self.standard_time
		standard_time_parts = standard_time.split(":")
		standard_time_total_minutes = (int(standard_time_parts[0]) * 60) + int(standard_time_parts[1])

		# Get the current time and CIP start time
		current_time = get_datetime()
		cip_start_time = self.cip_start_time

		# Calculate actual time elapsed
		actual_time_minutes = math.floor(time_diff(current_time, cip_start_time).total_seconds() / 60)
		delay_time_minutes = actual_time_minutes - standard_time_total_minutes
		
		if delay_time_minutes > 0:
			return True, actual_time_minutes, delay_time_minutes
		else:
			return False, actual_time_minutes, delay_time_minutes


	def before_submit(self):
		is_delayed, actual_time_minutes, delay_time_minutes = self.check_delay_before_submit()
		if is_delayed:
			if not self.delay_reason:
				frappe.throw("Please fill delay reason before marking CIP as finished")
		
			self.actual_time = self.convert_minutes_to_hhmm(actual_time_minutes)
			self.delay_time = self.convert_minutes_to_hhmm(delay_time_minutes)
			
		self.mark_cip_finished()

	def mark_cip_finished(self):
		# Resume the work order if CIP document is finished in case of Unplanned CIP
		if self.work_order_id and self.workflow_state == "CIP Finished" and self.cip_type == "General":
			work_order_status = frappe.db.get_value('Work Order', {'name': self.work_order_id}, 'status')
			if work_order_status == "Stopped":
				stop_unstop(self.work_order_id, "Resumed", self.name)
			elif work_order_status != "Closed":
				frappe.throw("Please contact support. The referenced work order has to be stopped or closed to finish CIP")

		self.cip_end_time = get_datetime()	


	def get_flavour_and_pack_changes_for_change_from(self):
		# Get flavour from and pack from for production item
		production_item_flavour_pack = frappe.db.sql(f"""
			SELECT 
				COALESCE(parent_item.item_name, child_item.reporting_flavor) as flavour, 
				child_item.reporting_variant as pack 
			FROM 
				`tabItem` AS child_item
			LEFT JOIN 
				`tabItem` AS parent_item ON parent_item.name = child_item.variant_of
			WHERE 
				child_item.name = '{self.work_order_item}'
		""", as_dict=True)

		if production_item_flavour_pack:
			flavour_from = production_item_flavour_pack[0].get('flavour')
			pack_from = production_item_flavour_pack[0].get('pack')
		else:
			flavour_from = None
			pack_from = None
		
		self.change_flavour_from = flavour_from
		self.change_pack_from = pack_from


	def get_flavour_and_pack_changes_for_change_to(self):
		# Get flavour to and pack to for selected item we move to for all cip types except general cip
		if self.cip_type != "General":
			to_item_flavour_pack = frappe.db.sql(f"""
				SELECT 
					COALESCE(parent_item.item_name, child_item.reporting_flavor) as flavour, 
					child_item.reporting_variant as pack 
				FROM 
					`tabItem` AS child_item
				LEFT JOIN 
					`tabItem` AS parent_item ON parent_item.name = child_item.variant_of
				WHERE 
					child_item.name = '{self.change_item_to}'
			""", as_dict=True)

			if to_item_flavour_pack:
				flavour_to = to_item_flavour_pack[0].get('flavour')
				pack_to = to_item_flavour_pack[0].get('pack')
			else:
				flavour_to = None
				pack_to = None
			
			self.flavour_change_to = flavour_to
			self.change_pack_to = pack_to


def get_flavour_pack_change_setup(maintenance_doc):
	cip_steps = None
	standard_time = None

	flavour_pack_change_setups = frappe.db.sql(f"""SELECT `to_flavor`, `to_pack`,`cip_steps`, `standard_time` FROM `tabCIP Standard Time` WHERE parent in (SELECT `name` FROM `tabCIP Standard Time Setup` WHERE `cip_type`='Flavour & Pack Change' AND `cip_section`='{maintenance_doc.section}') AND (`from_flavor`='{maintenance_doc.change_flavour_from}' AND `from_pack`='{maintenance_doc.change_pack_from}')""", as_dict=True)

	for flavour_pack_change_setup in flavour_pack_change_setups:
		if flavour_pack_change_setup.get('to_flavor', None) == maintenance_doc.flavour_change_to and flavour_pack_change_setup.get('to_pack', None) == maintenance_doc.change_pack_to and flavour_pack_change_setup.get('cip_steps', None) and flavour_pack_change_setup.get('standard_time', None):
			cip_steps = flavour_pack_change_setup.get('cip_steps')
			standard_time = flavour_pack_change_setup.get('standard_time')
		elif flavour_pack_change_setup.get('to_flavor', None) == "Any":
			if flavour_pack_change_setup.get('to_pack', None) == maintenance_doc.change_pack_to and flavour_pack_change_setup.get('cip_steps', None) and flavour_pack_change_setup.get('standard_time', None):
				cip_steps = flavour_pack_change_setup.get('cip_steps')
				standard_time = flavour_pack_change_setup.get('standard_time')
			elif flavour_pack_change_setup.get('to_pack', None) == "Any" and flavour_pack_change_setup.get('cip_steps', None) and flavour_pack_change_setup.get('standard_time', None):
				cip_steps = flavour_pack_change_setup.get('cip_steps')
				standard_time = flavour_pack_change_setup.get('standard_time')
		elif flavour_pack_change_setup.get('to_pack', None) == "Any":
			if flavour_pack_change_setup.get('to_flavor', None) == maintenance_doc.change_flavour_from and flavour_pack_change_setup.get('cip_steps', None) and flavour_pack_change_setup.get('standard_time', None):
				cip_steps = flavour_pack_change_setup.get('cip_steps')
				standard_time = flavour_pack_change_setup.get('standard_time')
			elif flavour_pack_change_setup.get('to_flavor', None) == "Any" and flavour_pack_change_setup.get('cip_steps', None) and flavour_pack_change_setup.get('standard_time', None):
				cip_steps = flavour_pack_change_setup.get('cip_steps')
				standard_time = flavour_pack_change_setup.get('standard_time')

	if not cip_steps or not standard_time:
		flavour_pack_change_setups = frappe.db.sql(f"""SELECT `from_flavor`, `from_pack`,`cip_steps`, `standard_time` FROM `tabCIP Standard Time` WHERE parent in (SELECT `name` FROM `tabCIP Standard Time Setup` WHERE `cip_type`='Flavour & Pack Change' AND `cip_section`='{maintenance_doc.section}') AND (`to_flavor`='{maintenance_doc.flavour_change_to}' AND `to_pack`='{maintenance_doc.change_pack_to}')""", as_dict=True)
		
		for flavour_pack_change_setup in flavour_pack_change_setups:
			if flavour_pack_change_setup.get('from_flavor', None) == maintenance_doc.change_flavour_from and flavour_pack_change_setup.get('from_pack', None) == maintenance_doc.change_pack_from and flavour_pack_change_setup.get('cip_steps', None) and flavour_pack_change_setup.get('standard_time', None):
				cip_steps = flavour_pack_change_setup.get('cip_steps')
				standard_time = flavour_pack_change_setup.get('standard_time')
			elif flavour_pack_change_setup.get('from_flavor', None) == "Any":
				if flavour_pack_change_setup.get('from_pack', None) == maintenance_doc.change_pack_from and flavour_pack_change_setup.get('cip_steps', None) and flavour_pack_change_setup.get('standard_time', None):
					cip_steps = flavour_pack_change_setup.get('cip_steps')
					standard_time = flavour_pack_change_setup.get('standard_time')
				elif flavour_pack_change_setup.get('from_pack', None) == "Any" and flavour_pack_change_setup.get('cip_steps', None) and flavour_pack_change_setup.get('standard_time', None):
					cip_steps = flavour_pack_change_setup.get('cip_steps')
					standard_time = flavour_pack_change_setup.get('standard_time')
			elif flavour_pack_change_setup.get('from_pack', None) == "Any":
				if flavour_pack_change_setup.get('from_flavor', None) == maintenance_doc.change_flavour_from and flavour_pack_change_setup.get('cip_steps', None) and flavour_pack_change_setup.get('standard_time', None):
					cip_steps = flavour_pack_change_setup.get('cip_steps')
					standard_time = flavour_pack_change_setup.get('standard_time')
				elif flavour_pack_change_setup.get('from_flavor', None) == "Any" and flavour_pack_change_setup.get('cip_steps', None) and flavour_pack_change_setup.get('standard_time', None):
					cip_steps = flavour_pack_change_setup.get('cip_steps')
					standard_time = flavour_pack_change_setup.get('standard_time')
	
	if cip_steps and standard_time:
		maintenance_doc.cip_steps = cip_steps
		maintenance_doc.standard_time = standard_time
	else:
		frappe.throw("No such mapping exists for this combination of flavour and pack")

def get_flavour_change_setup(maintenance_doc):
	cip_steps = None
	standard_time = None
	
	flavour_change_setups = frappe.db.sql("""
		SELECT to_flavor, cip_steps, standard_time
		FROM `tabCIP Standard Time`
		WHERE parent IN (SELECT name FROM `tabCIP Standard Time Setup` WHERE cip_type='Flavour Change' AND `cip_section`=%(cip_section)s)
		AND from_flavor=%(from_flavor)s
	""", {"from_flavor": maintenance_doc.change_flavour_from, "cip_section": maintenance_doc.section}, as_dict=True, debug=True)

	for setup in flavour_change_setups:
		if setup.to_flavor == maintenance_doc.flavour_change_to:
			cip_steps = setup.cip_steps
			standard_time = setup.standard_time
		elif setup.to_flavor == "Any":
			cip_steps = setup.cip_steps
			standard_time = setup.standard_time
	
	
	if not cip_steps or not standard_time:
		flavour_change_setups = frappe.db.sql("""
			SELECT from_flavor, cip_steps, standard_time
			FROM `tabCIP Standard Time`
			WHERE parent IN (SELECT name FROM `tabCIP Standard Time Setup` WHERE cip_type='Flavour Change' AND `cip_section`=%(cip_section)s)
			AND to_flavor=%(to_flavor)s
		""", {"to_flavor": maintenance_doc.flavour_change_to, "cip_section": maintenance_doc.section}, as_dict=True)

		for setup in flavour_change_setups:
			if setup.from_flavor == maintenance_doc.flavour_change_to:
				cip_steps = setup.cip_steps
				standard_time = setup.standard_time
			elif setup.from_flavor == "Any":
				cip_steps = setup.cip_steps
				standard_time = setup.standard_time

	
	if cip_steps and standard_time:
		maintenance_doc.cip_steps = cip_steps
		maintenance_doc.standard_time = standard_time
	else:
		frappe.throw("No such mapping exists for this combination of flavour and pack")
	
		
			

def get_pack_change_setup(maintenance_doc):
	cip_steps = None
	standard_time = None
	
	pack_change_setups = frappe.db.sql("""
		SELECT to_pack, cip_steps, standard_time
		FROM `tabCIP Standard Time`
		WHERE parent IN (SELECT name FROM `tabCIP Standard Time Setup` WHERE cip_type='Pack Change' AND `cip_section`=%(cip_section)s)
		AND from_pack=%(from_pack)s
	""", {"from_pack": maintenance_doc.change_pack_from, "cip_section": maintenance_doc.section}, as_dict=True)

	for setup in pack_change_setups:
		if setup.to_pack == maintenance_doc.change_pack_to:
			cip_steps = setup.cip_steps
			standard_time = setup.standard_time
		elif setup.to_pack == "Any":
			cip_steps = setup.cip_steps
			standard_time = setup.standard_time
	

	if not cip_steps or not standard_time:
		pack_change_setups = frappe.db.sql("""
			SELECT from_pack, cip_steps, standard_time
			FROM `tabCIP Standard Time`
			WHERE parent IN (SELECT name FROM `tabCIP Standard Time Setup` WHERE cip_type='Pack Change' AND `cip_section`=%(cip_section)s)
			AND to_pack=%(to_pack)s
		""", {"to_pack": maintenance_doc.change_pack_to, "cip_section": maintenance_doc.section}, as_dict=True)

		for setup in pack_change_setups:
			if setup.from_pack == maintenance_doc.change_pack_to:
				cip_steps = setup.cip_steps
				standard_time = setup.standard_time
			elif setup.from_pack == "Any":
				cip_steps = setup.cip_steps
				standard_time = setup.standard_time
	
	if cip_steps and standard_time:
		maintenance_doc.cip_steps = cip_steps
		maintenance_doc.standard_time = standard_time
	else:
		frappe.throw("No such mapping exists for this combination of flavour and pack")

def get_general_setup(maintenance_doc):
	general_change_setups = frappe.db.sql("""
		SELECT cip_steps, standard_time
		FROM `tabCIP Standard Time`
		WHERE parent IN (SELECT name FROM `tabCIP Standard Time Setup` WHERE cip_type='General' AND `cip_section`=%(cip_section)s)
	""", {"cip_section": maintenance_doc.section}, as_dict=True)

	if len(general_change_setups) > 0 and general_change_setups[0].get('cip_steps', None) and general_change_setups[0].get('standard_time', None):
		maintenance_doc.cip_steps = general_change_setups[0].get('cip_steps', None)
		maintenance_doc.standard_time = general_change_setups[0].get('standard_time', None)
	else:
		frappe.throw(f"No such mapping exists of general cip type for {maintenance_doc.section}")



def check_if_inprocess_cip(maintenance_doc):
	if maintenance_doc.cost_center:
		inprocess_cip = frappe.db.sql(f"""
			SELECT name
			FROM `tabMaintenance`
			WHERE `company` = %(company)s
			AND `name` != %(name)s
			AND `section` = %(section)s
			AND `task` = 'CIP' 
			AND `cost_center`=%(cost_center)s
			AND workflow_state = 'CIP Inprogress'
		""", {"company": maintenance_doc.company, "name": maintenance_doc.name,"section": maintenance_doc.section, "cost_center": maintenance_doc.cost_center})

		if inprocess_cip and len(inprocess_cip[0]) > 0:
			# Change workflow state of this document back to Not Initiated as workflow is first changed and then it comes to this document
			frappe.db.sql(f"""UPDATE `tabMaintenance` SET workflow_state = 'Not Initiated' WHERE name = '{maintenance_doc.name}'""")
			frappe.db.commit()
			frappe.msgprint(f"""Maintenance for this {maintenance_doc.cost_center} is already in progress: {inprocess_cip[0][0]}""")
			return True
	else:
		frappe.throw("Please select a cost center")



def check_if_work_order_in_process(maintenance_doc):
	# Check if work order is in process for the corresponding line and company
	work_order_data = frappe.db.get_list(
		'Work Order',
		filters={
			"company": maintenance_doc.company,
			"production_line": maintenance_doc.cost_center,
			"status": "In Process"
		},
		fields=['name', 'production_item', 'qty', 'produced_qty', 'company', 'item_name', 'production_line'],
		order_by='creation desc',
    	limit=1
	)
	if len(work_order_data) > 0 and work_order_data[0].get('name'):
		maintenance_doc.company = work_order_data[0].get('company')
		maintenance_doc.work_order_id = work_order_data[0].get('name')
		maintenance_doc.work_order_item = work_order_data[0].get('production_item')
		maintenance_doc.work_order_item_name = work_order_data[0].get('item_name')
		maintenance_doc.work_order_quantity = work_order_data[0].get('qty', 0)
		maintenance_doc.quantity_produced = work_order_data[0].get('produced_qty', 0)
		maintenance_doc.remaining_quantity = work_order_data[0].get('qty', 0) - work_order_data[0].get('produced_qty', 0)
		maintenance_doc.cost_center = work_order_data[0].get('production_line')