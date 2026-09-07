# import frappe


# def _build_conditions(filters):
#     """filters: list of [fieldname, operator, value]"""
#     conditions = []
#     values = {}
#     for i, f in enumerate(filters or []):
#         fieldname, operator, value = f[0], f[1], f[2]
#         key = f"val{i}"
#         if operator.lower() == "like":
#             conditions.append(f"`{fieldname}` LIKE %({key})s")
#             values[key] = f"%{value}%"
#         else:
#             conditions.append(f"`{fieldname}` = %({key})s")
#             values[key] = value
#     where_clause = " AND ".join(conditions) if conditions else "1=1"
#     return where_clause, values


# @frappe.whitelist()
# def get_commission_summary(filters=None):
#     filters = frappe.parse_json(filters) if filters else []
#     where_clause, values = _build_conditions(filters)

#     row = frappe.db.sql(
#         f"""
#         SELECT
#             COUNT(name) AS total_records,
#             COALESCE(SUM(CAST(NULLIF(TRIM(eligible_amount), '') AS DECIMAL(18,2))), 0) AS total_eligible,
#             COALESCE(SUM(CAST(NULLIF(TRIM(commission_amount), '') AS DECIMAL(18,2))), 0) AS total_commission,
#             COALESCE(SUM(CAST(NULLIF(TRIM(netpay), '') AS DECIMAL(18,2))), 0) AS total_netpay,
#             COALESCE(SUM(CAST(NULLIF(TRIM(security_deposit), '') AS DECIMAL(18,2))), 0) AS total_security_deposit
#         FROM `tabCommission`
#         WHERE {where_clause}
#         """,
#         values,
#         as_dict=True,
#     )

#     result = row[0] if row else {}
#     return {
#         "total_records": result.get("total_records") or 0,
#         "total_eligible": float(result.get("total_eligible") or 0),
#         "total_commission": float(result.get("total_commission") or 0),
#         "total_netpay": float(result.get("total_netpay") or 0),
#         "total_security_deposit": float(result.get("total_security_deposit") or 0),
#     }


# @frappe.whitelist()
# def get_commission_filter_options():
#     sol = frappe.db.get_list(
#         "Commission",
#         fields=["sol_id", "sol_description"],
#         group_by="sol_id",
#         order_by="sol_id",
#     )
#     scheme = frappe.db.get_list(
#         "Commission",
#         fields=["scheme_code"],
#         group_by="scheme_code",
#         order_by="scheme_code",
#         pluck="scheme_code",
#     )
#     agent = frappe.db.get_list(
#         "Commission",
#         fields=["agent_code"],
#         group_by="agent_code",
#         order_by="agent_code",
#         pluck="agent_code",
#     )

#     return {
#         "sol_list": [
#             {
#                 "value": r.sol_id,
#                 "label": f"{r.sol_id} - {r.sol_description}" if r.sol_description else str(r.sol_id),
#             }
#             for r in sol
#             if r.sol_id
#         ],
#         "scheme_list": [s for s in scheme if s],
#         "agent_list": [a for a in agent if a],
#     }


import frappe


def _build_conditions(filters):
    """filters: list of [fieldname, operator, value]"""
    conditions = []
    values = {}
    for i, f in enumerate(filters or []):
        fieldname, operator, value = f[0], f[1], f[2]
        key = f"val{i}"
        if operator.lower() == "like":
            conditions.append(f"`{fieldname}` LIKE %({key})s")
            values[key] = f"%{value}%"
        else:
            conditions.append(f"`{fieldname}` = %({key})s")
            values[key] = value
    where_clause = " AND ".join(conditions) if conditions else "1=1"
    return where_clause, values


# @frappe.whitelist()
# def get_commission_grouped(filters=None, limit_start=0, limit_page_length=10):
#     """Returns one consolidated row per agent_code, with SUM'd amount fields."""
#     filters = frappe.parse_json(filters) if filters else []
#     limit_start = int(limit_start)
#     limit_page_length = int(limit_page_length)

#     where_clause, values = _build_conditions(filters)

