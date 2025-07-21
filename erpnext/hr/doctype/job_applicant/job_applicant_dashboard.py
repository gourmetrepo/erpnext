from __future__ import unicode_literals
from frappe import _

def get_data():
     return {
        'fieldname': 'job_applicant',
        'non_standard_fieldnames': {
             "Interview": "job_applicant_id",
        },
        'transactions': [
            {
                'items': ['Employee', 'Employee Onboarding']
            },
            {
                'items': ['Job Offer', 'Interview']
            },
        ],
    }