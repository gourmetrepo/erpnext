# -*- coding: utf-8 -*-
# Copyright (c) 2017, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

from __future__ import unicode_literals
import frappe
from frappe.model.document import Document
from dateutil.relativedelta import relativedelta
from frappe.utils import cint, flt, nowdate, add_days, getdate, fmt_money, add_to_date, DATE_FORMAT, date_diff
from nerp.utils import change_queue_status
from frappe import _
from erpnext.accounts.utils import get_fiscal_year
from erpnext.hr.doctype.employee.employee import get_holiday_list_for_employee

class PayrollEntry(Document):
	def onload(self):
		if not self.docstatus==1 or self.salary_slips_submitted:
    			return

		# check if salary slips were manually submitted
		entries = frappe.db.count("Salary Slip", {'payroll_entry': self.name, 'docstatus': 1}, ['name'])
		if cint(entries) == len(self.employees):
    			self.set_onload("submitted_ss", True)

	def on_submit(self):
		self.create_salary_slips()

	def before_submit(self):
		if self.validate_attendance:
			if self.validate_employee_attendance():
				frappe.throw(_("Cannot Submit, Employees left to mark attendance"))

	def on_cancel(self):
		frappe.delete_doc("Salary Slip", frappe.db.sql_list("""select name from `tabSalary Slip`
			where payroll_entry=%s """, (self.name)))

	
	def get_emp_list(self):
		"""
			Returns list of active employees based on selected criteria
			and for which salary structure exists
		"""
		cond = self.get_filter_condition()
		cond += self.get_joining_relieving_condition()

		condition = ''
		if self.payroll_frequency:
			condition = """and payroll_frequency = '%(payroll_frequency)s'"""% {"payroll_frequency": self.payroll_frequency}

		sal_struct = frappe.db.sql_list("""
				select
					name from `tabSalary Structure`
				where
					docstatus = 1 and
					is_active = 'Yes'
					and company = %(company)s and
					ifnull(salary_slip_based_on_timesheet,0) = %(salary_slip_based_on_timesheet)s
					{condition}""".format(condition=condition),
				{"company": self.company, "salary_slip_based_on_timesheet":self.salary_slip_based_on_timesheet})

		if sal_struct:
			cond += "and t2.salary_structure IN %(sal_struct)s "
			cond += "and %(from_date)s >= t2.from_date"
			if not self.get("department"):
				ignored_departments = get_config_by_name("PAYROLL_IGNORED_DEPARTMENTS",None)
				if(ignored_departments):
					cond += " and t1.department NOT IN ({0})".format("'"+"','".join(ignored_departments)+"'")

			if self.get("employee"):
				cond += " and t1.employee = %(employee)s "
			if self.get("exclude_employees"):
				cond += ' and t1.status = "Active"'
			else:
				cond += ' and t1.status != "Pending"'

			emp_list = frappe.db.sql("""
				select
					distinct t1.name as employee, t1.employee_name, t1.department, t1.designation
				from
					`tabEmployee` t1, `tabSalary Structure Assignment` t2
				where
					t1.name = t2.employee
					and t2.docstatus = 1
			%s order by t2.from_date desc
			""" % cond, {"sal_struct": tuple(sal_struct), "from_date": self.end_date, "employee": self.employee}, as_dict=True)

			return emp_list

	def fill_employee_details(self):
		self.set('employees', [])
		employees = get_emp_list(self)
		if not employees:
			frappe.throw(_("No employees for the mentioned criteria"))

		for d in employees:
			self.append('employees', d)

		self.number_of_employees = len(employees)
		if self.validate_attendance:
			return self.validate_employee_attendance()

	def get_filter_condition(self):
		self.check_mandatory()

		cond = ''
		for f in ['company', 'branch', 'department', 'designation']:
			if self.get(f):
				cond += " and t1." + f + " = '" + self.get(f).replace("'", "\'") + "'"

		return cond

	def get_joining_relieving_condition(self):
		cond = """
			and ifnull(t1.date_of_joining, '0000-00-00') <= '%(end_date)s'
			and ifnull(t1.relieving_date, '2199-12-31') >= '%(start_date)s'
		""" % {"start_date": self.start_date, "end_date": self.end_date}
		return cond

	def check_mandatory(self):
		for fieldname in ['company', 'start_date', 'end_date']:
			if not self.get(fieldname):
				frappe.throw(_("Please set {0}").format(self.meta.get_label(fieldname)))

	def create_salary_slips(self):
		"""
			Creates salary slip for selected employees if already not created
		"""
		self.check_permission('write')
		self.created = 1
		change_queue_status(self.doctype, self.name, "Queued")
		emp_list = [d.employee for d in self.get_emp_list()]
		if emp_list:
			args = frappe._dict({
				"salary_slip_based_on_timesheet": self.salary_slip_based_on_timesheet,
				"payroll_frequency": self.payroll_frequency,
				"start_date": self.start_date,
				"end_date": self.end_date,
				"company": self.company,
				"posting_date": self.posting_date,
				"deduct_tax_for_unclaimed_employee_benefits": self.deduct_tax_for_unclaimed_employee_benefits,
				"deduct_tax_for_unsubmitted_tax_exemption_proof": self.deduct_tax_for_unsubmitted_tax_exemption_proof,
				"payroll_entry": self.name
			})
			frappe.enqueue("erpnext.hr.doctype.payroll_entry.payroll_entry.create_salary_slips_for_employees", queue='hr_tertiary', timeout=13600, employees=emp_list, args=args)
		self.reload()

	def get_sal_slip_list(self, ss_status, as_dict=False):
		"""
			Returns list of salary slips based on selected criteria
		"""
		cond = self.get_filter_condition()

		ss_list = frappe.db.sql("""
			select t1.name, t1.salary_structure from `tabSalary Slip` t1
			where t1.docstatus = %s and t1.start_date >= %s and t1.end_date <= %s and t1.payroll_entry = %s
			and (t1.journal_entry is null or t1.journal_entry = "") and ifnull(salary_slip_based_on_timesheet,0) = %s %s
		""" % ('%s', '%s', '%s', '%s', '%s', cond), (ss_status, self.start_date, self.end_date, self.name, self.salary_slip_based_on_timesheet), as_dict=as_dict)
		return ss_list

	def submit_salary_slips(self):
		try:
			self.check_permission('write')
			ss_list = self.get_sal_slip_list(ss_status=0)
			frappe.enqueue("erpnext.hr.doctype.payroll_entry.payroll_entry.submit_salary_slips_for_employees", queue='hr_tertiary', timeout=13600, payroll_entry_name=self.name, salary_slips=ss_list)
			change_queue_status(self.doctype, self.name, "Queued")
			self.reload()
		except Exception as error:
			frappe.log_error(frappe.get_traceback(), "Payroll Entry")
			frappe.throw(_("Error submitting salary slip for Payroll Entry {0}").format(self.name))

	def email_salary_slip(self, submitted_ss):
		if frappe.db.get_single_value("HR Settings", "email_salary_slip_to_employee"):
			for ss in submitted_ss:
				ss.email_salary_slip()

	def get_loan_details(self):
		"""
			Get loan details from submitted salary slip based on selected criteria
		"""
		cond = self.get_filter_condition()
		return frappe.db.sql(f""" select eld.loan_account, eld.loan,
				eld.interest_income_account, eld.principal_amount, eld.interest_amount, eld.total_payment,t1.employee
			from
				`tabSalary Slip` t1, `tabSalary Slip Loan` eld
			where
                t1.payroll_entry = '{self.name}' and
				t1.docstatus = 1 and t1.name = eld.parent and start_date >= '{self.start_date}' and end_date <= '{self.end_date}' 
                {cond}
			""", as_dict=True) or []

	def get_salary_component_account(self, salary_component):
		account = frappe.db.get_value("Salary Component Account",
			{"parent": salary_component, "company": self.company}, "default_account")

		if not account:
			frappe.throw(_("Please set default account in Salary Component {0}")
				.format(salary_component))

		return account


	def get_salary_components(self, component_type):
		'''
		This overrided function to be used to get account and department on the bases of employee in salary slip
		'''
		salary_slips = self.get_sal_slip_list(ss_status = 1, as_dict = True)
		if salary_slips:
			salary_components = frappe.db.sql("""
				SELECT 
					sal_comp.salary_component,
					sal_comp.amount,
					sal_comp.parentfield,
					sal_slip.department,
					sal_slip.sub_branch,
					sub_br.cost_center
				FROM
					`tabSalary Detail` sal_comp
				INNER JOIN
					`tabSalary Component` comp ON sal_comp.salary_component = comp.name
				LEFT JOIN
					`tabSalary Slip` sal_slip ON sal_comp.parent = sal_slip.name
				LEFT JOIN
					`tabSub Branch` sub_br ON sal_slip.sub_branch = sub_br.name
				WHERE
					sal_comp.parentfield = '%s' and sal_comp.parent in (%s) and comp.impact_on_gl=0 """ %
				(component_type, ', '.join(['%s']*len(salary_slips))), tuple([d.name for d in salary_slips]), as_dict=True)
			return salary_components

	def get_salary_component_total(self, component_type = None):
		'''
		This overrided function create dictionay on bases of expense account in department
		'''
		salary_components = self.get_salary_components(component_type)
		if salary_components:
			accounts_dict = {}
			for item in salary_components:
				add_component_to_accrual_jv_entry = True
				if component_type == "earnings":
					is_flexible_benefit, only_tax_impact = frappe.db.get_value("Salary Component", item['salary_component'], ['is_flexible_benefit', 'only_tax_impact'])
					if is_flexible_benefit == 1 and only_tax_impact ==1:
						add_component_to_accrual_jv_entry = False
				if add_component_to_accrual_jv_entry:
					if(not item['cost_center']):
						frappe.throw(_("Please attache Cost Center with Sub Branch {0}").format(item['sub_branch']))
					accounts_dict[item['sub_branch']] = accounts_dict.get(item['sub_branch'], 0) + item['amount']
			return accounts_dict

	def get_account(self, component_dict = None):
		account_dict = {}
		for s, a in component_dict.items():
			account = self.get_salary_component_account(s)
			account_dict[account] = account_dict.get(account, 0) + a
		return account_dict

	def get_default_payroll_payable_account(self):
		payroll_payable_account = frappe.get_cached_value('Company',
			{"company_name": self.company},  "default_payroll_payable_account")

		if not payroll_payable_account:
			frappe.throw(_("Please set Default Payroll Payable Account in Company {0}")
				.format(self.company))

		return payroll_payable_account

	def make_accrual_jv_entry(self):
		import datetime
		self.check_permission('write')
		# date_obj = datetime.strptime(self.end_date, '%Y-%m-%d')
		# formatted_date = date_obj.strftime('%B %Y')
		formatted_date = ''
		if isinstance(self.end_date, datetime.date):
			formatted_date = self.end_date.strftime('%B %Y')
		elif isinstance(self.end_date, str):
			date_obj = datetime.datetime.strptime(self.end_date, '%Y-%m-%d')
			formatted_date = date_obj.strftime('%B %Y')
		earnings = self.get_salary_component_total(component_type = "earnings") or {}
		deductions = self.get_salary_component_total(component_type = "deductions") or {}
		tax_deductions = get_salary_component_total_native(self,component_type = "deductions") or {}
		earning_component_gl_impact = get_salary_component_total_native(self,component_type = "earnings") or {}

		default_payroll_payable_account = self.get_default_payroll_payable_account()
		loan_details = self.get_loan_details()
		jv_name = ""
		precision = frappe.get_precision("Journal Entry Account", "debit_in_account_currency")

		if earnings or deductions:
			journal_entry = frappe.new_doc('Journal Entry')
			journal_entry.title = ('ACC SJV for {0} - {1}')\
			.format(self.company, formatted_date)
			journal_entry.naming_series = 'ACC-SJV-.YYYY.-'
			journal_entry.payroll_entry = self.name
			journal_entry.voucher_type = 'Journal Entry'
			journal_entry.user_remark = _('Accrual Journal Entry for salaries from {0} to {1}')\
				.format(self.start_date, self.end_date)
			journal_entry.company = self.company
			journal_entry.posting_date = self.posting_date

			accounts = []
			payable_amount = 0
			branches = {}		
			# Earnings
			for br, amount in earnings.items():
				payable_amount += flt(amount, precision)
				if(br not in branches):
					cost_acc = frappe.db.get_value("Sub Branch",br,["cost_center"])
					expense_acc = get_expense_account(br)	
					if(not expense_acc):
						frappe.throw(_("Please attache Expense accpint with parent of Sub Branch {0}").format(br))
					branches[br] = {"cost_center":cost_acc,"expense_account":expense_acc}

				accounts.append({
						"account": branches[br]["expense_account"],
						"debit_in_account_currency": flt(amount, precision),
						"party_type": '',
						"cost_center": branches[br]["cost_center"] or self.cost_center,
						"project": self.project
					})

			# Deductions
			for br, amount in deductions.items():
				payable_amount -= flt(amount, precision)

				if(br not in branches):
					cost_acc = frappe.db.get_value("Sub Branch",br,["cost_center"])
					expense_acc = get_expense_account(br)	
					if(not expense_acc):
						frappe.throw(_("Please attache Expense accpint with parent of Sub Branch {0}").format(br))
					branches[br] = {"cost_center":cost_acc,"expense_account":expense_acc}

				accounts.append({
						"account": branches[br]["expense_account"],
						"credit_in_account_currency": flt(amount, precision),
						"cost_center": branches[br]["cost_center"] or  self.cost_center,
						"party_type": '',
						"project": self.project
					})

			# Tax Deductions
			for acc, amount in tax_deductions.items():
				#added by Asad against employee wise general entry
				if type(amount) is list:
					for items in amount:
						for x in items:
							payable_amount -= flt(items[x], precision)            
							accounts.append({
								"account": acc,
								"credit_in_account_currency": flt(items[x], precision),
								"cost_center": self.cost_center,
								"party_type": 'Employee',
								"party": x,
								"project": self.project
							})			
				else:	
					payable_amount -= flt(amount, precision)			
					accounts.append({
							"account": acc,
							"credit_in_account_currency": flt(amount, precision),
							"cost_center": self.cost_center,
							"party_type": '',
							"project": self.project
						})

			# Earning Component GL impact
			for acc, amount in earning_component_gl_impact.items():
				#Copied by Shoaib against employee wise general entry
				if type(amount) is list:
					for items in amount:
						for x in items:
							payable_amount += flt(items[x], precision)            
							accounts.append({
								"account": acc,
								"debit_in_account_currency": flt(items[x], precision),
								"cost_center": self.cost_center,
								"party_type": 'Employee',
								"party": x,
								"project": self.project
							})			
				else:	
					payable_amount += flt(amount, precision)			
					accounts.append({
							"account": acc,
							"debit_in_account_currency": flt(amount, precision),
							"cost_center": self.cost_center,
							"party_type": '',
							"project": self.project
						})

			# Loan
			for data in loan_details:
				accounts.append({
						"account": data.loan_account,
						"credit_in_account_currency": data.principal_amount,
						"party_type": "Employee",
						"party": data.employee
					})

				if data.interest_amount and not data.interest_income_account:
					frappe.throw(_("Select interest income account in loan {0}").format(data.loan))

				if data.interest_income_account and data.interest_amount:
					accounts.append({
						"account": data.interest_income_account,
						"credit_in_account_currency": data.interest_amount,
						"cost_center": self.cost_center,
						"project": self.project,
						"party_type": "Employee",
						"party": data.employee
					})
				payable_amount -= flt(data.total_payment, precision)

			# Payable amount
			accounts.append({
				"account": default_payroll_payable_account,
				"credit_in_account_currency": flt(payable_amount, precision),
				"party_type": ''
			})

			journal_entry.set("accounts", accounts)
			journal_entry.save()
			frappe.db.commit()
			try:
				journal_entry.submit()
				jv_name = journal_entry.name
				self.update_salary_slip_status(jv_name = jv_name)
			except Exception as e:
				frappe.msgprint(e)

		return jv_name

	def make_payment_entry(self):
		self.check_permission('write')

		cond = self.get_filter_condition()
		salary_slip_name_list = frappe.db.sql(""" select t1.name from `tabSalary Slip` t1
			where t1.docstatus = 1 and start_date >= %s and end_date <= %s %s
			""" % ('%s', '%s', cond), (self.start_date, self.end_date), as_list = True)

		if salary_slip_name_list and len(salary_slip_name_list) > 0:
			salary_slip_total = 0
			for salary_slip_name in salary_slip_name_list:
				salary_slip = frappe.get_doc("Salary Slip", salary_slip_name[0])
				for sal_detail in salary_slip.earnings:
					is_flexible_benefit, only_tax_impact, creat_separate_je, statistical_component = frappe.db.get_value("Salary Component", sal_detail.salary_component,
						['is_flexible_benefit', 'only_tax_impact', 'create_separate_payment_entry_against_benefit_claim', 'statistical_component'])
					if only_tax_impact != 1 and statistical_component != 1:
						if is_flexible_benefit == 1 and creat_separate_je == 1:
							self.create_journal_entry(sal_detail.amount, sal_detail.salary_component)
						else:
							salary_slip_total += sal_detail.amount
				for sal_detail in salary_slip.deductions:
					statistical_component = frappe.db.get_value("Salary Component", sal_detail.salary_component, 'statistical_component')
					if statistical_component != 1:
						salary_slip_total -= sal_detail.amount

				#loan deduction from bank entry during payroll
				salary_slip_total -= salary_slip.total_loan_repayment

			if salary_slip_total > 0:
				self.create_journal_entry(salary_slip_total, "salary")

	def create_journal_entry(self, je_payment_amount, user_remark, account=False ,type =None , ref_sal_slips=None):
		default_payroll_payable_account = self.get_default_payroll_payable_account()
		precision = frappe.get_precision("Journal Entry Account", "debit_in_account_currency")
		if type:
			title_type =type.split(" ", 1)
		journal_entry = frappe.new_doc('Journal Entry')
		journal_entry.voucher_type = type
		journal_entry.title = ('Salary {1} {0} Paid')\
			.format(title_type[0], self.company)
		journal_entry.naming_series = 'ACC-SJV-.YYYY.-'
		journal_entry.user_remark = _('Payment of {0} from {1} to {2} against salary slips :{3}')\
			.format(user_remark, self.start_date, self.end_date, ' '.join(ref_sal_slips))
		# journal_entry.user_remark = _('Payment of {0} from {1} to {2}')\
		# 	.format(user_remark, self.start_date, self.end_date)
		journal_entry.company = self.company
		journal_entry.posting_date = self.posting_date

		payment_amount = flt(je_payment_amount, precision)

		journal_entry.set("accounts", [
			{
				"account": account if account else self.payment_account,
				"bank_account": self.bank_account,
				"credit_in_account_currency": payment_amount
			},
			{
				"account": default_payroll_payable_account,
				"debit_in_account_currency": payment_amount,
				"reference_type": self.doctype,
				"reference_name": self.name
			}
		])
		journal_entry.save(ignore_permissions = True)
		return journal_entry

	def update_salary_slip_status(self, jv_name = None):
		ss_list = self.get_sal_slip_list(ss_status=1)
		for ss in ss_list:
			ss_obj = frappe.get_doc("Salary Slip",ss[0])
			frappe.db.set_value("Salary Slip", ss_obj.name, "journal_entry", jv_name)

	def set_start_end_dates(self):
		self.update(get_start_end_dates(self.payroll_frequency,
			self.start_date or self.posting_date, self.company))

	def validate_employee_attendance(self):
		employees_to_mark_attendance = []
		days_in_payroll, days_holiday, days_attendance_marked = 0, 0, 0
		for employee_detail in self.employees:
			start_date = self.start_date
			employee_joining_date = frappe.db.get_value("Employee", employee_detail.employee, 'date_of_joining')
			if employee_joining_date > getdate(self.start_date):
				start_date = employee_joining_date
			days_holiday = self.get_count_holidays_of_employee(employee_detail.employee, start_date)
			days_attendance_marked = self.get_count_employee_attendance(employee_detail.employee, start_date)
			days_in_payroll = date_diff(self.end_date, self.start_date) + 1
			if days_in_payroll > days_holiday + days_attendance_marked and validate_employee_joining_relieving(employee_detail.employee, self.start_date, self.end_date, days_holiday + days_attendance_marked):
				employees_to_mark_attendance.append({
					"employee": employee_detail.employee,
					"employee_name": employee_detail.employee_name
					})
		return employees_to_mark_attendance

	def get_count_holidays_of_employee(self, employee, start_date):
		holiday_list = get_holiday_list_for_employee(employee)
		holidays = 0
		if holiday_list:
			days = frappe.db.sql("""select count(*) from tabHoliday where
				parent=%s and holiday_date between %s and %s""", (holiday_list,
				start_date, self.end_date))
			if days and days[0][0]:
				holidays = days[0][0]
		return holidays

	def get_count_employee_attendance(self, employee, start_date):
		marked_days = 0
		attendances = frappe.get_all("Attendance",
				fields = ["count(*)"],
				filters = {
					"employee": employee,
					"attendance_date": ('between', [start_date, self.end_date])
				}, as_list=1)
		if attendances and attendances[0][0]:
			marked_days = attendances[0][0]
		return marked_days

