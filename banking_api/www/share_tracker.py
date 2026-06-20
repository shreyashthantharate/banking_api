import json
import frappe
from frappe.utils import cint

CACHE_TTL = 20


def _cache():
    return frappe.cache()


def _make_cache_key(prefix, payload=None):
    payload = payload or {}
    return f"share_tracker::{prefix}::{frappe.as_json(payload, indent=None, separators=(',', ':'))}"


SOL_DESC_TTL = 4 * 24 * 60 * 60  # 4 days


def _sol_desc_cache_key(sol_id):
    return f"share_tracker::sol_desc::{sol_id}"


def get_sol_description(sol_id):
    sol_id = (sol_id or "").strip()
    if not sol_id:
        return ""

    cache_key = _sol_desc_cache_key(sol_id)
    cached = _cache().get_value(cache_key)
    if cached is not None:
        return cached

    branch_name = frappe.db.get_value(
        "Sahayog Branch",
        {"sol_id": sol_id},
        "branch"
    ) or ""

    _cache().set_value(cache_key, branch_name, expires_in_sec=SOL_DESC_TTL)
    return branch_name


def attach_sol_descriptions(rows):
    for row in rows:
        sol_id = row.get("sol_id")
        row["sol_desc"] = get_sol_description(sol_id)
    return rows


# def get_context(context):
#     return context

def get_avatar_from_name(full_name):
    full_name = (full_name or "").strip()
    if not full_name:
        return "U"

    parts = [p for p in full_name.split() if p]
    if not parts:
        return "U"

    if len(parts) == 1:
        return parts[0][0].upper()

    return (parts[0][0] + parts[-1][0]).upper()


def get_context(context):
    user = frappe.session.user

    context.user_display_name = "Unknown User"
    context.user_employee_id = user
    context.user_avatar = "U"

    if not user or user == "Guest":
        return context

    employee = frappe.db.get_value(
        "Employee",
        {"user_id": user},
        ["employee_name", "name"],
        as_dict=True
    )

    if employee:
        display_name = (employee.get("employee_name") or "").strip() or user
        employee_id = employee.get("name") or user

        context.user_display_name = display_name
        context.user_employee_id = employee_id
        context.user_avatar = get_avatar_from_name(display_name)
    else:
        fallback_name = frappe.db.get_value("User", user, "full_name") or user
        context.user_display_name = fallback_name
        context.user_employee_id = user
        context.user_avatar = get_avatar_from_name(fallback_name)

    return context


@frappe.whitelist()
def get_share_tracker_counts():
    cache_key = _make_cache_key("counts")
    cached = _cache().get_value(cache_key)
    if cached:
        return cached

    data = {
        "total": frappe.db.count("Share Application"),
        "pending": frappe.db.count("Share Application", {"payment_status": "Pending"}),
        "success": frappe.db.count("Share Application", {"payment_status": "Success"}),
        "insuf": frappe.db.count("Share Application", {"insufficient_balance": 1}),
        "closed": frappe.db.count("Share Application", {"account_closed": 1}),
    }

    _cache().set_value(cache_key, data, expires_in_sec=CACHE_TTL)
    return data


@frappe.whitelist()
def get_share_tracker_sol_ids(view="all", search=None):
    filters = {}

    if view == "pending":
        filters["payment_status"] = "Pending"
    elif view == "success":
        filters["payment_status"] = "Success"
    elif view == "insuf":
        filters["insufficient_balance"] = 1
    elif view == "closed":
        filters["account_closed"] = 1

    cache_payload = {
        "view": view,
        "search": search
    }
    cache_key = _make_cache_key("sol_ids", cache_payload)
    cached = _cache().get_value(cache_key)
    if cached:
        return cached

    if search:
        search = str(search).strip()
        like_txt = f"%{search}%"
        rows = frappe.get_all(
            "Share Application",
            fields=["sol_id"],
            filters=filters,
            or_filters=[
                ["Share Application", "name", "like", like_txt],
                ["Share Application", "sol_id", "like", like_txt],
                ["Share Application", "cif", "like", like_txt],
                ["Share Application", "account_number", "like", like_txt],
                ["Share Application", "transaction_id", "like", like_txt],
                ["Share Application", "payment_status", "like", like_txt],
            ]
        )
    else:
        rows = frappe.get_all(
            "Share Application",
            fields=["sol_id"],
            filters=filters
        )

    sol_ids = sorted({(row.get("sol_id") or "").strip()
                     for row in rows if row.get("sol_id")})
    _cache().set_value(cache_key, sol_ids, expires_in_sec=CACHE_TTL)
    return sol_ids


