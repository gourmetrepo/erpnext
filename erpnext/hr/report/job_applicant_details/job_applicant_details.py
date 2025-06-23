from __future__ import unicode_literals
import frappe
from datetime import datetime

def execute(filters=None):
	columns = get_columns()
	data = get_data(filters)
	return columns, data

def get_columns():
	return [
		{"label": "Full Name", "fieldname": "full_name", "fieldtype": "Data", "width": 200},
		{"label": "Age", "fieldname": "age", "fieldtype": "Int", "width": 100},
		{"label": "Mobile", "fieldname": "mobile", "fieldtype": "Data", "width": 120},
		{"label": "Email", "fieldname": "email", "fieldtype": "Data", "width": 200},
		{"label": "Job Opening", "fieldname": "job_opening", "fieldtype": "Link", "options": "Job Opening", "width": 180},
		{"label": "Work Experience", "fieldname": "experience", "fieldtype": "Float", "width": 150},
		{"label": "Job Title", "fieldname": "job_title", "fieldtype": "Data", "width": 200},
		{"label": "Company", "fieldname": "company", "fieldtype": "Link", "options": "Company", "width": 150},
		{"label": "Start Date", "fieldname": "start_date", "fieldtype": "Date", "width": 150},
		{"label": "End Date", "fieldname": "end_date", "fieldtype": "Date", "width": 150},
		{"label": "Last Drawn Salary", "fieldname": "last_drawn_salary", "fieldtype": "Currency", "width": 150},
		{"label": "Perks & Benifits", "fieldname": "perks_and_benefits", "fieldtype": "Data", "width": 200},
		{"label": "Reason For Job Switch", "fieldname": "reason_for_leaving", "fieldtype": "Data", "width": 200},
		{"label": "Notice Period", "fieldname": "notice_period", "fieldtype": "Int", "width": 150},
		{"label": "Education Title", "fieldname": "education_title", "fieldtype": "Data", "width": 150},
		{"label": "Specialization", "fieldname": "specialization", "fieldtype": "Data", "width": 150},
		{"label": "Institute", "fieldname": "institute", "fieldtype": "Data", "width": 150},
		{"label": "Education Start Date", "fieldname": "edu_start_date", "fieldtype": "Date", "width": 150},
		{"label": "Education End Date", "fieldname": "edu_end_date", "fieldtype": "Date", "width": 150},
		{"label": "Marital Status", "fieldname": "marital_status", "fieldtype": "Data", "width": 150},
		{"label": "Permanent City", "fieldname": "permanent_city", "fieldtype": "Data", "width": 150},
		{"label": "Residing City", "fieldname": "residing_city", "fieldtype": "Data", "width": 150},
		{"label": "Open to Relocate", "fieldname": "open_to_relocate", "fieldtype": "Check", "width": 150}
	]

