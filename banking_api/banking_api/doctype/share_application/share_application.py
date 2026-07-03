# Copyright (c) 2026, Talib Sheikh and contributors
# For license information, please see license.txt

from openpyxl.worksheet.table import Table, TableStyleInfo
from openpyxl.utils import get_column_letter
from openpyxl.styles import Font, PatternFill, Alignment
from openpyxl import Workbook
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


# @frappe.whitelist()
# def download_share_application_report(report_type):
#     report_type = (report_type or "").strip().lower()

#     filters = {}
#     fields = []
#     filename = ""

#     if report_type == "success":
#         filters = {"payment_status": "Success"}
#         fields = [
#             "sol_id",
#             "cif",
#             "account_number",
#             "transaction_id",
#             "fund_transfer_date",
#             "cif_creation_date",
#             "payment_status",
#         ]
#         filename = "share_application_success_report.csv"

#     elif report_type == "failed":
#         filters = {"payment_status": "Failed"}
#         fields = [
#             "sol_id",
#             "cif",
#             "account_number",
#             "cif_creation_date",
#             "payment_status",
#             "error_log",
#             "insufficient_balance",
#             "account_closed",
#         ]
#         filename = "share_application_failed_report.csv"

#     elif report_type == "insufficient_balance":
#         filters = {"insufficient_balance": 1}
#         fields = [
#             "sol_id",
#             "cif",
#             "account_number",
#             "cif_creation_date",
#             "payment_status",
#             "error_log",
#             "insufficient_balance",
#             "account_closed",
#         ]
#         filename = "share_application_insufficient_balance_report.csv"

#     elif report_type == "account_closed":
#         filters = {"account_closed": 1}
#         fields = [
#             "sol_id",
#             "cif",
#             "account_number",
#             "cif_creation_date",
#             "payment_status",
#             "error_log",
#             "insufficient_balance",
#             "account_closed",
#         ]
#         filename = "share_application_closed_account_report.csv"

#     else:
#         frappe.throw(_("Invalid report type."))

#     records = frappe.get_all(
#         "Share Application",
#         filters=filters,
#         fields=fields,
#         order_by="modified desc"
#     )

#     label_map = {
#         "sol_id": "SOL ID",
#         "cif": "CIF",
#         "account_number": "Account Number",
#         "transaction_id": "Transaction ID",
#         "fund_transfer_date": "Fund Transfer Date",
#         "cif_creation_date": "CIF Creation Date",
#         "payment_status": "Payment Status",
#         "error_log": "Error Log",
#         "insufficient_balance": "Insufficient Balance",
#         "account_closed": "Account Closed",
#     }

#     output = io.StringIO()
#     writer = csv.writer(output)

#     writer.writerow([label_map.get(field, field) for field in fields])

#     for row in records:
#         writer.writerow([row.get(field, "") for field in fields])

#     frappe.response.filename = filename
#     frappe.response.filecontent = output.getvalue()
#     frappe.response.type = "download"
#     frappe.response.display_content_as = "attachment"

###############################################################################################
# @frappe.whitelist()
# def download_share_application_report(report_type):
#     report_type = (report_type or "").strip().lower()

#     filters = {}
#     filename = ""

#     export_fields = [
#         "name",
#         # "docstatus",
#         "sol_id",
#         "cif",
#         "account_number",
#         "customer_name",
#         "address",
#         "scheme_type",
#         "scheme_code",
#         "transaction_amount",
#         "payment_status",
#         "failed_reason",
#         "transaction_id",
#         "fund_transfer_date",
#         "cif_creation_date",
#         "account_opening_date",
#         # "amended_from",
#         # "retry_attempted",
#         # "last_retry_attempted",
#         # "error_log",
#         # "owner",
#         # "creation",
#     ]

