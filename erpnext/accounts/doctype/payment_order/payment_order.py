from __future__ import unicode_literals
import frappe
from frappe import _
from frappe.utils import nowdate, flt
from erpnext.accounts.party import get_party_account
from erpnext.accounts.utils import get_balance_on


@frappe.whitelist()
def make_payment_records(name, supplier):
    doc = frappe.get_doc('Payment Order', name)
    make_journal_entry(doc, supplier)


def make_journal_entry(doc, supplier):
    je = frappe.new_doc('Journal Entry')
    je.payment_order = doc.name
    je.posting_date = nowdate()
    je.company = doc.company
    je.voucher_type = 'Journal Entry'

    mode_of_payment_list = frappe.db.get_list("Mode of Payment",  fields=['name'])
    payment_orders = {mode.name: {} for mode in mode_of_payment_list}

    accounts_details = {}
    for d in doc.references:
        if d.reference_name not in accounts_details:
            accounts_details[d.reference_name] = d
        else:
            accounts_details[d.reference_name].amount += d.amount

    for k, d in accounts_details.items():
        if supplier == d.supplier:
            remaining_amount = d.amount
            existing_amount = get_existing_journal_entry_amount(doc.name, supplier, d.reference_name)
            if existing_amount:
                remaining_amount -= existing_amount
                if remaining_amount == 0:
                    continue
            party_account = get_party_account('Supplier', d.supplier, doc.company)
            c_account = {'account': party_account,
                         'debit_in_account_currency': remaining_amount,
                         'party_type': 'Supplier',
                         'party': d.supplier,
                         'reference_type': d.reference_doctype,
                         'reference_name': d.reference_name}

            d_acc = payment_orders.get(d.mode_of_payment).get(d.account)
            if d_acc:
                d_acc['credit_in_account_currency'] += remaining_amount
                d_acc['c_accounts'].append(c_account)

            else:
                payment_orders[d.mode_of_payment][d.account] = {}

                d_account = {
                    'account': d.account,
                    'credit_in_account_currency': remaining_amount,
                    'balancec_accounts': [c_account]
                }

                payment_orders[d.mode_of_payment][d.account] = d_account

    for key, value in payment_orders.items():
        if value:
            for k, d_account in value.items():
                for c_acc in d_account.pop('c_accounts'):
                    je.append('accounts', c_acc)
            je.append('accounts', d_account)

    if not je.get('accounts'):
        frappe.throw("Journal Entry for this supplier's amount has already been submitted")

    je.flags.ignore_mandatory = True
    je.save()
    frappe.msgprint(_("{0} {1} created").format(je.doctype, je.name))


def get_existing_journal_entry_amount(po_dn, supplier, ref_dn):
    existing_payment_request_amount = frappe.db.sql(f"""
            select sum(ae.debit_in_account_currency)
            from `tabJournal Entry` je
            inner join `tabJournal Entry Account` ae
                on ae.parent = je.name and ae.party = '{supplier}' and ae.reference_name = '{ref_dn}'
            where je.payment_order = '{po_dn}'
                and je.docstatus = 1
                 """)
    return flt(existing_payment_request_amount[0][0]) if existing_payment_request_amount else 0


def before_save(doc, method):
    add_vendor_summary(doc)
    invoices = {}
    for item in doc.references:
        if item.reference_doctype == 'Purchase Invoice':
            if invoices.get(item.reference_name):
                frappe.throw(f"Purchase invoice duplicate found {item.reference_name}")
            else:
                invoices[item.reference_name] = item.reference_name
        if doc.account != item.account:
            frappe.throw("Payment Order Entry : "+item.payment_request+" have different account than Payment Order")


def add_vendor_summary(doc):
    vendor_details = {}
    company = doc.company
    for reference in doc.references:
        supplier = reference.supplier
        if supplier not in vendor_details:
            vendor_details[supplier] = {}
            vendor_details[supplier]['supplier_name'] = reference.supplier_name
            vendor_details[supplier]['req_amount'] = reference.amount
            vendor_details[supplier]['cheque_title'] = reference.cheque_title
            vendor_details[supplier]['outstanding_amount'] = -get_balance_on(party_type="Supplier", party=supplier, company=company)
        else:
            vendor_details[supplier]['req_amount'] += reference.amount

    doc.set('vendor_details', [])
    doc.set('total_amount', 0.0)
    for supplier, vendor_detail in vendor_details.items():
        child = doc.append('vendor_details')
        child.supplier = supplier
        child.supplier_name = vendor_detail['supplier_name']
        child.amount = vendor_detail['req_amount']
        child.t_outstanding_amount = vendor_detail['outstanding_amount']
        child.cheque_title = vendor_detail['cheque_title']

        doc.total_amount += child.amount

