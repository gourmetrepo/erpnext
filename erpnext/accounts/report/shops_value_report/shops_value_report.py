# Copyright (c) 2013, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

from __future__ import unicode_literals
from frappe import _
from nrp_manufacturing.utils import get_config_by_name
import frappe

def execute(filters=None):
    if not filters: filters = {}
    columns = get_columns(filters)
    
    from datetime import datetime, date, timedelta
    #starttime = datetime.now().strftime("%m/%d/%Y, %H:%M:%S")
    shop_date_str = filters.get('shop_date')
    if shop_date_str:
        today = datetime.strptime(shop_date_str, "%Y-%m-%d").date()
    
    yesterday = today - timedelta(days=1)
    
    data = []
    shop_value_account_config = get_config_by_name('shop_value_account_config')
    for (unit,unit_accounts) in shop_value_account_config.items():
        if unit==filters.company:
            data = frappe.db.sql(f"""SELECT  party as customer,c.customer_name,account,SUM(shop_value) as shop_value,GROUP_CONCAT(ref_doc) AS ref_doc  FROM
(
SELECT   party,account,SUM(credit)-SUM(debit) AS shop_value, GROUP_CONCAT(CONCAT('''',Voucher_no, '''' )) AS ref_doc
                    FROM `tabGL Entry` 
                    WHERE account IN ({unit_accounts.get('accounts')})
                    AND DATE(posting_date) ='{yesterday}'  AND company='{unit}' AND Voucher_type='Sales Invoice' AND party IN (SELECT DISTINCT customer FROM `tabCustomers Company Assignment` WHERE company='{unit}')
                    GROUP BY  account, party
                    
                    UNION ALL
                    SELECT  GROUP_CONCAT(CONCAT('''',Voucher_no, '''' )) AS ref_doc ,account, party , SUM(credit)-SUM(debit) AS shop_value 
                    FROM `tabGL Entry` 
                    WHERE account IN ({unit_accounts.get('accounts')})
                    AND DATE(posting_date) ='{today}'  AND company='{unit}' AND name NOT LIKE "%ACC-SVJV%" AND Voucher_type='Journal Entry' AND party IN (SELECT DISTINCT customer FROM `tabCustomers Company Assignment` WHERE company='{unit}')
                    GROUP BY  account, party
                
                    UNION ALL
                    SELECT  GROUP_CONCAT(CONCAT('''',Voucher_no, '''' )) AS ref_doc ,account, party , SUM(credit)-SUM(debit) AS shop_value 
                    FROM `tabGL Entry` 
                    WHERE account IN ({unit_accounts.get('accounts')})
                    AND DATE(posting_date) ='{today}'  AND company='{unit}' AND Voucher_type='Payment Entry' AND party IN (SELECT DISTINCT customer FROM `tabCustomers Company Assignment` WHERE company='{unit}')
                    GROUP BY  account, party
                
                    UNION ALL
                    SELECT  GROUP_CONCAT(CONCAT('''',Voucher_no, '''' )) AS ref_doc ,account, party , SUM(credit)-SUM(debit) AS shop_value 
                    FROM `tabGL Entry` 
                    WHERE account IN ({unit_accounts.get('ng_accounts')})
                    AND DATE(posting_date) ='{today}' AND company='{unit}' AND Voucher_type='Payment Entry' AND party IN (SELECT DISTINCT customer FROM `tabCustomers Company Assignment` WHERE company='{unit}')
                    GROUP BY  account, party
                
                    UNION ALL
                    SELECT  GROUP_CONCAT(CONCAT('''',Voucher_no, '''' )) AS ref_doc ,account, party , SUM(credit)-SUM(debit) AS shop_value 
                    FROM `tabGL Entry` 
                    WHERE account IN ({unit_accounts.get('ng_accounts')})
                    AND DATE(posting_date) ='{today}' AND company='{unit}' AND Voucher_type='Sales Invoice' AND party IN (SELECT DISTINCT customer FROM `tabCustomers Company Assignment` WHERE company='{unit}')
                    GROUP BY  account, party
                    ) AS a
                    INNER JOIN `tabCustomer` AS c ON a.party = c.`name`  
                    GROUP BY party, account""",as_dict=True,debug=True)



    return columns, data


def get_columns(filters):
    """return columns based on filters"""

    columns = [_("Customer") + ":Link/Customer:100"]  + [_("Customer Name") + "::150"] + [_("Account") + "::150"] + \
                 [_("Shop Value") + ":Float:120"] + [_("Ref Doc") + "::420"] 
    
    return columns