@frappe.whitelist()
def get_start_end_dates(payroll_frequency, start_date=None, company=None):
	'''Returns dict of start and end dates for given payroll frequency based on start_date'''

	if payroll_frequency == "Monthly" or payroll_frequency == "Bimonthly" or payroll_frequency == "":
		fiscal_year = get_fiscal_year(start_date, company=company)[0]
		month = "%02d" % getdate(start_date).month
		m = get_month_details(fiscal_year, month)
		if payroll_frequency == "Bimonthly":
			if getdate(start_date).day <= 15:
				start_date = m['month_start_date']
				end_date = m['month_mid_end_date']
			else:
				start_date = m['month_mid_start_date']
				end_date = m['month_end_date']
		else:
			start_date = m['month_start_date']
			end_date = m['month_end_date']

	if payroll_frequency == "Weekly":
		end_date = add_days(start_date, 6)

	if payroll_frequency == "Fortnightly":
		end_date = add_days(start_date, 13)

	if payroll_frequency == "Daily":
		end_date = start_date

	return frappe._dict({
		'start_date': start_date, 'end_date': end_date
	})

def get_frequency_kwargs(frequency_name):
	frequency_dict = {
		'monthly': {'months': 1},
		'fortnightly': {'days': 14},
		'weekly': {'days': 7},
		'daily': {'days': 1}
	}
	return frequency_dict.get(frequency_name)


