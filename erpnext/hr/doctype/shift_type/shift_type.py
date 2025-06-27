# -*- coding: utf-8 -*-
# Copyright (c) 2018, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

from __future__ import unicode_literals
import itertools
from datetime import datetime, timedelta

import frappe
from frappe.model.document import Document
from frappe.utils import cint, getdate, get_datetime
from erpnext.hr.doctype.shift_assignment.shift_assignment import get_actual_start_end_datetime_of_shift, get_employee_shift
from erpnext.hr.doctype.employee_checkin.employee_checkin import mark_attendance_and_link_log, calculate_working_hours
from erpnext.hr.doctype.attendance.attendance import mark_absent
from erpnext.hr.doctype.employee.employee import get_holiday_list_for_employee
from nerp.utils import get_time_diff, get_config_by_name

class ShiftType(Document):
	def process_auto_attendance(self,shift_end_time=None):
		# global absent_employees
		if(not shift_end_time):
			return
		doc = frappe.get_doc('Shift Type', doc)
		ci_start_date = datetime.now().date() - timedelta(days=5)
		if not cint(doc.enable_auto_attendance) or not shift_end_time:
			return
		
		filters = {
			'attendance':('is', 'not set'),
			'time':('>=', doc.process_attendance_after),
			'shift_actual_end': ('<=', doc.last_sync_of_checkin),
			'shift': doc.name
		}

		logs = frappe.db.get_list('Employee Checkin', fields="*", filters=filters, order_by="employee,time")
		# frappe.log_error(message="logs -> {0} {1}".format(len(logs),doc.name), title="Employee Checkin0 -> {0}".format(doc.name))
		i = 0
		unique_employee_logs = {}
		for key, group in itertools.groupby(logs, key=lambda x: (x['employee'], x['shift_actual_start'])):
			single_shift_logs = list(group)
			unique_employee_logs[key] = list(group)
			attendance_status, working_hours, short_hours, late_entry, early_exit, overtime_hours = doc.get_attendance(single_shift_logs)
			mark_attendance_and_link_log(single_shift_logs, attendance_status, key[1].date(), working_hours, short_hours, late_entry, early_exit, doc.name, overtime_hours)
			i += len(single_shift_logs)
			if i > 100:
				frappe.db.commit()
				i=0
		# frappe.db.commit()
		# for emp in unique_employee_logs:
		#     attendance_date=emp[1]
		#     employee=emp[0]
		#     frappe.enqueue(method="nerp.nerp.report.provisional_salary_report.provisional_salary_report.single_employee_salary_data",employee=employee,date=attendance_date, queue='hr_primary',timeout=13000)
		
		employees = doc.get_assigned_employee(doc.process_attendance_after, True)
		#employees_list = frappe.db.sql("""SELECT * from `tabEmployee` WHERE name in %(names)s""", {'names': employees}, as_dict=True)
		for employee in employees:
			doc.mark_absent_for_dates_with_no_attendance(employee)
			frappe.db.commit()
		# for emp in absent_employees:
		#     employee=emp[0]
		#     attendance_date=emp[1]
		#     frappe.enqueue(method="nerp.nerp.report.provisional_salary_report.provisional_salary_report.single_employee_salary_data",employee=employee,date=attendance_date, queue='hr_primary',timeout=13000)
		# absent_employees = []  
		doc.process_attendance_after = ci_start_date
		doc.save(ignore_permissions=True)

	def get_attendance(self, logs):
		"""Return attendance_status, working_hours for a set of logs belonging to a single shift.
		Assumtion: 
			1. These logs belongs to an single shift, single employee and is not in a holiday date.
			2. Logs are in chronological order
		"""
		late_entry = early_exit = False
		total_working_hours, in_time, out_time = calculate_working_hours(logs, self.determine_check_in_and_check_out, self.working_hours_calculation_based_on)
		### Customization ###
		short_hours = calculate_short_hours(self.start_time, self.end_time, total_working_hours, self.name)
		overtime_hours = calculate_overtime_hours(logs, self.start_time, self.end_time, total_working_hours, self.name)
		### Customization ###
		if cint(self.enable_entry_grace_period) and in_time and in_time > logs[0].shift_start + timedelta(minutes=cint(self.late_entry_grace_period)):
			late_entry = True
		
		if cint(self.enable_exit_grace_period) and out_time and out_time < logs[0].shift_end - timedelta(minutes=cint(self.early_exit_grace_period)):
			early_exit = True
		
		if self.name in get_config_by_name("24_HRS_SHIFT_TYPES", []):
			late_entry = 0
			early_exit = 0
			overtime_hours = 0
		if self.working_hours_threshold_for_absent and total_working_hours < self.working_hours_threshold_for_absent:
			# if absent then short_hours should be zero
			short_hours = 0
			late_entry = 0
			early_exit = 0
			overtime_hours = 0
			return 'Absent', total_working_hours, short_hours, late_entry, early_exit, overtime_hours
		if self.working_hours_threshold_for_half_day and total_working_hours < self.working_hours_threshold_for_half_day:
			return 'Half Day', total_working_hours, short_hours, late_entry, early_exit, overtime_hours
		return 'Present', total_working_hours, short_hours, late_entry, early_exit, overtime_hours

	def mark_absent_for_dates_with_no_attendance(self, employee):
		"""Marks Absents for the given employee on working days in this shift which have no attendance marked.
		The Absent is marked starting from 'process_attendance_after' or employee creation date.
		"""
		from erpnext.hr.doctype.shift_type.shift_type import get_filtered_date_list

		date_of_joining, relieving_date, employee_creation = frappe.db.get_value("Employee", employee, ["date_of_joining", "relieving_date", "creation"])
		if not date_of_joining:
			date_of_joining = employee_creation.date()
		start_date = max(getdate(self.process_attendance_after), date_of_joining)
		actual_shift_datetime = get_actual_start_end_datetime_of_shift(employee, get_datetime(self.last_sync_of_checkin), True)
		last_shift_time = actual_shift_datetime[0] if actual_shift_datetime[0] else get_datetime(self.last_sync_of_checkin)
		prev_shift = get_employee_shift(employee, last_shift_time.date()-timedelta(days=1), True, 'reverse')
		prev_date = get_datetime(self.last_sync_of_checkin).date()-timedelta(days=1)
		if(actual_shift_datetime[2]["actual_start"].date() == actual_shift_datetime[2]["actual_end"].date()):
			prev_date = get_datetime(self.last_sync_of_checkin).date()
		
		if prev_shift:
			end_date = min(prev_date, relieving_date) if relieving_date else prev_date
		else:
			return
		holiday_list_name = self.holiday_list
		if not holiday_list_name:
			holiday_list_name = get_holiday_list_for_employee(employee, False)
		dates = get_filtered_date_list(employee, start_date, end_date, holiday_list=holiday_list_name)
		for date in dates:
			shift_details = get_employee_shift(employee, date, True)
			if shift_details and shift_details.shift_type.name == self.name:
				mark_absent(employee, date, self.name)
				# absent_employees.append((employee,date))
				# frappe.enqueue(method="nerp.nerp.report.provisional_salary_report.provisional_salary_report.single_employee_salary_data",employee=employee,date=date, queue='short',timeout=13000,enqueue_after_commit=True)

	def get_assigned_employee(self, from_date=None, consider_default_shift=False):
		filters = {'date':('>=', from_date), 'shift_type': self.name, 'docstatus': '1'}
		if not from_date:
			del filters['date']
		assigned_employees = frappe.get_all('Shift Assignment', 'employee', filters, as_list=True)
		assigned_employees = [x[0] for x in assigned_employees]

		if consider_default_shift:
			filters = {'default_shift': self.name}
			default_shift_employees = frappe.get_all('Employee', 'name', filters, as_list=True)
			default_shift_employees = [x[0] for x in default_shift_employees]
			return list(set(assigned_employees+default_shift_employees))
		return assigned_employees

