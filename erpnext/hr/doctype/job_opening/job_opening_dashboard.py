# position_dashboard.py

from frappe import _
from frappe.desk.doctype.dashboard_chart.dashboard_chart import get_chart_config

def get_data():
    return {
        'fieldname': 'applied_on',
        'non_standard_fieldnames': {
        },
        'transactions': [
            {
                'items': ['Job Applicant']
            }
        ]
    }
