# Copyright (c) 2015, Frappe Technologies Pvt. Ltd. and Contributors
# License: GNU General Public License v3. See license.txt

from __future__ import unicode_literals
import frappe

def get_notification_config():
	doctypes = {}
	if frappe.session.user == 'zubair@gourmetpakistan.com':
		doctypes = {
			"Journal Entry": {"docstatus": 0,"workflow_state":("not like","Rejected%")},
			"Payment Entry": {"docstatus": 0,"workflow_state":("not like","Rejected%")},
			"Purchase Order": {
				"status": ("not in", ("Completed", "Closed")),
				"docstatus": ("<", 2),
				"workflow_state":("not like","Rejected%")
			},
			"BOM": {"docstatus": 0,"workflow_state":("not like","Rejected%")},
			"Payment Order": {"docstatus":0,"workflow_state":("not like","Rejected%")},
			"Employee": {"docstatus":0,"workflow_state":("not like","Rejected%")},
			"Expense Entry": {"docstatus":0,"workflow_state":("not like","Rejected%")},
			"Customer":{"docstatus":0,"workflow_state":("not like","Rejected%")},
			"Supplier":{"docstatus":0,"workflow_state":("not like","Rejected%")},
			"Item Daily Rate": {"docstatus":0,"workflow_state":("not like","Rejected%")},
			"Payment Advice": {"docstatus":0,"workflow_state":("not like","Rejected%")},
		}
	
	notifications =  { 
		"for_doctype": doctypes,
		"targets": {
			"Company": {
				"filters" : { "monthly_sales_target": ( ">", 0 ) },
				"target_field" : "monthly_sales_target",
				"value_field" : "total_monthly_sales"
			}
		}
	}

	if frappe.session.user != 'zubair@gourmetpakistan.com':
		user_roles = frappe.db.sql(f"""SELECT group_concat(CONCAT('"',ROLE,'"')) FROM `tabHas Role` WHERE parent = '{frappe.session.user}'""")
		if user_roles[0][0] != None:
			docper_user = frappe.db.sql(f"""SELECT parent FROM `tabDocPerm` WHERE ROLE IN ({user_roles[0][0]})""")
			if docper_user[0][0] != None:
				role_doctype = frappe.db.sql(f"""SELECT NAME FROM `tabDocType` WHERE NAME IN ({docper_user[0][0]})""",as_dict=True)
				doctype = [d.NAME for d in role_doctype]
				doctyps_workflow = ['Journal Entry','Payment Entry','Purchase Invoice','Sales Invoice','Payment Order','Purchase Order','Supplier Quotation','Request for Quotation','Leave Application','Attendance','Loan','Payroll Entry','Shift Assignment','Additional Salary','Attendance Request','Loan Application','Shift Request','BOM','Production Plan','Work Order','Annual Increments','Payment Advice','Manual Disbursement','Item Daily Rate','Gate Pass','Expense Entry','Batch Payment Request','Sales Order','Stock Entry','Purchase Receipt','Stock Reconciliation','Material Request']
				for doc in frappe.get_all('DocType',fields= ["name"], filters = {"name": ("in", doctype), 'is_submittable': 1}):
					if doc.name in doctyps_workflow:
						notifications["for_doctype"][doc.name] = {"docstatus": 0,"workflow_state":("not like","Rejected%")}
					else:
						notifications["for_doctype"][doc.name] = {"docstatus": 0}
	return notifications
