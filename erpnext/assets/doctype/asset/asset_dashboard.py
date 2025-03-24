from __future__ import unicode_literals

def get_data():
    return {
        'fieldname': 'asset_name',
        'non_standard_fieldnames': {
            'Asset Movement': 'asset',
            'Asset Capitalization': 'asset_id',
            'Sales Invoice': 'asset'
        },
        'transactions': [
            {
                'label': 'Maintenance',
                'items': ['Asset Maintenance', 'Asset Maintenance Log']
            },
            {
                'label': 'Repair',
                'items': ['Asset Repair']
            },
            {
                'label': 'Movement',
                'items': ['Asset Movement']
            },
            {
                'label': 'Capitalization',
                'items': ['Asset Capitalization']
            },
            {
                'label': 'Sales Invoice',
                'items': ['Sales Invoice']
            }
        ]
    }
