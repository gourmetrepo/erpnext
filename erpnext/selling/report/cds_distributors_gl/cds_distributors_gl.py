from __future__ import unicode_literals
import frappe


def execute(filters=None):
    columns = get_columns()
    data = get_data(filters)
    return columns, data


def get_columns():
    return [
        {
            "label": "Customer Name",
            "fieldname": "customer_name",
            "fieldtype": "Data",
            "width": 150,
        },
        {
            "label": "Customer",
            "fieldname": "customer",
            "fieldtype": "Link",
            "options": "Customer",
            "width": 140,
        },
        {
            "label": "Territory",
            "fieldname": "territory",
            "width": 150,
        },
        {
            "label": "Owner's CNIC",
            "fieldname": "customer_cnic",
            "fieldtype": "Data",
            "width": 150,
        },
        {
            "label": "CSD Distributor Amount",
            "fieldname": "csd_distributor_amount",
            "fieldtype": "Currency",
            "width": 180,
        },
        {
            "label": "VSP Distributors Amount",
            "fieldname": "vsp_distributor_amount",
            "fieldtype": "Currency",
            "width": 170,
        },
        {
            "label": "CSD Distributor Security",
            "fieldname": "csd_distributors_security",
            "fieldtype": "Currency",
            "width": 170,
        },
        {
            "label": "VSP Supplier Amount",
            "fieldname": "vsp_supplier_amount",
            "fieldtype": "Currency",
            "width": 160,
        },
        {
            "label": "Total Amount",
            "fieldname": "total_amount",
            "fieldtype": "Currency",
            "width": 180,
        },
    ]


def get_data(filters):
    company = filters.get("company")
    customer_filter = filters.get("customer")
    active_filter = filters.get("active")

    if not company:
        return []

    disabled_status = 0 if active_filter else 1

    if customer_filter:
        primary_customers = frappe.db.sql(
            """
            SELECT name, customer_name, cnic, territory
            FROM `tabCustomer`
            WHERE primary_company = %s 
            AND customer_group = 'CSD Distributors' 
            AND name = %s 
            AND disabled = %s
        """,
            (company, customer_filter, disabled_status),
            as_dict=True,
        )
    else:
        primary_customers = frappe.db.sql(
            """
            SELECT name, customer_name, cnic, territory
            FROM `tabCustomer`
            WHERE primary_company = %s 
            AND customer_group = 'CSD Distributors' 
            AND disabled = %s
        """,
            (company, disabled_status),
            as_dict=True,
        )

    if not primary_customers:
        return []

    primary_customer_names = (
        [customer_filter] if customer_filter else [c.name for c in primary_customers]
    )

    secondary_customers = frappe.db.sql(
        """
        SELECT name, customer_name, cnic, primary_customer, customer_group
        FROM `tabCustomer`
        WHERE primary_customer IN %s
    """,
        (tuple(primary_customer_names),),
        as_dict=True,
    )

    all_customers = {c["name"]: c for c in primary_customers}
    for s in secondary_customers:
        all_customers[s["name"]] = s

    financials = frappe.db.sql(
        """
        SELECT party, SUM(debit) AS total_debit, SUM(credit) AS total_credit
        FROM `tabGL Entry`
        WHERE party_type = 'Customer' AND party IN %(customers)s AND company = %(company)s
        GROUP BY party
        """,
        {
            "customers": tuple(all_customers.keys()),
            "company": company
        },
        as_dict=True,
    )
    fin_map = {f["party"]: f for f in financials}

    data = []
    for parent in primary_customers:
        cust_name = parent["name"]
        children = [
            c for c in secondary_customers if c["primary_customer"] == cust_name
        ]

        vsp_distributor_total = 0
        vsp_supplier_total = 0
        csd_distributor_total = 0
        csd_distributor_security = 0

        parent_debit = fin_map.get(cust_name, {}).get("total_debit", 0)
        parent_credit = fin_map.get(cust_name, {}).get("total_credit", 0)
        parent_total =  parent_debit - parent_credit
        csd_distributor_total += parent_total

        for child in children:
            child_name = child["name"]
            group = child.get("customer_group")
            child_debit = fin_map.get(child_name, {}).get("total_debit", 0)
            child_credit = fin_map.get(child_name, {}).get("total_credit", 0)
            child_total = child_credit - child_debit

            if group == "VSP Distributors":
                vsp_distributor_total += child_total
            elif group == "VSP Supplier":
                vsp_supplier_total += child_total
            elif group == "CSD Distributors":
                csd_distributor_total += child_total
            elif group == "CSD Distributor Security":
                csd_distributor_security += child_total

        overall_total = (
            csd_distributor_total
            + vsp_distributor_total
            + vsp_supplier_total
            + csd_distributor_security
        )

        data.append(
            {
                "customer_name": parent.get("customer_name"),
                "customer": cust_name,
                "territory": parent.get("territory"),
                "customer_cnic": parent.get("cnic"),
                "csd_distributor_amount": csd_distributor_total,
                "vsp_distributor_amount": vsp_distributor_total,
                "csd_distributors_security": csd_distributor_security,
                "vsp_supplier_amount": vsp_supplier_total,
                "total_amount": overall_total,
            }
        )

    return data
