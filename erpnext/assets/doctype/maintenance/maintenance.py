# -*- coding: utf-8 -*-
# Copyright (c) 2024, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

from __future__ import unicode_literals
import frappe
from frappe.model.document import Document
from erpnext.manufacturing.doctype.work_order.work_order import stop_unstop

class Maintenance(Document):

	def before_save(self):
		get_flavour_and_pack_changes(self)

		if self.task == "CIP":
			if self.cip_type == "Flavour Change":
				get_flavour_change_setup(self)
			elif self.cip_type == "Pack Change":
				get_pack_change_setup(self)
			elif self.cip_type == "Flavor & Pack Change":
				get_flavour_pack_change_setup(self)
			elif self.cip_type == "General":
				get_general_setup()
	
	def mark_cip_inprogress(self):
		# Stop the work order if CIP document goes in progress
		if self.workflow_state == "CIP Inprogress" and self.work_order_id:
			stop_unstop(self.work_order_id, "Stopped")
		
		return self.workflow_state


	def before_submit(self):
		self.mark_cip_finished()

	def mark_cip_finished(self):
		# Resume the work order if CIP document is finished
		if self.work_order_id and self.workflow_state == "CIP Finished" and self.cip_type == "General":
			stop_unstop(self.work_order_id, "Resumed")



def get_flavour_and_pack_changes(maintenance_doc):
	
	# Get flavour from and pack from for production item
	production_item_flavour_pack = frappe.db.sql(f"""
		SELECT 
			parent_item.item_name as flavour, 
			child_item.reporting_variant as pack 
		FROM 
			`tabItem` AS child_item
		LEFT JOIN 
			`tabItem` AS parent_item ON parent_item.name = child_item.variant_of
		WHERE 
			child_item.name = '{maintenance_doc.work_order_item}'
	""", as_dict=True)

	if production_item_flavour_pack:
		flavour_from = production_item_flavour_pack[0].get('flavour')
		pack_from = production_item_flavour_pack[0].get('pack')
	else:
		flavour_from = None
		pack_from = None
	
	maintenance_doc.change_flavour_from = flavour_from
	maintenance_doc.change_pack_from = pack_from

	# Get flavour to and pack to for selected item we move to
	to_item_flavour_pack = frappe.db.sql(f"""
		SELECT 
			parent_item.item_name as flavour, 
			child_item.reporting_variant as pack 
		FROM 
			`tabItem` AS child_item
		LEFT JOIN 
			`tabItem` AS parent_item ON parent_item.name = child_item.variant_of
		WHERE 
			child_item.name = '{maintenance_doc.change_item_to}'
	""", as_dict=True)

	if to_item_flavour_pack:
		flavour_to = to_item_flavour_pack[0].get('flavour')
		pack_to = to_item_flavour_pack[0].get('pack')
	else:
		flavour_to = None
		pack_to = None
	
	maintenance_doc.flavour_change_to = flavour_to
	maintenance_doc.change_pack_to = pack_to



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

	if cip_steps or not standard_time:
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
	""", {"from_flavor": maintenance_doc.change_flavour_from, "cip_section": maintenance_doc.section}, as_dict=True)

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
	pass