@frappe.whitelist()
def get_end_date(start_date, frequency):
	start_date = getdate(start_date)
	frequency = frequency.lower() if frequency else 'monthly'
	kwargs = get_frequency_kwargs(frequency) if frequency != 'bimonthly' else get_frequency_kwargs('monthly')

	# weekly, fortnightly and daily intervals have fixed days so no problems
	end_date = add_to_date(start_date, **kwargs) - relativedelta(days=1)
	if frequency != 'bimonthly':
		return dict(end_date=end_date.strftime(DATE_FORMAT))

	else:
		return dict(end_date='')


def get_month_details(year, month):
	ysd = frappe.db.get_value("Fiscal Year", year, "year_start_date")
	if ysd:
		import calendar, datetime
		diff_mnt = cint(month)-cint(ysd.month)
		if diff_mnt<0:
			diff_mnt = 12-int(ysd.month)+cint(month)
		msd = ysd + relativedelta(months=diff_mnt) # month start date
		month_days = cint(calendar.monthrange(cint(msd.year) ,cint(month))[1]) # days in month
		mid_start = datetime.date(msd.year, cint(month), 16) # month mid start date
		mid_end = datetime.date(msd.year, cint(month), 15) # month mid end date
		med = datetime.date(msd.year, cint(month), month_days) # month end date
		return frappe._dict({
			'year': msd.year,
			'month_start_date': msd,
			'month_end_date': med,
			'month_mid_start_date': mid_start,
			'month_mid_end_date': mid_end,
			'month_days': month_days
		})
	else:
		frappe.throw(_("Fiscal Year {0} not found").format(year))

