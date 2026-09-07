import csv
import io
from datetime import datetime

import frappe
from frappe import _


COMMISSION_DOCTYPE = "Commission"


ALLOWED_EXPORT_FIELDS = [
    "name",
    "posting_date",
    "sol_id",
    "sol_description",
    "agent_code",
    "agent_name",
    "scheme_code",
    "scheme_description",
    "pan_card",
    "pan_status",
    "cif",
    "agent_security_account",
    "agent_operative_account",
    "eligible_amount",
    "commission_amount",
    "tds",
    "security_deposit",
    "netpay",
]


def parse_date(value, field_label):
    if not value:
        frappe.throw(_("{0} is required.").format(field_label))

    try:
        return datetime.strptime(value.strip(), "%Y-%m-%d").date()
    except ValueError:
        frappe.throw(
            _("{0} must be a valid date.").format(field_label)
        )


def parse_csv_values(value):
    """Convert a comma-separated value string into a distinct cleaned list."""
    if not value:
        return []

    values = []
    seen = set()

    for item in str(value).split(","):
        item = item.strip()

        if item and item not in seen:
            values.append(item)
            seen.add(item)

    return values


def get_report_filters(from_date, to_date, sol_id=None, agent_code=None, scheme_code=None):
    """Build Commission filters using dates and optional multi-select values."""
    from_date = parse_date(from_date, "From Date")
    to_date = parse_date(to_date, "To Date")

    if from_date > to_date:
        frappe.throw(_("From Date cannot be greater than To Date."))

    filters = {
        "posting_date": ["between", [from_date, to_date]]
    }

    sol_ids = parse_csv_values(sol_id)
    agent_codes = parse_csv_values(agent_code)
    scheme_codes = parse_csv_values(scheme_code)

    if sol_ids:
        filters["sol_id"] = ["in", sol_ids]

    if agent_codes:
        filters["agent_code"] = ["in", agent_codes]

    if scheme_codes:
        filters["scheme_code"] = ["in", scheme_codes]

    return filters


def get_distinct_values(fieldname):
    """Get cleaned, non-empty, distinct values from tabCommission."""
    allowed_fields = {"sol_id", "agent_code", "scheme_code"}

    if fieldname not in allowed_fields:
        frappe.throw(_("Invalid filter field."))

    rows = frappe.db.sql(
        f"""
        SELECT DISTINCT `{fieldname}` AS value
        FROM `tabCommission`
        WHERE IFNULL(TRIM(`{fieldname}`), '') != ''
        ORDER BY `{fieldname}` ASC
        """,
        as_dict=True,
    )

    return [str(row.value).strip() for row in rows if row.value]


@frappe.whitelist()
def get_commission_report_options():
    return {
        "sol_ids": get_distinct_values("sol_id"),
        "agent_codes": get_distinct_values("agent_code"),
        "scheme_codes": get_distinct_values("scheme_code"),
    }


@frappe.whitelist()
def download_commission_report(
    from_date,
    to_date,
    sol_id=None,
    agent_code=None,
    scheme_code=None,
):
    """Generate and download a CSV Commission report."""
    filters = get_report_filters(
        from_date=from_date,
        to_date=to_date,
        sol_id=sol_id,
        agent_code=agent_code,
        scheme_code=scheme_code,
    )

    records = frappe.get_all(
        COMMISSION_DOCTYPE,
        filters=filters,
        fields=ALLOWED_EXPORT_FIELDS,
        order_by="posting_date asc, sol_id asc, agent_code asc, scheme_code asc",
        limit_page_length=0,
    )

    output = io.StringIO()
    writer = csv.writer(output)

    writer.writerow([
        "ID",
        "Posting Date",
        "SOL ID",
        "SOL Description",
        "Agent Code",
        "Agent Name",
        "Scheme Code",
        "Scheme Description",
        "PAN Card",
        "PAN Status",
        "CIF",
        "Security Account",
        "Operative Account",
        "Eligible Amount",
        "Commission Amount",
        "TDS",
        "Security Deposit",
        "Net Pay",
    ])

    for row in records:
        writer.writerow([
            row.get("name") or "",
            row.get("posting_date") or "",
            row.get("sol_id") or "",
            row.get("sol_description") or "",
            row.get("agent_code") or "",
            row.get("agent_name") or "",
            row.get("scheme_code") or "",
            row.get("scheme_description") or "",
            row.get("pan_card") or "",
            row.get("pan_status") or "",
            row.get("cif") or "",
            row.get("agent_security_account") or "",
            row.get("agent_operative_account") or "",
            row.get("eligible_amount") or 0,
            row.get("commission_amount") or 0,
            row.get("tds") or 0,
            row.get("security_deposit") or 0,
            row.get("netpay") or 0,
        ])

    safe_from_date = from_date.replace("-", "")
    safe_to_date = to_date.replace("-", "")

    frappe.local.response.filename = (
        f"commission_report_{safe_from_date}_to_{safe_to_date}.csv"
    )
    frappe.local.response.filecontent = output.getvalue()
    frappe.local.response.type = "download"

    return None
