# Copyright (c) 2013, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

from __future__ import unicode_literals
from frappe import _
from nrp_manufacturing.utils import get_config_by_name
import frappe


def execute(filters=None):
    if not filters:
        filters = {}
    columns = get_columns(filters)
    from datetime import datetime, date, timedelta

    shop_date_str = filters.get("shop_date")
    if shop_date_str:
        today = datetime.strptime(shop_date_str, "%Y-%m-%d").date()

    yesterday = today - timedelta(days=1)

    data = []
    shop_value_account_config = get_config_by_name("shop_value_account_config")
    for unit, unit_accounts in shop_value_account_config.items():
        if unit == filters.company:
            query_result = frappe.db.sql(
                f"""SELECT  party as customer,c.customer_name,account,SUM(shop_value) as shop_value,GROUP_CONCAT(ref_doc) AS ref_doc  FROM
(
SELECT party,account,SUM(credit)-SUM(debit) AS shop_value, GROUP_CONCAT(CONCAT('''',Voucher_no, '''' )) AS ref_doc
                    FROM `tabGL Entry` 
                    WHERE account IN ({unit_accounts.get('accounts')})
                    AND DATE(posting_date) ='{yesterday}'  AND company='{unit}' AND Voucher_type='Sales Invoice' AND party IN (SELECT DISTINCT customer FROM `tabCustomers Company Assignment` WHERE company='{unit}')
                    GROUP BY  account, party
                    
                    UNION ALL
                    SELECT party,account,SUM(credit)-SUM(debit) AS shop_value, GROUP_CONCAT(CONCAT('''',Voucher_no, '''' )) AS ref_doc
                    FROM `tabGL Entry` 
                    WHERE account IN ({unit_accounts.get('accounts')})
                    AND DATE(posting_date) ='{today}'  AND company='{unit}' AND name NOT LIKE "%ACC-SVJV%" AND Voucher_type='Journal Entry' AND party IN (SELECT DISTINCT customer FROM `tabCustomers Company Assignment` WHERE company='{unit}')
                    GROUP BY  account, party
                
                    UNION ALL
                    SELECT party,account,SUM(credit)-SUM(debit) AS shop_value, GROUP_CONCAT(CONCAT('''',Voucher_no, '''' )) AS ref_doc
                    FROM `tabGL Entry` 
                    WHERE account IN ({unit_accounts.get('accounts')})
                    AND DATE(posting_date) ='{today}'  AND company='{unit}' AND Voucher_type='Payment Entry' AND party IN (SELECT DISTINCT customer FROM `tabCustomers Company Assignment` WHERE company='{unit}')
                    GROUP BY  account, party
                
                    UNION ALL
                    SELECT party,account,SUM(credit)-SUM(debit) AS shop_value, GROUP_CONCAT(CONCAT('''',Voucher_no, '''' )) AS ref_doc
                    FROM `tabGL Entry` 
                    WHERE account IN ({unit_accounts.get('ng_accounts')})
                    AND DATE(posting_date) ='{today}' AND company='{unit}' AND Voucher_type='Payment Entry' AND party IN (SELECT DISTINCT customer FROM `tabCustomers Company Assignment` WHERE company='{unit}')
                    GROUP BY  account, party
                
                    UNION ALL
                    SELECT party,account,SUM(credit)-SUM(debit) AS shop_value, GROUP_CONCAT(CONCAT('''',Voucher_no, '''' )) AS ref_doc
                    FROM `tabGL Entry` 
                    WHERE account IN ({unit_accounts.get('ng_accounts')})
                    AND DATE(posting_date) ='{today}' AND company='{unit}' AND Voucher_type='Sales Invoice' AND party IN (SELECT DISTINCT customer FROM `tabCustomers Company Assignment` WHERE company='{unit}')
                    GROUP BY  account, party
                    ) AS a
					INNER JOIN `tabCustomer` AS c ON a.party = c.`name`  
                    GROUP BY party, account""",
                as_dict=True,
            )

            grouped_data = {}
            for row in query_result:
                customer = row["customer"]
                row["shop_value"] = row["shop_value"] or 0
                row["ref_doc"] = row["ref_doc"] or "-"
                row["ref_doc"] = ", ".join(
                    ref_doc.strip("'") for ref_doc in row["ref_doc"].split(",")
                )

                if customer not in grouped_data:
                    grouped_data[customer] = {
                        "customer": customer,
                        "customer_name": row["customer_name"],
                        "shop_value": 0,
                        "ref_doc": None,
                        "indent": 0,
                        "child_data": [],
                    }
                grouped_data[customer]["child_data"].append(
                    {
                        "account": row["account"],
                        "shop_value": row["shop_value"],
                        "ref_doc": row["ref_doc"],
                        "indent": 1,
                    }
                )

                grouped_data[customer]["shop_value"] += row["shop_value"]
            for customer, customer_data in grouped_data.items():
                data.append(customer_data)
                data.extend(customer_data["child_data"])

            columns = get_columns(filters)

    return columns, data


def get_columns(filters):
    """return columns based on filters"""

    columns = (
        [_("Customer") + ":Link/Customer:100"]
        + [_("Customer Name") + "::150"]
        + [_("Account") + "::350"]
        + [_("Shop Value") + ":Float:120"]
        + [_("Ref Doc") + "::520"]
    )

    return columns