#     db_fields = [
#         "name",
#         "docstatus",
#         "sol_id",
#         "cif",
#         "account_number",
#         "customer_name",
#         "address",
#         "scheme_type",
#         "scheme_code",
#         "transaction_amount",
#         "payment_status",
#         "transaction_id",
#         "fund_transfer_date",
#         "cif_creation_date",
#         "account_opening_date",
#         # "amended_from",
#         # "retry_attempted",
#         # "last_retry_attempted",
#         # "error_log",
#         # "owner",
#         # "creation",
#         "insufficient_balance",
#         "account_closed",
#         "account_frozen",
#         "account_not_found",
#     ]

#     if report_type == "success":
#         filters = {"payment_status": "Success"}
#         filename = "share_application_success_report.csv"

#     elif report_type == "failed":
#         filters = {"payment_status": "Failed"}
#         filename = "share_application_failed_report.csv"

#     elif report_type == "pending":
#         filters = {"payment_status": "Pending"}
#         filename = "share_application_pending_report.csv"

#     elif report_type == "consolidated":
#         filters = {}
#         filename = "share_application_consolidated_report.csv"

#     else:
#         frappe.throw(_("Invalid report type."))

#     records = frappe.get_all(
#         "Share Application",
#         filters=filters,
#         fields=db_fields,
#         order_by="modified desc"
#     )

#     label_map = {
#         "name": "Share Application ID",
#         "docstatus": "Doc Status",
#         "sol_id": "SOL ID",
#         "cif": "CIF",
#         "account_number": "Account Number",
#         "customer_name": "Customer Name",
#         "address": "Address",
#         "scheme_type": "Scheme Type",
#         "scheme_code": "Scheme Code",
#         "transaction_amount": "Transaction Amount",
#         "payment_status": "Payment Status",
#         "failed_reason": "Failed Reason",
#         "transaction_id": "Transaction ID",
#         "fund_transfer_date": "Fund Transfer Date",
#         "cif_creation_date": "CIF Creation Date",
#         "account_opening_date": "Account Opening Date",
#         "amended_from": "Amended From",
#         "retry_attempted": "Retry Attempted",
#         "last_retry_attempted": "Last Retry Attempted",
#         "error_log": "API Response",
#         "owner": "Owner",
#         "creation": "Created On",
#     }

#     docstatus_map = {
#         0: "Draft",
#         1: "Submitted",
#         2: "Cancelled"
#     }

#     def get_failed_reason(row):
#         if row.get("payment_status") != "Failed":
#             return ""

#         if row.get("insufficient_balance"):
#             return "Insufficient Balance"
#         if row.get("account_closed"):
#             return "Account Closed"
#         if row.get("account_frozen"):
#             return "Account Frozen"
#         if row.get("account_not_found"):
#             return "Account Not Found"

#         return "Network Issue"

#     output = io.StringIO()
#     writer = csv.writer(output)

#     writer.writerow([label_map.get(field, field) for field in export_fields])

#     for row in records:
#         row_data = []

#         for field in export_fields:
#             if field == "failed_reason":
#                 value = get_failed_reason(row)
#             elif field == "docstatus":
#                 value = docstatus_map.get(row.get(field), row.get(field))
#             else:
#                 value = row.get(field, "")

#             row_data.append(value)

#         writer.writerow(row_data)

#     frappe.response.filename = filename
#     frappe.response.filecontent = output.getvalue()
#     frappe.response.type = "download"
#     frappe.response.display_content_as = "attachment"

###############################################################################################