def get_payroll_entry_bank_entries(payroll_entry_name):
	journal_entries = frappe.db.sql(
		'SELECT B.name FROM `tabJournal Entry Account` AS A '
		' INNER JOIN `tabJournal Entry` AS B ON A.`parent` =B.`name`'
		' WHERE reference_type="Payroll Entry"  AND voucher_type="Bank Entry"'
		' and A.reference_name=%s and B.docstatus IN (0,1)',
		payroll_entry_name,
		as_dict=1
	)

	return journal_entries


@frappe.whitelist()
def payroll_entry_has_bank_entries(name):
	response = {}
	bank_entries = get_payroll_entry_bank_entries(name)
	response['submitted'] = 1 if bank_entries else 0

	return response


@frappe.whitelist()
def create_salary_slips_for_employees(employees, args, publish_progress=True):
	try:
		salary_slips_exists_for = get_existing_salary_slips(employees, args)
		count=0
		for emp in employees:
			if emp not in salary_slips_exists_for:
				count+=1
				frappe.enqueue("erpnext.hr.doctype.payroll_entry.payroll_entry.create_salary_slip_for_employee", queue='hr_tertiary', emp=emp, employees=employees, args=args, 
				count=count, ss_exists_for=salary_slips_exists_for, publish_progress=publish_progress, enqueue_after_commit=True)

		frappe.enqueue("erpnext.hr.doctype.payroll_entry.payroll_entry.after_salary_slips_creation", queue='hr_tertiary', payroll_entry_name=args.payroll_entry, enqueue_after_commit=True)
	except Exception as error:
		traceback = frappe.get_traceback()
		frappe.log_error(message=f"Error: {error} \n Traceback: {traceback}", title="Enqueue Salary Slip creation from payroll")

