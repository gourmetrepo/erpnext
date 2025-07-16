from __future__ import unicode_literals
from frappe import _

def get_data():
	return {
		'fieldname': 'asset_maintenance',

		'non_standard_fieldnames': {
			'Journal Entry': 'plant_maintenance_reference',
		},

		'internal_links': {
			'Material Request': ['bill_of_material_and_services', 'mr_reference']
		},

		'transactions': [
			{
				'label': _('Procurement'),
				'items': ['Material Request', 'Stock Entry']
			},
			{
				'label': _('Accounting'),
				'items': ['Journal Entry']
			}
		]
	}