# @frappe.whitelist()
# def get_share_tracker_rows(view="all", page=1, page_length=10, search=None, sol_ids=None, sort_by="modified", sort_order="desc"):
    page = cint(page) or 1
    page_length = cint(page_length) or 10
    page = max(page, 1)

    allowed_sort_by = {"modified", "sol_id", "cif_creation_date",
                       "fund_transfer_date", "creation", "name"}
    allowed_sort_order = {"asc", "desc"}

    if sort_by not in allowed_sort_by:
        sort_by = "modified"
    if str(sort_order).lower() not in allowed_sort_order:
        sort_order = "desc"

    filters = {}

    if view == "pending":
        filters["payment_status"] = "Pending"
    elif view == "success":
        filters["payment_status"] = "Success"
    elif view == "insuf":
        filters["insufficient_balance"] = 1
    elif view == "closed":
        filters["account_closed"] = 1

    if sol_ids:
        if isinstance(sol_ids, str):
            sol_ids = json.loads(sol_ids)
        if sol_ids:
            filters["sol_id"] = ["in", sol_ids]

    fields = [
        "name",
        "sol_id",
        "cif",
        "account_number",
        "transaction_id",
        "payment_status",
        "insufficient_balance",
        "account_closed",
        "fund_transfer_date",
        "cif_creation_date",
        "account_opening_date",
        "error_log",
        "modified"
    ]

    cache_payload = {
        "view": view,
        "page": page,
        "page_length": page_length,
        "search": search,
        "sol_ids": sol_ids,
        "sort_by": sort_by,
        "sort_order": sort_order,
    }
    cache_key = _make_cache_key("rows", cache_payload)
    cached = _cache().get_value(cache_key)
    if cached:
        return cached

    start = (page - 1) * page_length

    if search:
        search = str(search).strip()
        like_txt = f"%{search}%"

        rows = frappe.get_all(
            "Share Application",
            fields=fields,
            filters=filters,
            or_filters=[
                ["Share Application", "name", "like", like_txt],
                ["Share Application", "sol_id", "like", like_txt],
                ["Share Application", "cif", "like", like_txt],
                ["Share Application", "account_number", "like", like_txt],
                ["Share Application", "transaction_id", "like", like_txt],
                ["Share Application", "payment_status", "like", like_txt],
            ],
            start=start,
            page_length=page_length,
            order_by=f"`tabShare Application`.`{sort_by}` {sort_order}"
        )

        total = len(frappe.get_all(
            "Share Application",
            pluck="name",
            filters=filters,
            or_filters=[
                ["Share Application", "name", "like", like_txt],
                ["Share Application", "sol_id", "like", like_txt],
                ["Share Application", "cif", "like", like_txt],
                ["Share Application", "account_number", "like", like_txt],
                ["Share Application", "transaction_id", "like", like_txt],
                ["Share Application", "payment_status", "like", like_txt],
            ]
        ))
    else:
        rows = frappe.get_all(
            "Share Application",
            fields=fields,
            filters=filters,
            start=start,
            page_length=page_length,
            order_by=f"`tabShare Application`.`{sort_by}` {sort_order}"
        )
        total = frappe.db.count("Share Application", filters=filters)

    rows = attach_sol_descriptions(rows)

    result = {
        "rows": rows,
        "total": total,
        "page": page,
        "page_length": page_length
    }

    _cache().set_value(cache_key, result, expires_in_sec=CACHE_TTL)
    return result


