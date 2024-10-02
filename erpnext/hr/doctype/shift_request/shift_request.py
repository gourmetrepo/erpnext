# -*- coding: utf-8 -*-
# Copyright (c) 2018, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

from __future__ import unicode_literals
import frappe
import json
from frappe import _
from frappe.model.document import Document
from frappe.utils import formatdate, getdate

class OverlapError(frappe.ValidationError): pass

class ShiftRequest(Document):
	def validate(self):
		self.validate_dates()
		self.validate_shift_request_overlap_dates()
	def submit(self):
		self.queue_action('submit',queue_name="hr_secondary", enqueue_after_commit=True)
	def on_submit(self):
		frappe.enqueue("erpnext.hr.doctype.shift_request.shift_request.create_shift_assignment", queue='hr_secondary', doc=self, enqueue_after_commit=True)

	def on_cancel(self):
		shift_assignment_list = frappe.get_list("Shift Assignment", {'employee': self.employee, 'shift_request': self.name})
		if shift_assignment_list:
			for shift in shift_assignment_list:
				shift_assignment_doc = frappe.get_doc("Shift Assignment", shift['name'])
				shift_assignment_doc.cancel()


	def validate_dates(self):
		if self.from_date and self.to_date and (getdate(self.to_date) < getdate(self.from_date)):
			frappe.throw(_("To date cannot be before from date"))

	def validate_shift_request_overlap_dates(self):
			if not self.name:
				self.name = "New Shift Request"

			d = frappe.db.sql("""
				select
					name, shift_type, from_date, to_date
				from `tabShift Request`
				where employee = %(employee)s and docstatus < 2
				and ((%(from_date)s >= from_date
					and %(from_date)s <= to_date) or
					( %(to_date)s >= from_date
					and %(to_date)s <= to_date ))
				and name != %(name)s""", {
					"employee": self.employee,
					"shift_type": self.shift_type,
					"from_date": self.from_date,
					"to_date": self.to_date,
					"name": self.name
				}, as_dict=1)

			for date_overlap in d:
				if date_overlap ['name']:
					self.throw_overlap_error(date_overlap)

	def throw_overlap_error(self, d):
		msg = _("Employee {0} has already applied for {1} between {2} and {3} : ").format(self.employee,
			d['shift_type'], formatdate(d['from_date']), formatdate(d['to_date'])) \
			+ """ <b><a href="#Form/Shift Request/{0}">{0}</a></b>""".format(d["name"])
		frappe.throw(msg, OverlapError)

	def get_working_days(self, start_date, end_date):
		start_date, end_date = getdate(start_date), getdate(end_date)

		from datetime import timedelta

		date_list = []
		employee_holiday_list = []

		employee_holidays = frappe.db.sql("""select holiday_date from `tabHoliday`
								where parent in (select holiday_list from `tabEmployee`
								where name = %s)""",self.employee,as_dict=1)

		for d in employee_holidays:
			employee_holiday_list.append(d.holiday_date)

		reference_date = start_date
		
		while reference_date <= end_date:
			if reference_date not in employee_holiday_list:
				date_list.append(reference_date)
			reference_date += timedelta(days=1)

		return date_list


@frappe.whitelist()
def create_shift_assignment(doc):
	try:
		doc_list = []
		date_list = doc.get_working_days(doc.from_date, doc.to_date)
		for date in date_list:
			assignment_doc = frappe.new_doc("Shift Assignment")
			assignment_doc.company = doc.company
			assignment_doc.shift_type = doc.shift_type
			assignment_doc.employee = doc.employee
			assignment_doc.date = date
			assignment_doc.shift_request = doc.name
			assignment_doc.save()
			doc_list.append(assignment_doc.name)
		submit_shift_assignment(doc_list)
	except Exception as e:
		frappe.db.rollback()
		# add a comment (?)
		if frappe.local.message_log:
			msg = json.loads(frappe.local.message_log[-1]).get('message')
		else:
			msg = '<pre><code>' + frappe.get_traceback() + '</pre></code>'

		doc.add_comment('Comment', _('Action Failed') + '<br><br>' + msg)
		frappe.log_error(title="Shift Assignment Exception", message=f"An exception occurred while saving shift assignment: {e}")


def submit_shift_assignment(doc_names):
	if doc_names:
		try:			
			for name in doc_names:
				shift_assignment_doc = frappe.get_doc("Shift Assignment", name)
				shift_assignment_doc.submit()
		except Exception as e:
			frappe.log_error(title="Shift Assignment Exception", message=f"An exception occurred while submitting shift assignment: {e}")