def get_existing_salary_slips(employees, args):
	return frappe.db.sql_list("""
		select distinct employee from `tabSalary Slip`
		where docstatus!= 2 and company = %s
			and start_date >= %s and end_date <= %s
			and employee in (%s)
	""" % ('%s', '%s', '%s', ', '.join(['%s']*len(employees))),
		[args.company, args.start_date, args.end_date] + employees)


@frappe.whitelist()
def create_salary_slip_for_employee(emp, employees, args, count, ss_exists_for, publish_progress):
	try:
		args.update({
			"doctype": "Salary Slip",
			"employee": emp
		})
		ss = frappe.get_doc(args)
		ss.insert()

		# Comment code to block the foreground progress
		# if publish_progress:
		# 	frappe.publish_progress(count*100/len(set(employees) - set(ss_exists_for)),
		# 		title = _("Creating Salary Slips..."))
	except Exception as error:
		frappe.db.rollback()
		traceback = frappe.get_traceback()
		frappe.log_error(message=f"Error: {error} \n Traceback: {traceback}", title="Creating Salary Slip from payroll")


@frappe.whitelist()
def after_salary_slips_creation(payroll_entry_name):
	try:
		payroll_entry = frappe.get_doc("Payroll Entry", payroll_entry_name)
		payroll_entry.db_set("salary_slips_created", 1)
		payroll_entry.notify_update()
		change_queue_status("Payroll Entry", payroll_entry.name, "Salary Slip Created")
	except Exception as error:
		frappe.db.rollback()
		traceback = frappe.get_traceback()
		frappe.log_error(message=f"Error: {error} \n Traceback: {traceback}", title="After creating Salary Slip from payroll")