def get_data(filters=None):
	today = datetime.today()

	status_filter = filters.get('status') if filters and filters.get('status') else None
	job_opening_filter = filters.get('job_opening') if filters and filters.get('job_opening') else None

	data = frappe.db.sql("""
		SELECT
			ja.name,
			ja.first_name,
			ja.middle_name,
			ja.last_name,
			ja.date_of_birth,
			ja.email,
			ja.contact AS mobile,
			ja.applied_on AS job_opening,
			ja.total_work_experience_years,
			ja.availability_to_join_in_days,
			ja.permanent_city,
			ja.residing_city,
			ja.marital_status,
			jo.company AS job_company,
			ja.open_to_relocate AS open_to_relocate,
			we.job_title,
			we.company_name AS company,
			we.last_drawn_salary,
			we.end_date AS we_end_date,
			we.joining_date AS we_joining_date,
			we.currently_employed,
			we.perks_and_benifits AS perks_and_benefits,
			ja.reason_for_job_switch as reason_for_job_switch,
			ed.education_title AS education_title,
			ed.specialization AS specialization,
			ed.institute as institute,
			ed.start_date AS ed_start_date,
			ed.currently_enrolled AS currently_enrolled,
			ed.completion_date AS ed_completion_date
   
		FROM `tabJob Applicant` ja
		LEFT JOIN `tabJob Opening` jo ON jo.name = ja.applied_on
		LEFT JOIN `tabJob Applicant Work Experience` we ON we.parent = ja.name
		LEFT JOIN `tabJob Applicant Education` ed ON ed.parent = ja.name
		WHERE ja.job_applicant_status = %s AND ja.applied_on = %s
	""", (status_filter, job_opening_filter), as_dict=True, debug=True)

	result = []

	# Group by applicant
	applicants = {}
	for row in data:
		applicants.setdefault(row.name, []).append(row)

	for applicant_name, records in applicants.items():
		latest_experience = []
		latest_education = []
		for row in records:
			if row.get('company'):
				latest_experience.append({
					"company": row.get('company'),
					"job_title": row.get('job_title'),
					"currently_employed": row.get('currently_employed'),
					"last_drawn_salary": row.get('last_drawn_salary'),
					"start_date": row.get('we_joining_date'),
					"end_date": row.get('we_end_date'),
					"perks_and_benefits": row.get('perks_and_benefits')
				})

			if row.get('education_title'):
				latest_education.append({
					"education_title": row.get('education_title'),
					"specialization": row.get('specialization'),
					"institute": row.get('institute'),
					"start_date": row.get('ed_start_date'),
					"end_date": row.get('ed_completion_date'),
					"currently_enrolled": row.get('currently_enrolled'),
					"completion_date": row.get('ed_completion_date')
   				})

		selected_experience = {}
		if latest_experience:
			currently_employed = [exp for exp in latest_experience if exp.get('currently_employed') == 1]
			if currently_employed:
				selected_experience = currently_employed[0]
			else:
				selected_experience = max(
					(exp for exp in latest_experience if exp.get('end_date')),
					key=lambda x: x.get('end_date'),
					default={}
				)
		selected_education = {}
		if latest_education:
			currently_enrolled = [edu for edu in latest_education if edu.get('currently_enrolled') == 1]
			if currently_enrolled:
				selected_education = currently_enrolled[0]
			else:
				selected_education = max(
					(edu for edu in latest_education if edu.get('end_date')),
					key=lambda x: x.get('end_date'),
					default={}
				)

		base_row = records[0]

		full_name = " ".join(filter(None, [base_row.first_name, base_row.middle_name, base_row.last_name]))

		age = None
		if base_row.date_of_birth:
			dob = base_row.date_of_birth
			age = today.year - dob.year - ((today.month, today.day) < (dob.month, dob.day))

		result.append({
			"full_name": full_name,
			"age": age,
			"mobile": base_row.mobile,
			"email": base_row.email,
			"job_opening": base_row.job_opening,
			"experience": base_row.total_work_experience_years,
			"job_title": selected_experience.get('job_title'),
			"company": selected_experience.get('company'),
			"start_date": selected_experience.get('start_date'),
			"end_date": selected_experience.get('end_date'),
			"last_drawn_salary": selected_experience.get('last_drawn_salary') or 0,
			"perks_and_benefits": selected_experience.get('perks_and_benefits'),
			"reason_for_leaving": base_row.reason_for_job_switch,
			"notice_period": base_row.availability_to_join_in_days,
			"education_title": selected_education.get('education_title'),
			"specialization": selected_education.get('specialization'),
			"institute": selected_education.get('institute'),
			"edu_start_date": selected_education.get('start_date'),
			"edu_end_date": selected_education.get('end_date'),
			"marital_status": base_row.marital_status,
			"permanent_city": base_row.permanent_city,
			"residing_city": base_row.residing_city,
			"open_to_relocate": base_row.open_to_relocate
		})

	return result