def process_auto_attendance_for_all_shifts():
	shift_list = frappe.get_all('Shift Type', 'name', {'enable_auto_attendance':'1'}, as_list=True)
	for shift in shift_list:
		doc = frappe.get_doc('Shift Type', shift[0])
		#doc.process_auto_attendance()

def get_filtered_date_list(employee, start_date, end_date, filter_attendance=True, holiday_list=None):
	"""Returns a list of dates after removing the dates with attendance and holidays
	"""
	base_dates_query = """select adddate(%(start_date)s, t2.i*100 + t1.i*10 + t0.i) selected_date from
		(select 0 i union select 1 union select 2 union select 3 union select 4 union select 5 union select 6 union select 7 union select 8 union select 9) t0,
		(select 0 i union select 1 union select 2 union select 3 union select 4 union select 5 union select 6 union select 7 union select 8 union select 9) t1,
		(select 0 i union select 1 union select 2 union select 3 union select 4 union select 5 union select 6 union select 7 union select 8 union select 9) t2"""
	condition_query = ''
	if filter_attendance:
		condition_query += """ and a.selected_date not in (
			select attendance_date from `tabAttendance` 
			where docstatus = '1' and employee = %(employee)s 
			and attendance_date between %(start_date)s and %(end_date)s)"""
	if holiday_list:
		condition_query += """ and a.selected_date not in (
			select holiday_date from `tabHoliday` where parenttype = 'Holiday List' and
    		parentfield = 'holidays' and parent = %(holiday_list)s
    		and holiday_date between %(start_date)s and %(end_date)s)"""
	
	dates = frappe.db.sql("""select * from
		({base_dates_query}) as a
		where a.selected_date <= %(end_date)s {condition_query}
		""".format(base_dates_query=base_dates_query, condition_query=condition_query),
		{"employee":employee, "start_date":start_date, "end_date":end_date, "holiday_list":holiday_list}, as_list=True)

	return [getdate(date[0]) for date in dates]