@frappe.whitelist()
# def get_share_tracker_rows(view="all", page=1, page_length=10, search=None, sol_ids=None, sort_by="modified", sort_order="desc"):
@frappe.whitelist()
def get_share_tracker_rows(
    view="all",
    page=1,
    page_length=10,
    search=None,
    sol_ids=None,
    from_date=None,
    to_date=None,
    sort_by="modified",
    sort_order="desc"
):
    page = cint(page) or 1
    page_length = cint(page_length) or 10
    page = max(page, 1)

    allowed_sort_by = {"modified", "sol_id", "cif_creation_date",
                       "fund_transfer_date", "creation", "name"}
    allowed_sort_order = {"asc", "desc"}

    if sort_by not in allowed_sort_by:
        sort_by = "modified"
    if str(sort_order).lower() not in allowed_sort_order:
        sort_order = "desc"

    filters = {}

    if view == "pending":
        filters["payment_status"] = "Pending"
    elif view == "success":
        filters["payment_status"] = "Success"
    elif view == "insuf":
        filters["insufficient_balance"] = 1
    elif view == "closed":
        filters["account_closed"] = 1

    if sol_ids:
        if isinstance(sol_ids, str):
            sol_ids = json.loads(sol_ids)
        if sol_ids:
            filters["sol_id"] = ["in", sol_ids]

    if from_date and to_date:
        filters["fund_transfer_date"] = ["between", [from_date, to_date]]
    elif from_date:
        filters["fund_transfer_date"] = [">=", from_date]
    elif to_date:
        filters["fund_transfer_date"] = ["<=", to_date]

    fields = [
        "name",
        "sol_id",
        "cif",
        "account_number",
        "transaction_id",
        "payment_status",
        "insufficient_balance",
        "account_closed",
        "fund_transfer_date",
        "cif_creation_date",
        "account_opening_date",
        "error_log",
        "modified"
    ]

    # cache_payload = {
    #     "view": view,
    #     "page": page,
    #     "page_length": page_length,
    #     "search": search,
    #     "sol_ids": sol_ids,
    #     "sort_by": sort_by,
    #     "sort_order": sort_order,
    # }

    cache_payload = {
        "view": view,
        "page": page,
        "page_length": page_length,
        "search": search,
        "sol_ids": sol_ids,
        "from_date": from_date,
        "to_date": to_date,
        "sort_by": sort_by,
        "sort_order": sort_order,
    }
    cache_key = _make_cache_key("rows", cache_payload)
    cached = _cache().get_value(cache_key)
    if cached:
        return cached

    start = (page - 1) * page_length

    if search:
        search = str(search).strip()
        like_txt = f"%{search}%"

        rows = frappe.get_all(
            "Share Application",
            fields=fields,
            filters=filters,
            or_filters=[
                ["Share Application", "name", "like", like_txt],
                ["Share Application", "sol_id", "like", like_txt],
                ["Share Application", "cif", "like", like_txt],
                ["Share Application", "account_number", "like", like_txt],
                ["Share Application", "transaction_id", "like", like_txt],
                ["Share Application", "payment_status", "like", like_txt],
            ],
            start=start,
            page_length=page_length,
            order_by=f"`tabShare Application`.`{sort_by}` {sort_order}"
        )

        total = len(frappe.get_all(
            "Share Application",
            pluck="name",
            filters=filters,
            or_filters=[
                ["Share Application", "name", "like", like_txt],
                ["Share Application", "sol_id", "like", like_txt],
                ["Share Application", "cif", "like", like_txt],
                ["Share Application", "account_number", "like", like_txt],
                ["Share Application", "transaction_id", "like", like_txt],
                ["Share Application", "payment_status", "like", like_txt],
            ]
        ))
    else:
        rows = frappe.get_all(
            "Share Application",
            fields=fields,
            filters=filters,
            start=start,
            page_length=page_length,
            order_by=f"`tabShare Application`.`{sort_by}` {sort_order}"
        )
        total = frappe.db.count("Share Application", filters=filters)

    rows = attach_sol_descriptions(rows)

    result = {
        "rows": rows,
        "total": total,
        "page": page,
        "page_length": page_length
    }

    _cache().set_value(cache_key, result, expires_in_sec=CACHE_TTL)
    return result


# @frappe.whitelist()
# def get_share_application_by_cif(cif):
#     if not cif:
#         frappe.throw("CIF is required")

#     doc = frappe.db.get_value(
#         "Share Application",
#         {"cif": cif},
#         [
#             "name",
#             "sol_id",
#             "cif",
#             "account_number",
#             "transaction_id",
#             "payment_status",
#             "insufficient_balance",
#             "account_closed",
#             "fund_transfer_date",
#             "cif_creation_date",
#             "account_opening_date",
#             "error_log",
#             "modified"
#         ],
#         as_dict=True
#     )