@frappe.whitelist()
def submit_salary_slips_for_employees(payroll_entry_name, salary_slips, publish_progress=True):
	# payroll_entry = frappe.get_doc("Payroll Entry", payroll_entry_name)
	try:
		frappe.flags.via_payroll_entry = True

		count = 0
		for ss in salary_slips:
			count+=1
			frappe.enqueue("erpnext.hr.doctype.payroll_entry.payroll_entry.submit_salary_slip_for_employee", queue='hr_tertiary', ss=ss, count=count, publish_progress=publish_progress, 
			salary_slips=salary_slips, enqueue_after_commit=True)

		frappe.enqueue("erpnext.hr.doctype.payroll_entry.payroll_entry.after_salary_slip_submission", queue='hr_tertiary', payroll_entry_name=payroll_entry_name, enqueue_after_commit=True)
	except Exception as error:
		traceback = frappe.get_traceback()
		frappe.log_error(message=f"Error: {error} \n Traceback: {traceback}", title="Enqueue Salary Slip submission from payroll")


@frappe.whitelist()
def submit_salary_slip_for_employee(ss, count, publish_progress, salary_slips):
	try:
		ss_obj = frappe.get_doc("Salary Slip",ss[0])
		if ss_obj.net_pay<0:
			frappe.log_error(title="Salary Slip Submission", message="Employee net pay less than zero.")
		else:
			ss_obj.submit()

		# Comment code to block the foreground progress
		# if publish_progress:
		# 	frappe.publish_progress(count*100/len(salary_slips), title = _("Submitting Salary Slips..."))
	except Exception as error:
		frappe.db.rollback()
		traceback = frappe.get_traceback()
		frappe.log_error(message=f"Error: {error} \n Traceback: {traceback}", title="Submitting Salary Slip from payroll")