def calculate_shift_hours(start_time, end_time):
	todays_date = datetime.today().strftime('%Y-%m-%d')
	today_shift_start = "{0} {1}".format(todays_date, start_time)
	today_shift_end = "{0} {1}".format(todays_date, end_time)
	total_shift_hours = get_time_diff(today_shift_end, today_shift_start, "hours")
	# for shifts like 18:00:00 to 03:00:00
	if total_shift_hours < 0:
		tomorrows_date_obj = datetime.today() + timedelta(days=1)
		tomorrows_date = tomorrows_date_obj.strftime('%Y-%m-%d')
		today_shift_end = "{0} {1}".format(tomorrows_date, end_time)
		total_shift_hours = get_time_diff(today_shift_end, today_shift_start, "hours")
	return total_shift_hours

def calculate_short_hours(start_time, end_time, working_hours, shift_type=None):
	if shift_type in get_config_by_name("24_HRS_SHIFT_TYPES", []):
		total_shift_hours = get_config_by_name("24_HRS_SHIFT_TYPE_WORKING_HOURS", 9)
	else:
		total_shift_hours = calculate_shift_hours(start_time, end_time)
	
	shift_break_hours = get_config_by_name("BREAK_HOURS", 1)
	net_shift_hours = total_shift_hours - shift_break_hours

	short_hours = net_shift_hours - working_hours
	if short_hours < 0:
		short_hours =  0
	return short_hours

def calculate_overtime_hours(logs, start_time, end_time, working_hours, shift_name):
	# check we have more than 1 paid of checkins/checkouts
	overtime_hours = 0
	if len(logs) > 2 and shift_name in get_config_by_name("POS_SHIFT_TYPES", []):
		total_shift_hours = calculate_shift_hours(start_time, end_time)
		overtime_hours = working_hours - total_shift_hours
		if overtime_hours < 0:
			overtime_hours = 0
	return overtime_hours