#     rows = frappe.db.sql(
#         f"""
#         SELECT
#             agent_code,
#             MAX(agent_name) AS agent_name,
#             MAX(sol_id) AS sol_id,
#             MAX(sol_description) AS sol_description,
#             MAX(scheme_code) AS scheme_code,
#             MAX(scheme_description) AS scheme_description,
#             MAX(pan_card) AS pan_card,
#             MAX(cif) AS cif,
#             MAX(security_account) AS security_account,
#             MAX(operative_account) AS operative_account,
#             COUNT(name) AS record_count,
#             COALESCE(SUM(CAST(NULLIF(TRIM(eligible_amount), '') AS DECIMAL(18,2))), 0) AS eligible_amount,
#             COALESCE(SUM(CAST(NULLIF(TRIM(commission_amount), '') AS DECIMAL(18,2))), 0) AS commission_amount,
#             COALESCE(SUM(CAST(NULLIF(TRIM(tds), '') AS DECIMAL(18,2))), 0) AS tds,
#             COALESCE(SUM(CAST(NULLIF(TRIM(security_deposit), '') AS DECIMAL(18,2))), 0) AS security_deposit,
#             COALESCE(SUM(CAST(NULLIF(TRIM(netpay), '') AS DECIMAL(18,2))), 0) AS netpay
#         FROM `tabCommission`
#         WHERE {where_clause}
#         GROUP BY agent_code
#         ORDER BY agent_code ASC
#         LIMIT %(limit_page_length)s OFFSET %(limit_start)s
#         """,
#         {**values, "limit_start": limit_start,
#             "limit_page_length": limit_page_length},
#         as_dict=True,
#     )
#     return rows


@frappe.whitelist()
def get_commission_grouped(filters=None, limit_start=0, limit_page_length=10):
    """Returns one consolidated row per agent_code, with SUM'd amount fields."""
    filters = frappe.parse_json(filters) if filters else []
    limit_start = int(limit_start)
    limit_page_length = int(limit_page_length)

    where_clause, values = _build_conditions(filters)

    rows = frappe.db.sql(
        f"""
            SELECT
                agent_code,
                MAX(agent_name) AS agent_name,
                MAX(sol_id) AS sol_id,
                MAX(sol_description) AS sol_description,
                MAX(scheme_code) AS scheme_code,
                MAX(scheme_description) AS scheme_description,
                MAX(pan_card) AS pan_card,
                MAX(pan_status) AS pan_status,
                MAX(cif) AS cif,
                MAX(agent_security_account) AS security_account,
                MAX(agent_operative_account) AS operative_account,
                COUNT(name) AS record_count,
                COALESCE(SUM(CAST(NULLIF(TRIM(eligible_amount), '') AS DECIMAL(18,2))), 0) AS eligible_amount,
                COALESCE(SUM(CAST(NULLIF(TRIM(commission_amount), '') AS DECIMAL(18,2))), 0) AS commission_amount,
                COALESCE(SUM(CAST(NULLIF(TRIM(tds), '') AS DECIMAL(18,2))), 0) AS tds,
                COALESCE(SUM(CAST(NULLIF(TRIM(security_deposit), '') AS DECIMAL(18,2))), 0) AS security_deposit,
                COALESCE(SUM(CAST(NULLIF(TRIM(netpay), '') AS DECIMAL(18,2))), 0) AS netpay
            FROM `tabCommission`
            WHERE {where_clause}
            GROUP BY agent_code
            ORDER BY agent_code ASC
            LIMIT %(limit_page_length)s OFFSET %(limit_start)s
        """,
        {**values, "limit_start": limit_start,
            "limit_page_length": limit_page_length},
        as_dict=True,
    )
    return rows


@frappe.whitelist()
def get_commission_grouped_count(filters=None):
    """Count of distinct agent_code groups matching the filters."""
    filters = frappe.parse_json(filters) if filters else []
    where_clause, values = _build_conditions(filters)

    row = frappe.db.sql(
        f"""
        SELECT COUNT(DISTINCT agent_code) AS total
        FROM `tabCommission`
        WHERE {where_clause}
        """,
        values,
        as_dict=True,
    )
    return row[0].get("total") or 0 if row else 0