#     if doc:
#         doc["sol_desc"] = get_sol_description(doc.get("sol_id"))

#     return doc


@frappe.whitelist()
def get_share_application_by_cif(cif):
    if not cif:
        frappe.throw("CIF is required")

    doc = frappe.db.get_value(
        "Share Application",
        {"cif": cif},
        [
            "name",
            "sol_id",
            "cif",
            "account_number",
            "transaction_id",
            "payment_status",
            "insufficient_balance",
            "account_closed",
            "account_frozen",
            "account_not_found",
            "retry_attempted",
            "last_retry_attempted",
            "fund_transfer_date",
            "cif_creation_date",
            "account_opening_date",
            "customer_name",
            "address",
            "scheme_type",
            "scheme_code",
            "transaction_amount",
            "error_log",
            "modified"
        ],
        as_dict=True
    )

    if doc:
        doc["sol_desc"] = get_sol_description(doc.get("sol_id"))

    return doc


def clear_share_tracker_cache():
    cache = _cache()
    cache.delete_keys("share_tracker::counts::*")
    cache.delete_keys("share_tracker::rows::*")
    cache.delete_keys("share_tracker::sol_ids::*")


def clear_sol_desc_cache(sol_id=None):
    cache = _cache()
    if sol_id:
        cache.delete_value(_sol_desc_cache_key(sol_id))
    else:
        cache.delete_keys("share_tracker::sol_desc::*")


def publish_share_tracker_update(doc=None, method=None):
    clear_share_tracker_cache()
    frappe.publish_realtime("share_tracker_updated", {
        "name": getattr(doc, "name", None),
        "cif": getattr(doc, "cif", None),
        "payment_status": getattr(doc, "payment_status", None),
        "sol_id": getattr(doc, "sol_id", None),
        "event": method
    })


# @frappe.whitelist()
# def get_share_tracker_export_rows(search=None, sol_ids=None, sort_by="modified", sort_order="desc"):
@frappe.whitelist()
def get_share_tracker_export_rows(search=None, sol_ids=None, from_date=None, to_date=None, sort_by="modified", sort_order="desc"):
    allowed_sort_by = {"modified", "sol_id", "cif_creation_date",
                       "fund_transfer_date", "creation", "name"}
    allowed_sort_order = {"asc", "desc"}

    if sort_by not in allowed_sort_by:
        sort_by = "modified"
    if str(sort_order).lower() not in allowed_sort_order:
        sort_order = "desc"

    filters = {}

    if sol_ids:
        if isinstance(sol_ids, str):
            sol_ids = json.loads(sol_ids)
        if sol_ids:
            filters["sol_id"] = ["in", sol_ids]

    if from_date and to_date:
        filters["fund_transfer_date"] = ["between", [
            f"{from_date} 00:00:00", f"{to_date} 23:59:59"]]
    elif from_date:
        filters["fund_transfer_date"] = [">=", f"{from_date} 00:00:00"]
    elif to_date:
        filters["fund_transfer_date"] = ["<=", f"{to_date} 23:59:59"]
    fields = [
        "name",
        "sol_id",
        "cif",
        "account_number",
        "transaction_id",
        "payment_status",
        "insufficient_balance",
        "account_closed",
        "fund_transfer_date",
        "cif_creation_date",
        "account_opening_date",
        "error_log",
        "modified"
    ]

    if search:
        search = str(search).strip()
        like_txt = f"%{search}%"

        rows = frappe.get_all(
            "Share Application",
            fields=fields,
            filters=filters,
            or_filters=[
                ["Share Application", "name", "like", like_txt],
                ["Share Application", "sol_id", "like", like_txt],
                ["Share Application", "cif", "like", like_txt],
                ["Share Application", "account_number", "like", like_txt],
                ["Share Application", "transaction_id", "like", like_txt],
                ["Share Application", "payment_status", "like", like_txt],
            ],
            order_by=f"`tabShare Application`.`{sort_by}` {sort_order}",
            limit_page_length=0
        )
    else:
        rows = frappe.get_all(
            "Share Application",
            fields=fields,
            filters=filters,
            order_by=f"`tabShare Application`.`{sort_by}` {sort_order}",
            limit_page_length=0
        )

    rows = attach_sol_descriptions(rows)
    return rows
