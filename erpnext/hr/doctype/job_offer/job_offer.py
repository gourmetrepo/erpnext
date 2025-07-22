# Copyright (c) 2015, Frappe Technologies Pvt. Ltd. and Contributors and contributors
# For license information, please see license.txt

from __future__ import unicode_literals
import frappe
from frappe.utils import cint
from frappe.model.document import Document
from frappe.model.mapper import get_mapped_doc
from frappe import _
from frappe.utils.data import get_link_to_form, getdate, nowdate
from frappe.utils.pdf import get_pdf

class JobOffer(Document):
	def on_update_after_submit(self):
		if self.applicant_id:
			if self.offer_status == "Accepted":
				frappe.db.set_value("Job Applicant", self.applicant_id, "job_applicant_status", "Offer Accepted")
			elif self.offer_status == "Declined":
				frappe.db.set_value("Job Applicant", self.applicant_id, "job_applicant_status", "Offer Rejected")

	def before_save(self):
		if self.is_new() and self.offer_status != "Offered":
			frappe.throw(_("Job Offer can only be created with status <b>Offered<b>"))

		if getdate(self.offer_date) < getdate(nowdate()):
			frappe.throw(_("Offer Date cannot be in the past."))

	def on_submit(self):
		if self.applicant_id:	
			frappe.db.set_value("Job Applicant", self.applicant_id, "job_applicant_status", "Offered")

	def on_cancel(self):
		self.offer_status = "Cancelled"
		if self.applicant_id:
			frappe.db.set_value("Job Applicant", self.applicant_id, "job_applicant_status", "Accepted")


def update_job_applicant(status, job_applicant):
	if status in ("Accepted", "Rejected"):
		frappe.set_value("Job Applicant", job_applicant, "status", status)

def get_staffing_plan_detail(designation, company, offer_date):
	detail = frappe.db.sql("""
		SELECT DISTINCT spd.parent,
			sp.from_date as from_date,
			sp.to_date as to_date,
			sp.name,
			sum(spd.vacancies) as vacancies,
			spd.designation
		FROM `tabStaffing Plan Detail` spd, `tabStaffing Plan` sp
		WHERE
			sp.docstatus=1
			AND spd.designation=%s
			AND sp.company=%s
			AND spd.parent = sp.name
			AND %s between sp.from_date and sp.to_date
	""", (designation, company, offer_date), as_dict=1)

	return frappe._dict(detail[0]) if (detail and detail[0].parent) else None

@frappe.whitelist()
def make_employee(source_name, target_doc=None):
	def set_missing_values(source, target):
		target.personal_email = frappe.db.get_value("Job Applicant", source.job_applicant, "email_id")
	doc = get_mapped_doc("Job Offer", source_name, {
			"Job Offer": {
				"doctype": "Employee",
				"field_map": {
					"applicant_name": "employee_name",
				}}
		}, target_doc, set_missing_values)
	return doc


@frappe.whitelist()
def send_job_offer_email(job_offer_name):
    job_offer = frappe.get_doc("Job Offer", job_offer_name)
    applicant = frappe.get_doc("Job Applicant", job_offer.applicant_id)
    
    if not applicant or not applicant.email:
        frappe.throw("No applicant email found.")
    subject = f"Job Offer for {job_offer.position_title} at Gourmet Pakistan"
    message = f"""
		<p>Dear {applicant.full_name},</p>
  		<p>I am pleased to extend the following offer of employment to you on behalf of Gourmet Foods. You have been selected for the position of {job_offer.position_title}”.
		<p>Congratulations!</p>
  		<p>We believe that your knowledge, skills and experience would be an ideal fit for our team. We hope you will enjoy your role and make a significant contribution to the overall success of Gourmet foods.</p>
		<p>Please acknowledge the Job offer letter attached, mention your date of joining and share it back after signing it. In case of any query kindly contact me.</p>
		<br>
  		<p>Kindly bring 4 Passport size pics , 4 CNIC’s copies , 1 CNIC’s copy of Beneficiary, and all your experience and educational certificates / Letters copies on your date of joining.</p>
		<br>
        <p>Best Regards,</p>
        <p>Human Resources<br>Gourmet Pakistan</p>
    """

    # Rendering html of print format "Job Offer Template" and sending it as attachment in mail.
    html = frappe.get_print(
        "Job Offer", 
        job_offer_name,
        print_format="Job Offer Template",
        as_pdf=False        
    )
    pdf_file = get_pdf(html)
    
    if not applicant.email:
        frappe.throw("No applicant email found.")
    frappe.sendmail(
        sender="recruitment@gourmetpakistan.com",
        recipients=applicant.email,
        subject=subject,
        message=message,
        attachments=[{
            "fname": f"Offer Letter.pdf",
            "fcontent": pdf_file,
        }]
    )