@frappe.whitelist()
def after_salary_slip_submission(payroll_entry_name):
	payroll_entry = frappe.get_doc("Payroll Entry", payroll_entry_name)
	
	try:
		ss_count = frappe.db.sql(f"Select count(*) as submitted_ss_count From `tabSalary Slip` where payroll_entry='{payroll_entry.name}' and docstatus=1;", as_dict=True)
		if ss_count and ss_count[0].submitted_ss_count > 0:
			payroll_entry.make_accrual_jv_entry()
			payroll_entry.db_set("salary_slips_submitted", 1)
			payroll_entry.notify_update()
		change_queue_status("Payroll Entry", payroll_entry.name, "Completed")
	except Exception as error:
		frappe.db.rollback()
		traceback = frappe.get_traceback()
		frappe.log_error(message=f"Error: {error} \n Traceback: {traceback}", title="After submitting Salary Slip from payroll")


@frappe.whitelist()
@frappe.validate_and_sanitize_search_inputs
def get_payroll_entries_for_jv(doctype, txt, searchfield, start, page_len, filters):
	return frappe.db.sql("""
		select name from `tabPayroll Entry`
		where `{key}` LIKE %(txt)s
		and name not in
			(select reference_name from `tabJournal Entry Account`
				where reference_type="Payroll Entry")
		order by name limit %(start)s, %(page_len)s"""
		.format(key=searchfield), {
			'txt': "%%%s%%" % frappe.db.escape(txt),
			'start': start, 'page_len': page_len
		})


