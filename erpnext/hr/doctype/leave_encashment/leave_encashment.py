# -*- coding: utf-8 -*-
# Copyright (c) 2018, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

from __future__ import unicode_literals
import frappe
from frappe import _
from frappe.model.document import Document
from frappe.utils import getdate, nowdate, flt
from erpnext.hr.utils import set_employee_name
from erpnext.hr.doctype.salary_structure_assignment.salary_structure_assignment import get_assigned_salary_structure
from erpnext.hr.doctype.leave_ledger_entry.leave_ledger_entry import create_leave_ledger_entry
from erpnext.hr.doctype.leave_allocation.leave_allocation import get_unused_leaves
from nerp.utils import get_month_interval_dates

class LeaveEncashment(Document):
	def validate(self):
		set_employee_name(self)
		self.get_leave_details_for_encashment()

		if not self.encashment_date:
			self.encashment_date = getdate(nowdate())

	def before_submit(self):
		if self.encashment_amount <= 0:
			frappe.throw(_("You can only submit Leave Encashment for a valid encashment amount"))

	def on_submit(self):
		if not self.leave_allocation:
			self.leave_allocation = self.get_leave_allocation().get('name')
		additional_salary = frappe.new_doc("Additional Salary")
		additional_salary.company = frappe.get_value("Employee", self.employee, "company")
		additional_salary.employee = self.employee
		additional_salary.salary_component = frappe.get_value("Leave Type", self.leave_type, "earning_component")
		additional_salary.payroll_date = self.encashment_date
		additional_salary.amount = self.encashment_amount
		additional_salary.submit()

		self.db_set("additional_salary", additional_salary.name)

		# Set encashed leaves in Allocation
		frappe.db.set_value("Leave Allocation", self.leave_allocation, "total_leaves_encashed",
				frappe.db.get_value('Leave Allocation', self.leave_allocation, 'total_leaves_encashed') + self.encashable_days)

		self.create_leave_ledger_entry()

	def on_cancel(self):
		if self.additional_salary:
			frappe.get_doc("Additional Salary", self.additional_salary).cancel()
			self.db_set("additional_salary", "")

		if self.leave_allocation:
			frappe.db.set_value("Leave Allocation", self.leave_allocation, "total_leaves_encashed",
				frappe.db.get_value('Leave Allocation', self.leave_allocation, 'total_leaves_encashed') - self.encashable_days)
		self.create_leave_ledger_entry(submit=False)

	def get_leave_details_for_encashment(self):
		salary_structure = salary_structure_custom(self.employee, self.encashment_date or getdate(nowdate()))
		if not salary_structure:
			frappe.throw(_("No Salary Structure assigned for Employee {0} on given date {1}").format(self.employee, self.encashment_date))

		if not frappe.db.get_value("Leave Type", self.leave_type, 'allow_encashment'):
			frappe.throw(_("Leave Type {0} is not encashable").format(self.leave_type))

		leave_type = frappe.db.get_value('Leave Encashment', {"employee":self.employee, "leave_type":self.leave_type, "docstatus":1}, "leave_type")
		if leave_type:
			leaves = frappe.db.sql("""
						SELECT
							SUM(lle.leaves) as leave_sum
						FROM `tabLeave Allocation` as la
						INNER JOIN `tabLeave Type` as lt
						ON la.`leave_type` = lt.`name`
						INNER JOIN `tabLeave Ledger Entry` as lle
						ON lt.`name` = lle.`leave_type`
						WHERE
							la.docstatus = 1
							AND la.employee=%s
							AND lle.employee=%s
					""", (self.employee, self.employee), as_dict=1)
			if leaves[0]['leave_sum'] <= 0:
				frappe.throw(_("Leave Encashment is already applied: {0} for Leave Type: {1}").format(self.employee, self.leave_type))
		elif leave_type != None:
			frappe.throw(_("Leave Encashment is already applied: {0} for Leave Type: {1}").format(self.employee, self.leave_type))

		allocation = self.get_leave_allocation()

		if not allocation:
			frappe.throw(_("No Leaves Allocated to Employee: {0} for Leave Type: {1}").format(self.employee, self.leave_type))

		self.leave_balance = allocation.total_leaves_allocated - allocation.carry_forwarded_leaves_count\
			+ get_unused_leaves(self.employee, self.leave_type, allocation.from_date, self.encashment_date)

		encashable_days = self.leave_balance - frappe.db.get_value('Leave Type', self.leave_type, 'encashment_threshold_days')

		# set max encashable days to 28 (ticket no: 965)
		# if encashable_days > get_config_by_name('ENCASHMENT_DAYS'):
		#     encashable_days = get_config_by_name('ENCASHMENT_DAYS')
		# Change it to the leave type maximum encashable days
		maximum_encashable_days = frappe.db.get_value("Leave Type", self.leave_type, 'maximum_encashable_days')
		if maximum_encashable_days:
			maximum_encashable_days = float(maximum_encashable_days)
			if encashable_days > maximum_encashable_days:
				encashable_days = maximum_encashable_days
		self.encashable_days = encashable_days if encashable_days > 0 else 0

		# comment this one after discussion with rameez
		# per_day_encashment = frappe.db.get_value('Salary Structure', salary_structure[0] , 'leave_encashment_amount_per_day')
		# self.encashment_amount = self.encashable_days * per_day_encashment if per_day_encashment > 0 else 0

		# leave encashment rate work (ticket no. 966)
		base_salary = salary_structure[1]
		month_interval = get_month_interval_dates(self.encashment_date)
		month_days = month_interval[1] - month_interval[0]
		total_month_days = month_days.days
		total_month_days = total_month_days + 1
		self.encashment_rate = base_salary / total_month_days if base_salary > 0 else 0
		self.encashment_amount = self.encashment_rate * self.encashable_days
		self.leave_allocation = allocation.name
		return True

	def get_leave_allocation(self):
		leave_allocation = frappe.db.sql("""select name, from_date, to_date, total_leaves_allocated, carry_forwarded_leaves_count from `tabLeave Allocation` where '{0}'
		between from_date and to_date and docstatus=1 and leave_type='{1}'
		and employee= '{2}'""".format(self.encashment_date or getdate(nowdate()), self.leave_type, self.employee), as_dict=1) #nosec

		return leave_allocation[0] if leave_allocation else None

	def create_leave_ledger_entry(self, submit=True):
		args = frappe._dict(
			leaves=self.encashable_days * -1,
			from_date=self.encashment_date,
			to_date=self.encashment_date,
			is_carry_forward=0
		)
		create_leave_ledger_entry(self, args, submit)

		# create reverse entry for expired leaves
		leave_allocation = self.get_leave_allocation()
		if not leave_allocation:
			return

		to_date = leave_allocation.get('to_date')
		if to_date < getdate(nowdate()):
			args = frappe._dict(
				leaves=self.encashable_days,
				from_date=to_date,
				to_date=to_date,
				is_carry_forward=0
			)
			create_leave_ledger_entry(self, args, submit)


def create_leave_encashment(leave_allocation):
	''' Creates leave encashment for the given allocations '''
	for allocation in leave_allocation:
		if not get_assigned_salary_structure(allocation.employee, allocation.to_date):
			continue
		leave_encashment = frappe.get_doc(dict(
			doctype="Leave Encashment",
			leave_period=allocation.leave_period,
			employee=allocation.employee,
			leave_type=allocation.leave_type,
			encashment_date=allocation.to_date
		))
		leave_encashment.insert(ignore_permissions=True)


def salary_structure_custom(employee, on_date):
	if not employee or not on_date:
		return None
	salary_structure = frappe.db.sql("""
		select salary_structure, base from `tabSalary Structure Assignment`
		where employee=%(employee)s
		and docstatus = 1
		and %(on_date)s >= from_date order by from_date desc limit 1""", {
			'employee': employee,
			'on_date': on_date,
		})
	return salary_structure[0] if salary_structure else None