@frappe.whitelist()
def download_share_application_report(report_type):
    report_type = (report_type or "").strip().lower()

    filters = {}
    filename = ""

    export_fields = [
        "name",
        # "docstatus",
        "sol_id",
        "cif",
        "account_number",
        "customer_name",
        "scheme_type",
        "scheme_code",
        "transaction_amount",
        "payment_status",
        "failed_reason",
        "transaction_id",
        "fund_transfer_date",
        "cif_creation_date",
        "account_opening_date",
        # "retry_attempted",
        # "last_retry_attempted",
        # "owner",
        # "creation",
        "address",
        # "error_log",
    ]

    db_fields = [
        "name",
        # "docstatus",
        "sol_id",
        "cif",
        "account_number",
        "customer_name",
        "scheme_type",
        "scheme_code",
        "transaction_amount",
        "payment_status",
        "transaction_id",
        "fund_transfer_date",
        "cif_creation_date",
        "account_opening_date",
        # "retry_attempted",
        # "last_retry_attempted",
        # "owner",
        # "creation",
        "address",
        # "error_log",
        "insufficient_balance",
        "account_closed",
        "account_frozen",
        "account_not_found",
    ]

    if report_type == "success":
        filters = {"payment_status": "Success"}
        filename = "share_application_success_report.csv"

    elif report_type == "failed":
        filters = {"payment_status": "Failed"}
        filename = "share_application_failed_report.csv"

    elif report_type == "pending":
        filters = {"payment_status": "Pending"}
        filename = "share_application_pending_report.csv"

    elif report_type == "consolidated":
        filters = {}
        filename = "share_application_consolidated_report.csv"

    else:
        frappe.throw(_("Invalid report type."))

    label_map = {
        "name": "Share Application ID",
        # "docstatus": "Doc Status",
        "sol_id": "SOL ID",
        "cif": "CIF",
        "account_number": "Account Number",
        "customer_name": "Customer Name",
        "scheme_type": "Scheme Type",
        "scheme_code": "Scheme Code",
        "transaction_amount": "Transaction Amount",
        "payment_status": "Payment Status",
        "failed_reason": "Failed Reason",
        "transaction_id": "Transaction ID",
        "fund_transfer_date": "Fund Transfer Date",
        "cif_creation_date": "CIF Creation Date",
        "account_opening_date": "Account Opening Date",
        # "retry_attempted": "Retry Attempted",
        # "last_retry_attempted": "Last Retry Attempted",
        # "owner": "Owner",
        # "creation": "Created On",
        "address": "Address",
        # "error_log": "API Response",
    }

    docstatus_map = {
        0: "Draft",
        1: "Submitted",
        2: "Cancelled",
    }

    def get_failed_reason(row):
        if row.get("payment_status") != "Failed":
            return ""

        if row.get("insufficient_balance"):
            return "Insufficient Balance"
        if row.get("account_closed"):
            return "Account Closed"
        if row.get("account_frozen"):
            return "Account Frozen"
        if row.get("account_not_found"):
            return "Account Not Found"

        return "Network Issue"

    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow([label_map.get(field, field) for field in export_fields])

    chunk_size = 10000
    start = 0

    while True:
        records = frappe.get_all(
            "Share Application",
            filters=filters,
            fields=db_fields,
            limit_start=start,
            limit_page_length=chunk_size,
            order_by="name asc"
        )

        if not records:
            break

        for row in records:
            row_data = []

            for field in export_fields:
                if field == "failed_reason":
                    value = get_failed_reason(row)
                elif field == "docstatus":
                    value = docstatus_map.get(row.get(field), row.get(field))
                else:
                    value = row.get(field, "")

                row_data.append(value)

            writer.writerow(row_data)

        start += chunk_size

    frappe.response.filename = filename
    frappe.response.filecontent = output.getvalue()
    frappe.response.type = "download"
    frappe.response.display_content_as = "attachment"


@frappe.whitelist()
def get_share_application_status_counts():
    data = frappe.db.sql("""
        SELECT payment_status, COUNT(*) AS count
        FROM `tabShare Application`
        GROUP BY payment_status
    """, as_dict=True)

    counts = {
        "Success": 0,
        "Pending": 0,
        "Failed": 0
    }

    for row in data:
        status = row.get("payment_status")
        if status in counts:
            counts[status] = row.get("count", 0)

    return counts
