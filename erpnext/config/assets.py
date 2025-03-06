from __future__ import unicode_literals
from frappe import _

def get_data():
	return [
		{
			"label": _("Assets"),
			"items": [
				{
					"type": "doctype",
					"name": "Asset",
					"onboard": 1,
				},
				{
					"type": "doctype",
					"name": "Location",
					"onboard": 1,
				},
				{
					"type": "doctype",
					"name": "Asset Category",
					"onboard": 1,
				},
				{
					"type": "doctype",
					"name": "Asset Movement",
					"description": _("Transfer an asset from one warehouse to another")
				},
			]
		},
		{
			"label": _("Maintenance"),
			"items": [
				{
					"type": "doctype",
					"name": "Asset Maintenance Team",
					"onboard": 1,
				},
				{
					"type": "doctype",
					"name": "Asset Maintenance",
					"onboard": 1,
					"dependencies": ["Asset Maintenance Team"],
				},
				{
					"type": "doctype",
					"name": "Asset Maintenance Tasks",
					"onboard": 1,
					"dependencies": ["Asset Maintenance"],
				},
				{
					"type": "doctype",
					"name": "Asset Maintenance Log",
					"dependencies": ["Asset Maintenance"],
				},
				{
					"type": "doctype",
					"name": "Asset Value Adjustment",
					"dependencies": ["Asset"],
				},
				{
					"type": "doctype",
					"name": "Asset Repair",
					"dependencies": ["Asset"],
				},
			]
		},
		{
			"label": _("Reports"),
			"icon": "fa fa-table",
			"items": [
				{
					"type": "report",
					"name": "Asset Depreciation Ledger",
					"doctype": "Asset",
					"is_query_report": True,
					"dependencies": ["Asset"],
				},
				{
					"type": "report",
					"name": "Asset Depreciations and Balances",
					"doctype": "Asset",
					"is_query_report": True,
					"dependencies": ["Asset"],
				},
				{
					"type": "report",
					"name": "Asset Maintenance",
					"doctype": "Asset Maintenance",
					"dependencies": ["Asset Maintenance"]
				},
			]
		},
  		{
			"label": _("Assets Log Management"),
			"items": [
				{
					"type": "doctype",
					"name": "Vehicle"
				},
				{
					"type": "doctype",
					"name": "Vehicle Log"
				},
				{
					"type": "report",
					"is_query_report": True,
					"name": "Vehicle Expenses",
					"doctype": "Vehicle",
					"title":"Maintenance Asset Expenses"
				},
			]
		},
		{
            "label": _("Plant Maintenance"),
            "items": [
                 {
                    "type": "doctype",
                    "name": "Maintenance",
                    "description": _("Maintenance and Downtime"),
                    "label": _("Downtime"),
                    "onboard": 1
                },
				{
                    "type": "doctype",
                    "name": "CIP Standard Time Setup",
                    "description": _("CIP Standard Time Setup"),
                    "label": _("CIP Standard Time Setup"),
                    "onboard": 1
                },
				{
                    "type": "doctype",
                    "name": "Asset Maintenance",
                    "description": _("Asset Maintenance"),
                    "label": _("Asset Maintenance"),
                    "onboard": 1
                },
				{
                    "type": "doctype",
                    "name": "Asset Maintenance Log",
                    "description": _("Asset Maintenance Log"),
                    "label": _("Asset Maintenance Log"),
                    "onboard": 1
                },
				{
                    "type": "doctype",
                    "name": "Work Order",
                    "description": _("Work Order"),
                    "label": _("Work Order"),
                    "onboard": 1
                },
				{
                    "type": "doctype",
                    "name": "Cost Center",
                    "description": _("Cost Center"),
                    "label": _("Cost Center"),
                    "onboard": 1
                },
				{
                    "type": "doctype",
                    "name": "Ranking Setup",
                    "description": _("Ranking Setup"),
                    "label": _("Ranking Setup"),
                    "onboard": 1
                },
				{
                    "type": "doctype",
                    "name": "Parameter Setup",
                    "description": _("Parameter Setup"),
                    "label": _("Parameter Setup"),
                    "onboard": 1
                },
				{
                    "type": "doctype",
                    "name": "Compliance Verification",
                    "description": _("Compliance Verification"),
                    "label": _("Compliance Verification"),
                    "onboard": 1
                }
            ]
        }
	]