def get_salary_components_native(self, component_type):
	salary_slips = self.get_sal_slip_list(ss_status = 1, as_dict = True)
	if salary_slips:
		salary_components = frappe.db.sql("""
			select 
				sd.salary_component, sd.amount, sd.parentfield, comp.employee_segregation,sl.Employee
			from 
				`tabSalary Detail` sd
			INNER JOIN
				`tabSalary Component` comp ON sd.salary_component = comp.name
			INNER JOIN
				`tabSalary Slip` sl ON sd.parent = sl.name
			where
				sd.parentfield = '%s' and sd.parent in (%s) and  comp.impact_on_gl=1 """ %
			(component_type, ', '.join(['%s']*len(salary_slips))), tuple([d.name for d in salary_slips]), as_dict=True)
		return salary_components


def get_salary_component_total_native(self, component_type = None):
	salary_components = get_salary_components_native(self, component_type)
	if salary_components:
		component_dict = {}
		#employeeWise_dict = {}
		for item in salary_components:
			add_component_to_accrual_jv_entry = True
			if component_type == "earnings":
				is_flexible_benefit, only_tax_impact = frappe.db.get_value("Salary Component", item['salary_component'], ['is_flexible_benefit', 'only_tax_impact'])
				if is_flexible_benefit == 1 and only_tax_impact ==1:
					add_component_to_accrual_jv_entry = False
			if add_component_to_accrual_jv_entry:
				if item['employee_segregation']==1:					
					if item['salary_component'] not in component_dict:
						component_dict[item['salary_component']] = []
					component_dict[item['salary_component']].append({item['Employee']:item['amount']})
				else:					
					component_dict[item['salary_component']] = component_dict.get(item['salary_component'], 0) + item['amount']
				#employeeWise_dict[item['salary_component']] = item['employee_segregation'] # added for employee wise journal entry
		#account_details = self.get_account(component_dict = component_dict)
		account_details = get_account_custom(self,component_dict = component_dict)
		#return account_details,employeeWise_dict
		return account_details


def get_expense_account(sub_branch=None):
	account = frappe.db.sql("""
		SELECT
			dept.expense_account
		FROM
			`tabSub Branch` sub_br
		INNER JOIN
			`tabBranch` br
			ON 
				br.name = sub_br.branch
		INNER JOIN
			`tabDepartment` dept
			ON 
				dept.name = br.department
		WHERE 
			sub_br.name = '{0}'
	""".format(sub_branch), as_dict=True)

	if(not sub_branch):
		frappe.throw("No Expense Account for parent of sub branch {0}".format(sub_branch))
	if(not account or len(account) == 0):
		frappe.throw("There is not link to Expense account through sub branch {0}".format(sub_branch))

	return account[0]["expense_account"]