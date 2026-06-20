# Copyright (c) 2026, Talib Sheikh and contributors
# For license information, please see license.txt

import frappe
import csv
import io
from frappe import _
from frappe.model.document import Document


class ShareApplication(Document):
    def autoname(self):
        from frappe import _
        from frappe.model.naming import getseries

        sol_id = str(self.sol_id or "").strip()

        if not sol_id:
            frappe.throw(_("SOL ID is mandatory for naming."))

        if not sol_id.isdigit():
            frappe.throw(_("SOL ID must contain digits only."))

        if len(sol_id) != 4:
            frappe.throw(_("SOL ID must be exactly 4 digits."))

        prefix = f"{sol_id}01"

        for _ in range(5):
            sequence = getseries("Share Application-", 9)
            new_name = f"{prefix}{sequence}"

            if not frappe.db.exists("Share Application", new_name):
                self.name = new_name
                return

        frappe.throw(
            _("Unable to generate a unique Share Application ID. Please try again."))

    def validate(self):
        if self.docstatus == 1:
            if self.payment_status != "Success":
                frappe.throw(
                    _("Only documents with Status = 'Success' can be submitted."))

            if not self.transaction_id:
                frappe.throw(
                    _("Transaction ID is mandatory before submission."))


@frappe.whitelist()
def download_share_application_report(report_type):
    report_type = (report_type or "").strip().lower()

    filters = {}
    fields = []
    filename = ""

    if report_type == "success":
        filters = {"payment_status": "Success"}
        fields = [
            "sol_id",
            "cif",
            "account_number",
            "transaction_id",
            "fund_transfer_date",
            "cif_creation_date",
            "payment_status",
        ]
        filename = "share_application_success_report.csv"

    elif report_type == "failed":
        filters = {"payment_status": "Failed"}
        fields = [
            "sol_id",
            "cif",
            "account_number",
            "cif_creation_date",
            "payment_status",
            "error_log",
            "insufficient_balance",
            "account_closed",
        ]
        filename = "share_application_failed_report.csv"

    elif report_type == "insufficient_balance":
        filters = {"insufficient_balance": 1}
        fields = [
            "sol_id",
            "cif",
            "account_number",
            "cif_creation_date",
            "payment_status",
            "error_log",
            "insufficient_balance",
            "account_closed",
        ]
        filename = "share_application_insufficient_balance_report.csv"

    elif report_type == "account_closed":
        filters = {"account_closed": 1}
        fields = [
            "sol_id",
            "cif",
            "account_number",
            "cif_creation_date",
            "payment_status",
            "error_log",
            "insufficient_balance",
            "account_closed",
        ]
        filename = "share_application_closed_account_report.csv"

    else:
        frappe.throw(_("Invalid report type."))

    records = frappe.get_all(
        "Share Application",
        filters=filters,
        fields=fields,
        order_by="modified desc"
    )

    label_map = {
        "sol_id": "SOL ID",
        "cif": "CIF",
        "account_number": "Account Number",
        "transaction_id": "Transaction ID",
        "fund_transfer_date": "Fund Transfer Date",
        "cif_creation_date": "CIF Creation Date",
        "payment_status": "Payment Status",
        "error_log": "Error Log",
        "insufficient_balance": "Insufficient Balance",
        "account_closed": "Account Closed",
    }

    output = io.StringIO()
    writer = csv.writer(output)

    writer.writerow([label_map.get(field, field) for field in fields])

    for row in records:
        writer.writerow([row.get(field, "") for field in fields])

    frappe.response.filename = filename
    frappe.response.filecontent = output.getvalue()
    frappe.response.type = "download"
    frappe.response.display_content_as = "attachment"