@frappe.whitelist()
def get_commission_summary(filters=None):
    """Overall totals across ALL matching rows (not just current page) — used for stat cards."""
    filters = frappe.parse_json(filters) if filters else []
    where_clause, values = _build_conditions(filters)

    row = frappe.db.sql(
        f"""
        SELECT
            COUNT(DISTINCT agent_code) AS total_records,
            COALESCE(SUM(CAST(NULLIF(TRIM(eligible_amount), '') AS DECIMAL(18,2))), 0) AS total_eligible,
            COALESCE(SUM(CAST(NULLIF(TRIM(commission_amount), '') AS DECIMAL(18,2))), 0) AS total_commission,
            COALESCE(SUM(CAST(NULLIF(TRIM(netpay), '') AS DECIMAL(18,2))), 0) AS total_netpay,
            COALESCE(SUM(CAST(NULLIF(TRIM(security_deposit), '') AS DECIMAL(18,2))), 0) AS total_security_deposit
        FROM `tabCommission`
        WHERE {where_clause}
        """,
        values,
        as_dict=True,
    )

    result = row[0] if row else {}
    return {
        "total_records": result.get("total_records") or 0,
        "total_eligible": float(result.get("total_eligible") or 0),
        "total_commission": float(result.get("total_commission") or 0),
        "total_netpay": float(result.get("total_netpay") or 0),
        "total_security_deposit": float(result.get("total_security_deposit") or 0),
    }


@frappe.whitelist()
def get_commission_filter_options():
    sol = frappe.db.get_list(
        "Commission",
        fields=["sol_id", "sol_description"],
        group_by="sol_id",
        order_by="sol_id",
    )
    scheme = frappe.db.get_list(
        "Commission",
        fields=["scheme_code"],
        group_by="scheme_code",
        order_by="scheme_code",
        pluck="scheme_code",
    )
    agent = frappe.db.get_list(
        "Commission",
        fields=["agent_code"],
        group_by="agent_code",
        order_by="agent_code",
        pluck="agent_code",
    )

    return {
        "sol_list": [
            {
                "value": r.sol_id,
                "label": f"{r.sol_id} - {r.sol_description}" if r.sol_description else str(r.sol_id),
            }
            for r in sol
            if r.sol_id
        ],
        "scheme_list": [s for s in scheme if s],
        "agent_list": [a for a in agent if a],
    }


@frappe.whitelist(methods=["POST"])
def run_commission_payment(agent_codes=None, filters=None):
    agent_codes = frappe.parse_json(agent_codes) if isinstance(
        agent_codes, str) else (agent_codes or [])
    filters = frappe.parse_json(filters) if isinstance(
        filters, str) else (filters or [])

    if not agent_codes:
        frappe.throw("No agent codes provided for payment run.")

    # Exclude unselected agents: combine the incoming filters with an explicit
    # "agent_code IN (...)" restriction so payment only runs for selected agents.
    where_clause, values = _build_conditions(filters)

    placeholders = ", ".join(
        [f"%(agent_{i})s" for i in range(len(agent_codes))])
    for i, code in enumerate(agent_codes):
        values[f"agent_{i}"] = code

    # TODO: Replace this SELECT with your actual payment execution logic —
    # e.g. creating Payment Entry records, calling a bank disbursal API,
    # updating a "payment_status" field on Commission rows, etc.
    rows = frappe.db.sql(
        f"""
        SELECT agent_code,
               COALESCE(SUM(CAST(NULLIF(TRIM(netpay), '') AS DECIMAL(18,2))), 0) AS netpay
        FROM `tabCommission`
        WHERE {where_clause} AND agent_code IN ({placeholders})
        GROUP BY agent_code
        """,
        values,
        as_dict=True,
    )

    # frappe.db.commit() if you make DB changes above

    return {
        "status": "success",
        "paid_agents": [r.agent_code for r in rows],
        "total_paid": sum(float(r.netpay or 0) for r in rows),
    }