@frappe.whitelist()
def get_pmo_dashboard_balances(data):
    doc = frappe.get_doc("Payment Order", data)
    balance = 0
    mode_of_payment = None
    consumed_amount = 0
    consumed_amount = frappe.db.sql(f"""
           SELECT 
    (sum_pe + sum_ee + sum_je)AS total_sum
FROM (
    SELECT 
        IFNULL((SELECT SUM(paid_amount) FROM `tabPayment Entry` WHERE workflow_state IN ("Approved By Accounts Manager", "Approved By Manager Accounts", "Approved By CFO", "Approved By Director") AND docstatus = 0 AND paid_from = "{doc.account}"), 0) AS sum_pe,
        IFNULL((SELECT SUM(total) FROM `tabExpense Entry` WHERE workflow_state IN ("Approved By Accounts Manager", "Approved By CFO", "Approved By CEO", "Approved By Director") AND docstatus = 0 AND payment_account = "{doc.account}"), 0) AS sum_ee,
        IFNULL((SELECT SUM(credit) FROM `tabJournal Entry Account` WHERE parent IN (SELECT name FROM `tabJournal Entry` WHERE workflow_state IN ("Approved By Accounts Manager", "Approved By CFO") AND docstatus = 0) AND account = "{doc.account}" AND credit > 0), 0) AS sum_je
) AS subquery;""")
    consumed_amount=consumed_amount[0][0] if consumed_amount else 0.0
    if doc.get("payment_order_type")=="Payment Request":
        balance=get_balance_on(account=doc.get("account"), date=nowdate(), company=doc.get("company"))
    payment=0
    for item in doc.references:
        if doc.account == item.account:
            payment += item.amount
            mode_of_payment =item.mode_of_payment
        else:
            frappe.throw("Payment Order Entry : "+item.payment_request+" have different account than Payment Order")
    balances = {
    "mode_of_payment":mode_of_payment,
    "balance_before_payment":f"{balance:,}",
    "payment": f"{payment:,}",
    "balance_after_payment":f"{balance - payment:,}" ,
    "consumed_amount": f"{consumed_amount:,}" 
    }
    return balances

@frappe.whitelist()
def get_pmo_payment_history(pmono,company):
    payment_history = frappe.db.sql(f"""
                                    SELECT
    supplier,
    SUM(TBB) AS TBB,
    SUM(TVCD) AS TVCD,
    SUM(TPCP) AS TPCP,
    ROUND((SUM(TVCD) / SUM(TPCP) * 100), 3) AS PTOP,
    SUM(TOP) AS TOP,
    (SUM(TBB) - SUM(TPCP) - SUM(TOP)) AS TOBS
FROM (
    SELECT
        GL.party AS supplier,
        (SUM(GL.credit) - SUM(GL.debit)) AS TBB,
        0 AS TVCD,
        0 AS TPCP,
        0 AS PTOP,
        0 AS TOP,
        0 AS TOBS
    FROM `tabGL Entry` AS GL
    INNER JOIN `tabParty Account` AS PA ON GL.party = PA.parent AND PA.parenttype = 'Supplier' AND PA.company = '{company}'
        AND GL.account = PA.account
    WHERE GL.company = '{company}' AND GL.party_type = 'Supplier'
    AND GL.party IN (SELECT DISTINCT `supplier` FROM `tabPayment Order Detail` WHERE parent = '{pmono}')
    GROUP BY GL.party

    UNION ALL

    SELECT
        PIPO.supplier,
        0 AS TBB,
        SUM(PIPO.outstanding_amount) AS TVCD,
        0 AS TPCP,
        0 AS PTOP,
        0 AS TOP,
        0 AS TOBS
    FROM (
        SELECT `supplier`, SUM(outstanding_amount) AS outstanding_amount
        FROM `tabPurchase Invoice`
        WHERE NAME IN (SELECT DISTINCT `reference_name` FROM `tabPayment Order Reference` WHERE parent = '{pmono}')
        GROUP BY supplier

        UNION ALL

        SELECT
            PO.`supplier`,
            SUM(PO.grand_total) - SUM(debit) AS outstanding_amount
        FROM `tabPurchase Order` AS PO
        INNER JOIN `tabGL Entry` AS GL ON PO.name = GL.against_voucher AND against_voucher_type = 'Purchase Order' AND GL.party = PO.supplier
        WHERE PO.NAME IN (SELECT DISTINCT `reference_name` FROM `tabPayment Order Reference` WHERE parent = '{pmono}')
        GROUP BY PO.supplier
    ) AS PIPO
    GROUP BY PIPO.supplier

    UNION ALL

    SELECT
        `supplier`,
        0 AS TBB,
        0 AS TVCD,
        amount AS TPCP,
        0 AS PTOP,
        0 AS TOP,
        0 AS TOBS
    FROM `tabPayment Order Detail`
    WHERE parent = '{pmono}'

    UNION ALL
	
    SELECT
        `supplier`,
        0 AS TBB,
        0 AS TVCD,
        0 AS TPCP,
        0 AS PTOP,
        SUM(amount) AS TOP,
        0 AS TOBS
    FROM `tabPayment Order Detail`
    WHERE parent IN (
        SELECT NAME
        FROM `tabPayment Order`
        WHERE company = '{company}' AND docstatus = 0 AND NAME != '{pmono}'
    ) AND supplier IN (SELECT DISTINCT `supplier` FROM `tabPayment Order Detail` WHERE parent = '{pmono}')
    GROUP BY `supplier`
) AS CombinedData
GROUP BY supplier;""", as_dict =1)
    
    payment_history = [{key.lower(): value for key, value in item.items()} for item in payment_history]
    #[
    # { "supplier": "Ali", "tot_bal_bef": "300,000", "tot_bal_after": "20,000", "tot_val_curr_docs": "250,000", "tot_pmts_curr_pmo": "200,000", "percent_ptop": "80%", "tot_other_pmos": "80,000", "tot_os_bal_supp": "50,000" },
    # { "supplier": "Taha", "tot_bal_bef": "300,000", "tot_bal_after": "20,000", "tot_val_curr_docs": "250,000", "tot_pmts_curr_pmo": "200,000", "percent_ptop": "80%", "tot_other_pmos": "80,000", "tot_os_bal_supp": "50,000" }
    #     ]

    return payment_history