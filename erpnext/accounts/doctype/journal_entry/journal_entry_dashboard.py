from __future__ import unicode_literals
from frappe import _

def get_data():
	return {
		'fieldname': 'journal_entry',
		'non_standard_fieldnames': {
            'Payment Request': 'reference_name',
		},
		
		'transactions': [
			{
				'label': _('Payment'),
				'items': ['Payment Request']
			},
			
		]
	}
