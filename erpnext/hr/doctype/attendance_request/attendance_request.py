# -*- coding: utf-8 -*-
# Copyright (c) 2018, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

from __future__ import unicode_literals
import frappe
from frappe import _
from frappe.model.document import Document
from frappe.utils import date_diff, add_days, getdate
from erpnext.hr.doctype.employee.employee import is_holiday
from erpnext.hr.utils import validate_dates
from nerp.constants.globals import STATUS_APPROVED, LOG_TYPE_IN, LOG_TYPE_OUT

class AttendanceRequest(Document):
	def validate(self):
		validate_dates(self, self.from_date, self.to_date)
		if self.half_day:
			if not getdate(self.from_date)<=getdate(self.half_day_date)<=getdate(self.to_date):
				frappe.throw(_("Half day date should be in between from date and to date"))
	def submit(self, *args, **kwargs):
		ignore_workflow = kwargs.get('ignore_workflow', False)
		self.queue_action('submit',queue_name="hr_secondary", enqueue_after_commit=True,ignore_workflow=ignore_workflow)

	def on_submit(self):
		self.create_attendance()

	def on_cancel(self):
		attendance_list = frappe.get_list("Attendance", {'employee': self.employee, 'attendance_request': self.name})
		if attendance_list:
			for attendance in attendance_list:
				attendance_obj = frappe.get_doc("Attendance", attendance['name'])
				attendance_obj.cancel()

	def create_attendance(self):
		if self.workflow_state != STATUS_APPROVED:
			return False
		request_days = date_diff(self.to_date, self.from_date) + 1
		holiday_dates = []
		for number in range(request_days):
			attendance_date = add_days(self.from_date, number)
			if is_holiday(self.employee, attendance_date):
					holiday_dates.append(attendance_date.strftime('%d/%m/%Y'))
			# skip_attendance = self.validate_if_attendance_not_applicable(attendance_date)
			# if not skip_attendance:
				### cancel old attendance if exists ###
			old_attendance_name = None
			try:
				old_attendance_name = frappe.db.get_value('Attendance',  {"employee": self.employee, "attendance_date": attendance_date, "docstatus": 1},"name")
				if(old_attendance_name):
					old_attendance = frappe.get_doc("Attendance", old_attendance_name)
					old_attendance.cancel()
					#del_ci_sql = "delete from `tabEmployee Checkin` where attendance = '{0}'".format(old_attendance_name)
					#frappe.db.sql(del_ci_sql)
			except Exception as error:
				frappe.log_error(message=error, title="Exception in Create Attendance")
				pass
			### cancel old attendance if exists ###
			activation_status=frappe.get_value("Employee", self.employee, "attendance_activation")
			attendance = frappe.new_doc("Attendance")
			attendance.employee = self.employee
			attendance.employee_name = self.employee_name
			if self.half_day and date_diff(getdate(self.half_day_date), getdate(attendance_date)) == 0:
				attendance.status = "Half Day"
			else:
				attendance.status = "Present"
			attendance.attendance_date = attendance_date
			attendance.company = self.company
			attendance.attendance_activation=activation_status
			attendance.attendance_request = self.name
			attendance.amended_from = old_attendance_name
			attendance.save(ignore_permissions=True)
			attendance.submit()
			# frappe.db.commit()
			# frappe.enqueue(method="nerp.nerp.report.provisional_salary_report.provisional_salary_report.single_employee_salary_data",employee=self.employee,date=attendance_date, queue='hr_primary',timeout=13000)
			if self.check_in:
				employee_checkin = frappe.new_doc("Employee Checkin")
				employee_checkin.employee = self.employee
				employee_checkin.attendance = attendance.name
				employee_checkin.log_type = LOG_TYPE_IN
				employee_checkin.time = self.check_in
				employee_checkin.save(ignore_permissions=True)
			if self.check_out:
				employee_checkout = frappe.new_doc("Employee Checkin")
				employee_checkout.employee = self.employee
				employee_checkout.attendance = attendance.name
				employee_checkout.log_type = LOG_TYPE_OUT
				employee_checkout.time = self.check_out
				employee_checkout.save(ignore_permissions=True)
		if is_holiday(self.employee, attendance_date):
			message = '<ul><li>' +'</li><li>'.join(holiday_dates) + "</ul>"    
			frappe.msgprint(message,'Attendance Submitted on Holiday(s):')

	def validate_if_attendance_not_applicable(self, attendance_date):
		# Check if attendance_date is a Holiday
		if is_holiday(self.employee, attendance_date):
			frappe.msgprint(_("Attendance not submitted for {0} as it is a Holiday.").format(attendance_date), alert=1)
			return True

		# Check if employee on Leave
		leave_record = frappe.db.sql("""select half_day from `tabLeave Application`
			where employee = %s and %s between from_date and to_date
			and docstatus = 1""", (self.employee, attendance_date), as_dict=True)
		if leave_record:
			frappe.msgprint(_("Attendance not submitted for {0} as {1} on leave.").format(attendance_date, self.employee), alert=1)
			return True

		return False
