from __future__ import unicode_literals
from frappe import _


def get_data():
    """
    Add evetns module to desk home screen.
    """
    return [
        {
            "label": _("Sugar Mill"),
            "icon": "octicon octicon-briefcase",
                    "items": [
                {
                    "type": "doctype",
                    "name": "VTS",
                    "label": _("VTS"),
                    "description": _("VTS Module Description."),
                },
            ]
        }
    ]
