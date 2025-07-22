# nerp/config/recruitment.py
from frappe import _

def get_data():
    return [
        {
            "label": _("Recruitment"),
            "icon": "octicon octicon-briefcase",
            "items": [
                {
                    "type": "doctype",
                    "name": "Position",
                    "label": _("Position"),
                    "description": _("Job positions within the organization"),
                    "onboard": 1
                },
                {
                    "type": "doctype",
                    "name": "Job Requisition",
                    "label": _("Job Requisition"),
                    "description": _("Requests for new hires"),
                    "onboard": 1
                },
                {
                    "type": "doctype",
                    "name": "Job Opening",
                    "label": _("Job Opening"),
                    "description": _("Available job openings"),
                    "onboard": 1
                },
                {
                    "type": "doctype",
                    "name": "Job Applicant",
                    "label": _("Job Applicant"),
                    "description": _("Candidates applying for jobs"),
                    "onboard": 1
                },
                {
                    "type": "doctype",
                    "name": "Interview",
                    "label": _("Interview"),
                    "description": _("Scheduled interviews"),
                    "onboard": 1
                },
                {
                    "type": "doctype",
                    "name": "Interview Feedback",
                    "label": _("Interview Feedback"),
                    "description": _("Feedback from interviewers"),
                    "onboard": 1
                },
                {
                    "type": "doctype",
                    "name": "Job Offer",
                    "label": _("Job Offer"),
                    "description": _("Offers made to selected applicants"),
                    "onboard": 1
                }
            ]
        }
    ]
