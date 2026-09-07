# Copyright (c) 2026, Talib Sheikh and contributors
# For license information, please see license.txt

from tqdm import tqdm

import frappe
from frappe import _
from frappe.model.document import Document
from frappe.utils import add_to_date, cint, flt, getdate

import psycopg2
from psycopg2.extras import RealDictCursor


class Commission(Document):
    pass


def db_connection():
    """Connect to external PostgreSQL using Finacle DB Credentials."""
    try:
        creds = frappe.get_single("Finacle DB Credentials")

        port = int(creds.db_port) if creds.db_port else 5432

        return psycopg2.connect(
            host=creds.db_host,
            port=port,
            user=creds.db_user,
            password=creds.get_password("db_password"),
            database=creds.db_name,
        )

    except Exception:
        frappe.log_error(
            frappe.get_traceback(),
            "PostgreSQL Connection Failed",
        )
        frappe.throw(_("Database Connection Error"))


QUERY_1 = """
WITH account_data AS (
    SELECT
        d.rm_id,
        g2.emp_name AS rm_name,
        d2.operacc,
        g.cif_id,
        g.acct_opn_date,
        a2.relationshipopeningdate AS cif_id_opening_date,
        g.foracid,
        g.sol_id,
        sol.sol_desc,
        g.schm_code AS scheme_code,
        gsp.schm_desc,
        tam.deposit_period_days,
        tam.deposit_period_mths,
        tam.deposit_amount,
        /* ADDED - ACCOUNT NAME FROM GAM */
        g.acct_name
    FROM custom.dsamap d
    INNER JOIN tbaadm.gam g
        ON g.foracid = d.account_number
        AND g.schm_code IN ('2004','2005','2006','2010','2011','2012','2013','2014','2015')
    LEFT JOIN tbaadm.tam tam
        ON tam.acid = g.acid
    LEFT JOIN crmuser.accounts a2
        ON g.cif_id = a2.orgkey
    LEFT JOIN tbaadm.sol sol
        ON g.sol_id = sol.sol_id
    LEFT JOIN tbaadm.gsp gsp
        ON g.schm_code = gsp.schm_code
    LEFT JOIN custom.dsaauth d2
        ON d.rm_id = d2.user_id
    LEFT JOIN tbaadm.get g2
        ON d2.user_id = g2.emp_id
),
flow_data AS (
    SELECT
        d.rm_id,
        g.foracid,
        g.schm_code,
        SUM(tdt.flow_amt) AS total_flow_amount
    FROM custom.dsamap d
    INNER JOIN tbaadm.gam g
        ON g.foracid = d.account_number
        AND g.schm_code IN ('2004','2005','2006','2010','2011','2012','2013','2014','2015')
    INNER JOIN tbaadm.tdt tdt
        ON tdt.acid = g.acid
        AND tdt.flow_code = 'NI'
    WHERE
        tdt.flow_date BETWEEN DATE '2026-08-01' AND DATE '2026-08-31'
    GROUP BY d.rm_id, g.foracid, g.schm_code
    HAVING SUM(tdt.flow_amt) > 0
),
tran_data AS (
    SELECT
        d.rm_id,
        g.foracid,
        g.schm_code,
        SUM(dtt.tran_amt) AS total_tran_amt
    FROM custom.dsamap d
    INNER JOIN tbaadm.gam g
        ON g.foracid = d.account_number
        AND g.schm_code IN ('2004','2005','2006','2010','2011','2012','2013','2014','2015')
    INNER JOIN tbaadm.dtt dtt
        ON dtt.acid = g.acid
        AND dtt.flow_code = 'NI'
    WHERE
        (
            (dtt.tran_date BETWEEN DATE '2026-08-01' AND DATE '2026-08-31'
             AND dtt.value_date > DATE '2026-07-31')
            OR
            (dtt.tran_date > DATE '2026-08-31'
             AND dtt.value_date BETWEEN DATE '2026-08-01' AND DATE '2026-08-31')
            OR
            (dtt.value_date BETWEEN DATE '2026-08-01' AND DATE '2026-08-31'
             AND dtt.tran_date > DATE '2026-08-31')
        )
    GROUP BY d.rm_id, g.foracid, g.schm_code
    HAVING SUM(dtt.tran_amt) > 0
),
reference_data AS (
    SELECT
        ed.referencenumber,
        da.user_id AS rm_id
    FROM crmuser.entitydocument ed
    INNER JOIN tbaadm.gam g
        ON ed.orgkey = g.cif_id
    INNER JOIN custom.dsaauth da
        ON g.foracid = da.operacc
    WHERE ed.doccode = 'PAN'
)
SELECT
    ad.rm_id,
    ad.rm_name,
    ad.operacc,
    ad.cif_id,
    ad.acct_opn_date,
    ad.acct_opn_date,
    ad.cif_id_opening_date,
    ad.foracid,
    /* ADDED - ACCOUNT NAME */
    ad.acct_name,
    ad.deposit_amount,
    COALESCE(fd.total_flow_amount,0) AS total_flow_amount,
    /* CHANGED - SCHEME 2004 KA FLOW AMT SAME RAHEGA
       SCHEME 2005-2015 KA * 3 HOGA */
    CASE
        WHEN ad.scheme_code = '2004'
            THEN COALESCE(fd.total_flow_amount,0)
        WHEN ad.scheme_code IN ('2005','2006','2010','2011','2012','2013','2014','2015')
            THEN COALESCE(fd.total_flow_amount,0) * 3
        ELSE COALESCE(fd.total_flow_amount,0)
    END AS adjusted_flow_amount,
    COALESCE(td.total_tran_amt,0) AS total_tran_amt,
    LEAST(
        COALESCE(fd.total_flow_amount,0),
        COALESCE(td.total_tran_amt,0)
    ) AS commission_amount,
    CASE
        WHEN ad.acct_opn_date + INTERVAL '1 year' >= DATE '2026-08-31' THEN 'YES'
        ELSE 'NO'
    END AS one_year_completed,
    ad.deposit_period_days,
    ad.deposit_period_mths,
    COALESCE(rd.referencenumber,'N/A') AS referencenumber,
    ad.scheme_code,
    ad.schm_desc,
    ad.sol_id,
    ad.sol_desc
FROM account_data ad
LEFT JOIN flow_data fd
    ON ad.rm_id = fd.rm_id
    AND ad.foracid = fd.foracid
    AND ad.scheme_code = fd.schm_code
LEFT JOIN tran_data td
    ON ad.rm_id = td.rm_id
    AND ad.foracid = td.foracid
    AND ad.scheme_code = td.schm_code
LEFT JOIN reference_data rd
    ON ad.rm_id = rd.rm_id
WHERE
    COALESCE(td.total_tran_amt,0) > 0
    -- ADDED: SIRF RDDSA AUR DDDSA PREFIX WALE RM_ID
AND (
    UPPER(ad.rm_id) LIKE 'RDDSA%'
    OR UPPER(ad.rm_id) LIKE 'DDDSA%'
)
ORDER BY
    ad.foracid,
    ad.rm_id,
    ad.scheme_code;
    """


QUERY_2 = """
--COMMITION QUERY 2 -- COUNT 6,563
 
WITH account_data AS (
SELECT
ds.rm_id,
g2.emp_name AS rm_name,
d2.operacc,
g.foracid,
g.acct_name,                    /* ADDED - ACCOUNT NAME FROM GAM */
g.acct_opn_date,
tam.deposit_amount,
tam.deposit_period_mths,
tam.deposit_period_days,
COUNT(DISTINCT g.acid) AS count_acid_gam,
SUM(dtt.tran_amt) AS total_tran_amt_dtt,
SUM(tdt.flow_amt) AS total_flow_amt_tdt,
g.sol_id,
sol.sol_desc,
g.schm_code AS scheme_code,
gsp.schm_desc
FROM custom.dsamap AS ds
LEFT JOIN tbaadm.gam AS g
ON g.foracid = ds.account_number
AND g.schm_code IN (
'2001','2002','2003',
'2018','2019','2020','2021','2022','2023','2024','2025','2026','2027','2028','2029','2030','2031','2032','2033','2034','2035',
'2101','2102','2103','2104','2105','2106',
'2201','2202','2203',
'9001','9002'
)
AND g.acct_opn_date BETWEEN DATE '2026-08-01' AND DATE '2026-08-31'
AND g.acct_cls_flg = 'N'
LEFT JOIN tbaadm.tam AS tam
ON tam.acid = g.acid
LEFT JOIN tbaadm.dtt AS dtt
ON dtt.acid = g.acid
AND dtt.flow_code = 'PI'
AND dtt.tran_date BETWEEN DATE '2026-08-01' AND DATE '2026-08-31'
AND NOT (
dtt.value_date >= DATE '2026-07-01'
AND dtt.value_date < DATE '2026-08-01'
)
LEFT JOIN tbaadm.tdt AS tdt
ON tdt.acid = g.acid
AND tdt.flow_code = 'PI'
AND tdt.flow_date BETWEEN DATE '2026-08-01' AND DATE '2026-08-31'
LEFT JOIN custom.dsaauth AS d2
ON UPPER(ds.rm_id) = UPPER(d2.user_id)
LEFT JOIN tbaadm.get AS g2
ON d2.user_id = g2.emp_id
LEFT JOIN tbaadm.sol AS sol
ON g.sol_id = sol.sol_id
LEFT JOIN tbaadm.gsp AS gsp
ON gsp.schm_code = g.schm_code
GROUP BY
ds.rm_id,
g2.emp_name,
d2.operacc,
g.foracid,
g.acct_name,                    /* ADDED */
g.acct_opn_date,
tam.deposit_amount,
tam.deposit_period_mths,
tam.deposit_period_days,
g.sol_id,
sol.sol_desc,
g.schm_code,
gsp.schm_desc
),
reference_data AS (
SELECT
ed.referencenumber,
da.user_id AS rm_id
FROM crmuser.entitydocument AS ed
JOIN tbaadm.gam AS g
ON ed.orgkey = g.cif_id
JOIN custom.dsaauth AS da
ON g.foracid = da.operacc
WHERE ed.doccode = 'PAN'
)
SELECT
ad.rm_id,
ad.rm_name,
ad.operacc,
ad.foracid,
ad.acct_name,                   /* ADDED - ACCOUNT NAME */
ad.acct_opn_date,
ad.deposit_amount,
ad.deposit_period_mths,
ad.deposit_period_days,
ad.sol_id,
ad.sol_desc,
ad.scheme_code,
ad.schm_desc,
SUM(ad.total_tran_amt_dtt)      AS total_tran_amt_dtt,
SUM(ad.total_flow_amt_tdt)      AS total_flow_amt_tdt,
SUM(ad.total_flow_amt_tdt)      AS adjusted_flow_amount,
LEAST(
COALESCE(SUM(ad.total_tran_amt_dtt),0),
COALESCE(SUM(ad.total_flow_amt_tdt),0)
) AS commission_amount,
CASE
WHEN ad.acct_opn_date + INTERVAL '1 year' <= DATE '2026-08-31' THEN 'YES'
ELSE 'NO'
END AS one_year_completed,
MAX(COALESCE(rd.referencenumber,'N/A')) AS referencenumber
FROM account_data AS ad
LEFT JOIN reference_data AS rd
ON UPPER(ad.rm_id) = UPPER(rd.rm_id)
WHERE ad.total_tran_amt_dtt > 0
-- ADDED: SIRF RDDSA AUR DDDSA PREFIX WALE RM_ID
AND (
    UPPER(ad.rm_id) LIKE 'RDDSA%'
    OR UPPER(ad.rm_id) LIKE 'DDDSA%'
)
GROUP BY
ad.rm_id,
ad.rm_name,
ad.operacc,
ad.foracid,
ad.acct_name,                   /* ADDED */
ad.acct_opn_date,
ad.deposit_amount,
ad.deposit_period_mths,
ad.deposit_period_days,
ad.sol_id,
ad.sol_desc,
ad.scheme_code,
ad.schm_desc
ORDER BY
ad.sol_id,
ad.rm_id,
ad.scheme_code,
ad.deposit_period_mths;


"""


def _safe_int(value):
    if value in (None, "", "N/A"):
        return None

    try:
        return int(value)
    except Exception:
        try:
            return int(float(value))
        except Exception:
            return None


def _safe_str(value):
    if value is None:
        return None

    return str(value).strip()


def _create_commission_from_query_1(row):
    doc = frappe.get_doc({
        "doctype": "Commission",

        "agent_code": _safe_str(row.get("rm_id")),
        "agent_name": _safe_str(row.get("rm_name")),
        "agent_operative_account": _safe_str(row.get("operacc")),
        "customer_account_number": _safe_str(row.get("foracid")),
        "customer_account_name": _safe_str(row.get("acct_name")),
        "deposit_amount": _safe_int(row.get("deposit_amount")),

        "tenure_months": _safe_int(row.get("deposit_period_mths")),
        "tenure_days": _safe_int(row.get("deposit_period_days")),

        "demand": _safe_int(row.get("total_flow_amount")),
        "collection": _safe_int(row.get("total_tran_amt")),

        # New fields
        "eligible_amount": _safe_int(row.get("commission_amount")),
        "account_opening_date": row.get("acct_opn_date"),
        "remarks": _safe_str(row.get("one_year_completed")),

        "pan_card": _safe_str(row.get("referencenumber")),
        "scheme_code": _safe_str(row.get("scheme_code")),
        "scheme_description": _safe_str(row.get("schm_desc")),
        "sol_id": _safe_str(row.get("sol_id")),
        "sol_description": _safe_str(row.get("sol_desc")),
    })

    doc.insert(ignore_permissions=True)
    frappe.db.commit()

    return doc.name


def _create_commission_from_query_2(row):
    doc = frappe.get_doc({
        "doctype": "Commission",

        "agent_code": _safe_str(row.get("rm_id")),
        "agent_name": _safe_str(row.get("rm_name")),
        "agent_operative_account": _safe_str(row.get("operacc")),
        "customer_account_number": _safe_str(row.get("foracid")),
        "customer_account_name": _safe_str(row.get("acct_name")),
        "deposit_amount": _safe_int(row.get("deposit_amount")),

        "tenure_months": _safe_int(row.get("deposit_period_mths")),
        "tenure_days": _safe_int(row.get("deposit_period_days")),

        "demand": _safe_int(row.get("total_flow_amt_tdt")),
        "collection": _safe_int(row.get("total_tran_amt_dtt")),

        # New fields
        "eligible_amount": _safe_int(row.get("commission_amount")),
        "account_opening_date": row.get("acct_opn_date"),
        "remarks": _safe_str(row.get("one_year_completed")),

        "pan_card": _safe_str(row.get("referencenumber")),
        "scheme_code": _safe_str(row.get("scheme_code")),
        "scheme_description": _safe_str(row.get("schm_desc")),
        "sol_id": _safe_str(row.get("sol_id")),
        "sol_description": _safe_str(row.get("sol_desc")),
    })

    doc.insert(ignore_permissions=True)
    frappe.db.commit()

    return doc.name


def _run_query(connection, query):
    with connection.cursor(cursor_factory=RealDictCursor) as cursor:
        cursor.execute(query)
        return cursor.fetchall()


@frappe.whitelist()
def fetch_and_create_commission():
    """
    Execute Query 2 first, then Query 1.
    Each document is inserted and committed individually.
    """
    frappe.only_for(("System Manager",))

    conn = None
    inserted_docs = []
    errors = []
    query_1_rows = []
    query_2_rows = []

    try:
        conn = db_connection()

        # Query 2 first, preserving current logic
        query_2_rows = _run_query(conn, QUERY_2)

        for row in query_2_rows:
            try:
                docname = _create_commission_from_query_2(row)
                inserted_docs.append(docname)

            except Exception:
                frappe.db.rollback()

                error_message = (
                    f"Query 2 row failed for foracid "
                    f"{row.get('foracid')}: {frappe.get_traceback()}"
                )

                frappe.log_error(
                    error_message,
                    "Commission Import Query 2 Row Error",
                )

                errors.append(error_message)

        # Query 1 second, preserving current logic
        query_1_rows = _run_query(conn, QUERY_1)

        for row in query_1_rows:
            try:
                docname = _create_commission_from_query_1(row)
                inserted_docs.append(docname)

            except Exception:
                frappe.db.rollback()

                error_message = (
                    f"Query 1 row failed for foracid "
                    f"{row.get('foracid')}: {frappe.get_traceback()}"
                )

                frappe.log_error(
                    error_message,
                    "Commission Import Query 1 Row Error",
                )

                errors.append(error_message)

        return {
            "status": "completed",
            "query_1_fetched": len(query_1_rows),
            "query_2_fetched": len(query_2_rows),
            "query_1_created": sum(
                1 for name in inserted_docs
                if name
            ),
            "query_2_created": len(inserted_docs),
            "inserted_count": len(inserted_docs),
            "error_count": len(errors),
            "errors": errors,
        }

    except Exception:
        frappe.db.rollback()
        frappe.log_error(
            frappe.get_traceback(),
            "Commission Import Failed",
        )
        raise

    finally:
        if conn:
            conn.close()


@frappe.whitelist()
def run_fetch_and_create_commission_with_progress(limit=None):
    """
    Execute Query 1 and Query 2 with terminal progress.
    Each document is inserted and committed individually.
    """
    frappe.only_for(("System Manager",))

    conn = None
    inserted_docs = []
    errors = []

    try:
        if limit is not None and str(limit).strip():
            limit = int(limit)

            if limit <= 0:
                frappe.throw(_("Limit must be greater than 0"))
        else:
            limit = None

        conn = db_connection()

        query_1_rows = _run_query(conn, QUERY_1)
        query_2_rows = _run_query(conn, QUERY_2)

        total_available = len(query_1_rows) + len(query_2_rows)
        total_to_process = (
            min(limit, total_available)
            if limit
            else total_available
        )

        created_count = 0
        query_1_created = 0
        query_2_created = 0

        progress = tqdm(
            total=total_to_process,
            desc="Creating Commission Docs",
            unit="doc",
        )

        try:
            for row in query_1_rows:
                if limit and created_count >= limit:
                    break

                try:
                    docname = _create_commission_from_query_1(row)

                    inserted_docs.append(docname)
                    created_count += 1
                    query_1_created += 1
                    progress.update(1)

                except Exception:
                    frappe.db.rollback()

                    error_message = (
                        f"Query 1 row failed for foracid "
                        f"{row.get('foracid')}: {frappe.get_traceback()}"
                    )

                    frappe.log_error(
                        error_message,
                        "Commission Import Query 1 Row Error",
                    )

                    errors.append(error_message)

            for row in query_2_rows:
                if limit and created_count >= limit:
                    break

                try:
                    docname = _create_commission_from_query_2(row)

                    inserted_docs.append(docname)
                    created_count += 1
                    query_2_created += 1
                    progress.update(1)

                except Exception:
                    frappe.db.rollback()

                    error_message = (
                        f"Query 2 row failed for foracid "
                        f"{row.get('foracid')}: {frappe.get_traceback()}"
                    )

                    frappe.log_error(
                        error_message,
                        "Commission Import Query 2 Row Error",
                    )

                    errors.append(error_message)

        finally:
            progress.close()

        print("\nCommission Fetch Completed")
        print(f"Query 1 Rows Fetched: {len(query_1_rows)}")
        print(f"Query 2 Rows Fetched: {len(query_2_rows)}")
        print(f"Query 1 Docs Created: {query_1_created}")
        print(f"Query 2 Docs Created: {query_2_created}")
        print(f"Total Docs Created: {len(inserted_docs)}")
        print(f"Total Errors: {len(errors)}")

        return {
            "status": "completed",
            "limit": limit,
            "query_1_fetched": len(query_1_rows),
            "query_2_fetched": len(query_2_rows),
            "query_1_created": query_1_created,
            "query_2_created": query_2_created,
            "inserted_count": len(inserted_docs),
            "error_count": len(errors),
            "errors": errors,
        }

    except Exception:
        frappe.db.rollback()
        frappe.log_error(
            frappe.get_traceback(),
            "Commission Import Failed",
        )
        raise

    finally:
        if conn:
            conn.close()


@frappe.whitelist()
def debug_fetch_commission_data():
    frappe.only_for(("System Manager",))

    conn = None

    try:
        conn = db_connection()

        query_1_rows = _run_query(conn, QUERY_1)
        query_2_rows = _run_query(conn, QUERY_2)

        print("\n===== COMMISSION DEBUG FETCH =====")
        print(f"QUERY 1 ROW COUNT: {len(query_1_rows)}")
        print(f"QUERY 2 ROW COUNT: {len(query_2_rows)}")

        if query_1_rows:
            print("QUERY 1 FIRST ROW:")
            print(query_1_rows[0])
        else:
            print("QUERY 1 returned no rows")

        if query_2_rows:
            print("QUERY 2 FIRST ROW:")
            print(query_2_rows[0])
        else:
            print("QUERY 2 returned no rows")

        return {
            "query_1_count": len(query_1_rows),
            "query_2_count": len(query_2_rows),
            "query_1_first_row": query_1_rows[0] if query_1_rows else None,
            "query_2_first_row": query_2_rows[0] if query_2_rows else None,
        }

    except Exception:
        frappe.log_error(
            frappe.get_traceback(),
            "Commission Debug Fetch Failed",
        )
        raise

    finally:
        if conn:
            conn.close()


@frappe.whitelist()
def debug_create_one_commission():
    frappe.only_for(("System Manager",))

    conn = None

    try:
        conn = db_connection()
        query_1_rows = _run_query(conn, QUERY_1)

        if not query_1_rows:
            return {"status": "no_data"}

        row = query_1_rows[0]
        docname = _create_commission_from_query_1(row)

        return {
            "status": "success",
            "docname": docname,
            "sample_row": row,
        }

    except Exception:
        frappe.log_error(
            frappe.get_traceback(),
            "Commission Debug Create One Failed",
        )
        raise

    finally:
        if conn:
            conn.close()


def _get_deferred_product(product_name):
    """
    Load Product including its deferred child table.
    frappe.db.get_value does not provide the child rows,
    so Deferred needs the full Product document.
    """
    product_doc = frappe.get_doc("Product", product_name)

    if product_doc.commission_type != "Deferred":
        frappe.throw(
            _("Product {0} is not configured for Deferred commission").format(
                product_name
            )
        )

    if not product_doc.deferred_commission_schedule:
        frappe.throw(
            _("Deferred Commission Schedule is missing in Product: {0}").format(
                product_name
            )
        )

    return product_doc


def _get_valid_deferred_schedule_rows(product_doc):
    """
    Read, validate, and sort enabled Product deferred schedule rows.
    """
    schedule_rows = []
    used_years = set()

    for row in product_doc.deferred_commission_schedule:
        if not row.enabled:
            continue

        year_no = cint(row.year_no)
        rate = flt(row.commission_rate)

        if year_no <= 0:
            frappe.throw(
                _("Deferred Year No must be greater than 0 in Product: {0}").format(
                    product_doc.name
                )
            )

        if year_no in used_years:
            frappe.throw(
                _("Duplicate Deferred Year No {0} in Product: {1}").format(
                    year_no,
                    product_doc.name
                )
            )

        if rate < 0:
            frappe.throw(
                _("Deferred commission rate cannot be negative for Year {0}").format(
                    year_no
                )
            )

        used_years.add(year_no)

        schedule_rows.append({
            "year_no": year_no,
            "rate": rate,
            "remarks": _safe_str(row.remarks),
        })

    if not schedule_rows:
        frappe.throw(
            _("No enabled deferred commission rows found in Product: {0}").format(
                product_doc.name
            )
        )

    return sorted(schedule_rows, key=lambda item: item["year_no"])


def _create_deferred_commission_schedule(commission_doc, product_doc, eligible_amount):
    """
    Create deferred payout schedule rows in the current Commission document.

    Example:
    Commission document created on 2026-08-19:
    Year 1 due: 2026-09-01
    Year 2 due: 2027-09-01
    Year 3 due: 2028-09-01
    """
    commission_meta = frappe.get_meta("Commission")

    if not commission_meta.has_field("deferred_commission_details"):
        frappe.throw(
            _("Commission child table field 'deferred_commission_details' is missing")
        )

    if commission_doc.deferred_commission_details:
        frappe.throw(
            _("Deferred schedule already exists for Commission record: {0}").format(
                commission_doc.name
            )
        )

    schedule_rows = _get_valid_deferred_schedule_rows(product_doc)

    source_date = getdate(commission_doc.creation)

    # First day of the next calendar month.
    first_due_date = add_to_date(
        source_date.replace(day=1),
        months=1,
        as_string=True,
    )

    total_commission = 0
    total_rate = 0

    for schedule in schedule_rows:
        year_no = schedule["year_no"]
        rate = schedule["rate"]

        gross_commission = (eligible_amount * rate) / 100
        tds = gross_commission * 0.02
        security_deposit = gross_commission * 0.10
        netpay = gross_commission - (tds + security_deposit)

        due_date = add_to_date(
            first_due_date,
            years=year_no - 1,
            as_string=True,
        )

        commission_doc.append(
            "deferred_commission_details",
            {
                "year_no": year_no,
                "commission_rate": rate,
                "eligible_amount": eligible_amount,
                "gross_commission": gross_commission,
                "due_date": due_date,
                "status": "Pending",
                "tds": tds,
                "security_deposit": security_deposit,
                "netpay": netpay,
                "remarks": schedule["remarks"],
            },
        )

        total_commission += gross_commission
        total_rate += rate

    return {
        "total_commission": total_commission,
        "total_rate": total_rate,
        "first_due_date": first_due_date,
        "schedule_count": len(schedule_rows),
    }


@frappe.whitelist()
def calculate_commission_amount(docname):
    """
    Calculate Commission.commission_amount based on the Product commission type.

    Supported Product commission types:
    1. Fixed Rate
    2. Age Based
    3. Eligible Amount Based

    For Eligible Amount Based products:
    - Consider only Commission records whose scheme_code points to a Product
      with commission_type = 'Eligible Amount Based'.
    - Slab selection is based on agent_total_eligible_collection (sum of
      eligible_amount for those filtered records for the same agent).
    - Commission is calculated on the document's own eligible_amount.
    """

    if not docname:
        frappe.throw(_("Commission document name is required"))

    commission_doc = frappe.get_doc("Commission", docname)

    if not commission_doc.scheme_code:
        frappe.throw(
            _("Scheme Code is required in Commission document")
        )

    if commission_doc.eligible_amount in (None, ""):
        frappe.throw(
            _("Eligible Amount is required in Commission document")
        )

    product_name = str(commission_doc.scheme_code).strip()

    product = frappe.db.get_value(
        "Product",
        product_name,
        [
            "commission_type",
            "commission_rate",
            "commission_rate_upto_one_year",
            "commission_rate_above_one_year",
            "slab_1_limit",
            "slab_1_rate",
            "slab_2_limit",
            "slab_2_rate",
            "slab_3_rate",
        ],
        as_dict=True,
    )

    if not product:
        frappe.throw(
            _("No Product found with Product Code: {0}").format(
                product_name
            )
        )

    if not product.commission_type:
        frappe.throw(
            _("Commission Type is not configured in Product: {0}").format(
                product_name
            )
        )

    commission_type = product.commission_type
    eligible_amount = flt(commission_doc.eligible_amount)

    if eligible_amount < 0:
        frappe.throw(
            _("Eligible Amount cannot be negative")
        )

    rate = None

    if commission_type == "Fixed Rate":
        if product.commission_rate in (None, ""):
            frappe.throw(
                _("Commission Rate is required for Product: {0}").format(
                    product_name
                )
            )

        rate = flt(product.commission_rate)

    elif commission_type == "Age Based":
        remarks = _safe_str(commission_doc.remarks).upper()

        if remarks == "YES":
            if product.commission_rate_upto_one_year in (None, ""):
                frappe.throw(
                    _(
                        "Commission Rate Upto One Year is required "
                        "for Product: {0}"
                    ).format(product_name)
                )

            rate = flt(product.commission_rate_upto_one_year)

        elif remarks == "NO":
            if product.commission_rate_above_one_year in (None, ""):
                frappe.throw(
                    _(
                        "Commission Rate Above One Year is required "
                        "for Product: {0}"
                    ).format(product_name)
                )

            rate = flt(product.commission_rate_above_one_year)

        else:
            frappe.throw(
                _(
                    "Remarks must be YES or NO for Age Based Product: {0}"
                ).format(product_name)
            )

    elif commission_type == "Eligible Amount Based":
        required_fields = {
            "Slab 1 Limit": product.slab_1_limit,
            "Slab 1 Rate": product.slab_1_rate,
            "Slab 2 Limit": product.slab_2_limit,
            "Slab 2 Rate": product.slab_2_rate,
            "Slab 3 Rate": product.slab_3_rate,
        }

        for field_label, field_value in required_fields.items():
            if field_value in (None, ""):
                frappe.throw(
                    _("{0} is required for Product: {1}").format(
                        field_label,
                        product_name,
                    )
                )

        slab_1_limit = flt(product.slab_1_limit)
        slab_2_limit = flt(product.slab_2_limit)

        if slab_1_limit < 0:
            frappe.throw(
                _("Slab 1 Limit cannot be negative")
            )

        if slab_2_limit <= slab_1_limit:
            frappe.throw(
                _(
                    "Slab 2 Limit must be greater than "
                    "Slab 1 Limit for Product: {0}"
                ).format(product_name)
            )

        if not commission_doc.agent_code:
            frappe.throw(
                _("Agent Code is required for Eligible Amount Based calculation")
            )

        agent_code = str(commission_doc.agent_code).strip()

        eligible_products = frappe.get_all(
            "Product",
            filters={"commission_type": "Eligible Amount Based"},
            pluck="name",
        )

        if not eligible_products:
            frappe.throw(
                _(
                    "No Product found with commission_type = 'Eligible Amount Based'"
                )
            )

        # Build safe IN clause for eligible_products
        if len(eligible_products) == 1:
            in_clause = "%s"
            in_params = tuple(eligible_products)
        else:
            in_clause = ", ".join(["%s"] * len(eligible_products))
            in_params = tuple(eligible_products)

        result = frappe.db.sql(
            """
            SELECT SUM(c.eligible_amount) AS total
            FROM `tabCommission` c
            WHERE c.agent_code = %s
            AND c.docstatus < 2
            AND c.scheme_code IN ({0})
            """.format(in_clause),
            tuple([agent_code] + list(in_params)),
            as_dict=True,
        )

        agent_total = flt(result[0].total) if result and result[0].total else 0

        if agent_total <= 0:
            frappe.throw(
                _(
                    "Total eligible amount for Agent {0} (Eligible Amount Based products) "
                    "is zero or invalid"
                ).format(agent_code)
            )

        frappe.db.sql(
            """
            UPDATE `tabCommission` c
            SET c.agent_total_eligible_collection = %s
            WHERE c.agent_code = %s
            AND c.docstatus < 2
            AND c.scheme_code IN ({0})
            """.format(in_clause),
            tuple([agent_total, agent_code] + list(in_params)),
        )

        commission_doc.agent_total_eligible_collection = agent_total

        if agent_total <= slab_1_limit:
            rate = flt(product.slab_1_rate)
        elif agent_total <= slab_2_limit:
            rate = flt(product.slab_2_rate)
        else:
            rate = flt(product.slab_3_rate)

    # else:
    #     frappe.throw(
    #         _(
    #             "Invalid Commission Type '{0}' in Product: {1}. "
    #             "Allowed values are Fixed Rate, Age Based, "
    #             "and Eligible Amount Based."
    #         ).format(
    #             commission_type,
    #             product_name,
    #         )
    #     )

        # ==========================================================
    # PRODUCT TYPE 4: DEFERRED
    # ==========================================================
    elif commission_type == "Deferred":
        product_doc = _get_deferred_product(product_name)

        deferred_result = _create_deferred_commission_schedule(
            commission_doc=commission_doc,
            product_doc=product_doc,
            eligible_amount=eligible_amount,
        )

        # Parent-level fields store the total across every scheduled year.
        commission_amount = deferred_result["total_commission"]
        tds = commission_amount * 0.02
        security_deposit = commission_amount * 0.10
        netpay = commission_amount - (tds + security_deposit)

        commission_doc.commission_amount = commission_amount
        commission_doc.tds = tds
        commission_doc.security_deposit = security_deposit
        commission_doc.netpay = netpay

        if frappe.get_meta("Commission").has_field("applied_commission_rate"):
            commission_doc.applied_commission_rate = deferred_result["total_rate"]

        if frappe.get_meta("Commission").has_field("commission_type_applied"):
            commission_doc.commission_type_applied = commission_type

        commission_doc.save(ignore_permissions=True)
        frappe.db.commit()

        return {
            "status": "success",
            "docname": commission_doc.name,
            "product_code": product_name,
            "commission_type": commission_type,
            "eligible_amount": eligible_amount,
            "applied_rate": deferred_result["total_rate"],
            "commission_amount": commission_amount,
            "tds": tds,
            "security_deposit": security_deposit,
            "netpay": netpay,
            "deferred_schedule_count": deferred_result["schedule_count"],
            "first_deferred_due_date": deferred_result["first_due_date"],
            "message": _("Deferred commission schedule created successfully"),
        }

    else:
        frappe.throw(
            _(
                "Invalid Commission Type '{0}' in Product: {1}. "
                "Allowed values are Fixed Rate, Age Based, "
                "Eligible Amount Based, and Deferred."
            ).format(
                commission_type,
                product_name,
            )
        )

    if rate is None:
        frappe.throw(
            _("Unable to determine commission rate for Product: {0}").format(
                product_name
            )
        )

    if rate < 0:
        frappe.throw(
            _("Commission rate cannot be negative")
        )

    commission_amount = (eligible_amount * rate) / 100
    commission_doc.commission_amount = commission_amount

    tds = commission_amount * 0.02           # 2% TDS
    security_deposit = commission_amount * 0.10  # 10% security deposit
    netpay = commission_amount - (tds + security_deposit)

    commission_doc.tds = tds
    commission_doc.security_deposit = security_deposit
    commission_doc.netpay = netpay

    if frappe.get_meta("Commission").has_field("applied_commission_rate"):
        commission_doc.applied_commission_rate = rate

    if frappe.get_meta("Commission").has_field("commission_type_applied"):
        commission_doc.commission_type_applied = commission_type

    commission_doc.save(ignore_permissions=True)
    frappe.db.commit()

    return {
        "status": "success",
        "docname": commission_doc.name,
        "product_code": product_name,
        "commission_type": commission_type,
        "remarks": commission_doc.remarks,
        "eligible_amount": eligible_amount,
        "agent_total_eligible_collection": (
            flt(commission_doc.agent_total_eligible_collection)
            if commission_type == "Eligible Amount Based"
            else None
        ),
        "applied_rate": rate,
        "commission_amount": commission_amount,
        "tds": tds,
        "security_deposit": security_deposit,
        "netpay": netpay,
    }


# @frappe.whitelist()
# def calculate_commission_amounts(docname):
#     """
#     Calculate Commission.commission_amount based on the Product commission type.

#     Supported Product commission types:
#     1. Fixed Rate
#     2. Age Based
#     3. Eligible Amount Based

#     For Eligible Amount Based products:
#     - Consider only Commission records whose scheme_code points to a Product
#       with commission_type = 'Eligible Amount Based'.
#     - Slab selection is based on agent_total_eligible_collection (sum of
#       eligible_amount for those filtered records for the same agent).
#     - Commission is calculated on the document's own eligible_amount.
#     """

#     if not docname:
#         frappe.throw(_("Commission document name is required"))

#     commission_doc = frappe.get_doc("Commission", docname)

#     if not commission_doc.scheme_code:
#         frappe.throw(
#             _("Scheme Code is required in Commission document")
#         )

#     if commission_doc.eligible_amount in (None, ""):
#         frappe.throw(
#             _("Eligible Amount is required in Commission document")
#         )

#     product_name = str(commission_doc.scheme_code).strip()

#     product = frappe.db.get_value(
#         "Product",
#         product_name,
#         [
#             "commission_type",
#             "commission_rate",
#             "commission_rate_upto_one_year",
#             "commission_rate_above_one_year",
#             "slab_1_limit",
#             "slab_1_rate",
#             "slab_2_limit",
#             "slab_2_rate",
#             "slab_3_rate",
#         ],
#         as_dict=True,
#     )

#     if not product:
#         frappe.throw(
#             _("No Product found with Product Code: {0}").format(
#                 product_name
#             )
#         )

#     if not product.commission_type:
#         frappe.throw(
#             _("Commission Type is not configured in Product: {0}").format(
#                 product_name
#             )
#         )

#     commission_type = product.commission_type
#     eligible_amount = flt(commission_doc.eligible_amount)

#     if eligible_amount < 0:
#         frappe.throw(
#             _("Eligible Amount cannot be negative")
#         )

#     rate = None

#     # ==========================================================
#     # PRODUCT TYPE 1: FIXED RATE
#     # ==========================================================
#     if commission_type == "Fixed Rate":
#         if product.commission_rate in (None, ""):
#             frappe.throw(
#                 _("Commission Rate is required for Product: {0}").format(
#                     product_name
#                 )
#             )

#         rate = flt(product.commission_rate)

#     elif commission_type == "Age Based":
#         remarks = _safe_str(commission_doc.remarks).upper()

#         if remarks == "YES":
#             if product.commission_rate_upto_one_year in (None, ""):
#                 frappe.throw(
#                     _(
#                         "Commission Rate Upto One Year is required "
#                         "for Product: {0}"
#                     ).format(product_name)
#                 )

#             rate = flt(product.commission_rate_upto_one_year)

#         elif remarks == "NO":
#             if product.commission_rate_above_one_year in (None, ""):
#                 frappe.throw(
#                     _(
#                         "Commission Rate Above One Year is required "
#                         "for Product: {0}"
#                     ).format(product_name)
#                 )

#             rate = flt(product.commission_rate_above_one_year)

#         else:
#             frappe.throw(
#                 _(
#                     "Remarks must be YES or NO for Age Based Product: {0}"
#                 ).format(product_name)
#             )

#     elif commission_type == "Eligible Amount Based":
#         required_fields = {
#             "Slab 1 Limit": product.slab_1_limit,
#             "Slab 1 Rate": product.slab_1_rate,
#             "Slab 2 Limit": product.slab_2_limit,
#             "Slab 2 Rate": product.slab_2_rate,
#             "Slab 3 Rate": product.slab_3_rate,
#         }

#         for field_label, field_value in required_fields.items():
#             if field_value in (None, ""):
#                 frappe.throw(
#                     _("{0} is required for Product: {1}").format(
#                         field_label,
#                         product_name,
#                     )
#                 )

#         slab_1_limit = flt(product.slab_1_limit)
#         slab_2_limit = flt(product.slab_2_limit)

#         if slab_1_limit < 0:
#             frappe.throw(
#                 _("Slab 1 Limit cannot be negative")
#             )

#         if slab_2_limit <= slab_1_limit:
#             frappe.throw(
#                 _(
#                     "Slab 2 Limit must be greater than "
#                     "Slab 1 Limit for Product: {0}"
#                 ).format(product_name)
#             )

#         if not commission_doc.agent_code:
#             frappe.throw(
#                 _("Agent Code is required for Eligible Amount Based calculation")
#             )

#         agent_code = str(commission_doc.agent_code).strip()

#         # Get all Product IDs where commission_type = 'Eligible Amount Based'
#         eligible_products = frappe.get_all(
#             "Product",
#             filters={"commission_type": "Eligible Amount Based"},
#             pluck="name",
#         )

#         if not eligible_products:
#             frappe.throw(
#                 _(
#                     "No Product found with commission_type = 'Eligible Amount Based'"
#                 )
#             )

#         # Build safe IN clause for eligible_products
#         if len(eligible_products) == 1:
#             in_clause = "%s"
#             in_params = tuple(eligible_products)
#         else:
#             in_clause = ", ".join(["%s"] * len(eligible_products))
#             in_params = tuple(eligible_products)

#         result = frappe.db.sql(
#             """
#             SELECT SUM(c.eligible_amount) AS total
#             FROM `tabCommission` c
#             WHERE c.agent_code = %s
#             AND c.docstatus < 2
#             AND c.scheme_code IN ({0})
#             """.format(in_clause),
#             tuple([agent_code] + list(in_params)),
#             as_dict=True,
#         )

#         agent_total = flt(result[0].total) if result and result[0].total else 0

#         if agent_total <= 0:
#             frappe.throw(
#                 _(
#                     "Total eligible amount for Agent {0} (Eligible Amount Based products) "
#                     "is zero or invalid"
#                 ).format(agent_code)
#             )

#         # Update all Commission records for this agent (for Eligible Amount Based products)
#         # with the aggregated total.
#         frappe.db.sql(
#             """
#             UPDATE `tabCommission` c
#             SET c.agent_total_eligible_collection = %s
#             WHERE c.agent_code = %s
#             AND c.docstatus < 2
#             AND c.scheme_code IN ({0})
#             """.format(in_clause),
#             tuple([agent_total, agent_code] + list(in_params)),
#         )

#         # Refresh the current document's value
#         commission_doc.agent_total_eligible_collection = agent_total

#         if agent_total <= slab_1_limit:
#             rate = flt(product.slab_1_rate)

#         elif agent_total <= slab_2_limit:
#             rate = flt(product.slab_2_rate)

#         else:
#             rate = flt(product.slab_3_rate)

#     # else:
#     #     frappe.throw(
#     #         _(
#     #             "Invalid Commission Type '{0}' in Product: {1}. "
#     #             "Allowed values are Fixed Rate, Age Based, "
#     #             "and Eligible Amount Based."
#     #         ).format(
#     #             commission_type,
#     #             product_name,
#     #         )
#     #     )

#     # ==========================================================
#     # PRODUCT TYPE 4: DEFERRED
#     # ==========================================================
#     elif commission_type == "Deferred":
#         product_doc = _get_product_with_deferred_schedule(product_name)

#         deferred_result = _generate_deferred_commission_schedule(
#             commission_doc=commission_doc,
#             product_doc=product_doc,
#             eligible_amount=eligible_amount,
#         )

#         # Parent Commission amount stores total deferred commission
#         # across all configured years.
#         commission_amount = deferred_result["total_deferred_amount"]

#         # Parent tds/security/netpay are total values across all deferred years.
#         tds = commission_amount * 0.02
#         security_deposit = commission_amount * 0.10
#         netpay = commission_amount - (tds + security_deposit)

#         commission_doc.commission_amount = commission_amount
#         commission_doc.tds = tds
#         commission_doc.security_deposit = security_deposit
#         commission_doc.netpay = netpay

#         if frappe.get_meta("Commission").has_field("applied_commission_rate"):
#             commission_doc.applied_commission_rate = deferred_result["total_deferred_rate"]

#         if frappe.get_meta("Commission").has_field("commission_type_applied"):
#             commission_doc.commission_type_applied = commission_type

#         commission_doc.save(ignore_permissions=True)
#         frappe.db.commit()

#         return {
#             "status": "success",
#             "docname": commission_doc.name,
#             "product_code": product_name,
#             "commission_type": commission_type,
#             "eligible_amount": eligible_amount,
#             "applied_rate": deferred_result["total_deferred_rate"],
#             "commission_amount": commission_amount,
#             "tds": tds,
#             "security_deposit": security_deposit,
#             "netpay": netpay,
#             "deferred_schedule_count": deferred_result["schedule_count"],
#             "first_deferred_due_date": deferred_result["first_due_date"],
#             "message": _("Deferred commission schedule generated successfully"),
#         }

#     else:
#         frappe.throw(
#             _(
#                 "Invalid Commission Type '{0}' in Product: {1}. "
#                 "Allowed values are Fixed Rate, Age Based, "
#                 "Eligible Amount Based, and Deferred."
#             ).format(
#                 commission_type,
#                 product_name,
#             )
#         )

#     if rate is None:
#         frappe.throw(
#             _("Unable to determine commission rate for Product: {0}").format(
#                 product_name
#             )
#         )

#     if rate < 0:
#         frappe.throw(
#             _("Commission rate cannot be negative")
#         )

#     # Apply the selected rate to the COMPLETE eligible_amount of this document.
#     commission_amount = (eligible_amount * rate) / 100

#     commission_doc.commission_amount = commission_amount

#     # Optional audit fields.
#     if frappe.get_meta("Commission").has_field("applied_commission_rate"):
#         commission_doc.applied_commission_rate = rate

#     if frappe.get_meta("Commission").has_field("commission_type_applied"):
#         commission_doc.commission_type_applied = commission_type

#     commission_doc.save(ignore_permissions=True)
#     frappe.db.commit()

#     return {
#         "status": "success",
#         "docname": commission_doc.name,
#         "product_code": product_name,
#         "commission_type": commission_type,
#         "remarks": commission_doc.remarks,
#         "eligible_amount": eligible_amount,
#         "agent_total_eligible_collection": (
#             flt(commission_doc.agent_total_eligible_collection)
#             if commission_type == "Eligible Amount Based"
#             else None
#         ),
#         "applied_rate": rate,
#         "commission_amount": commission_amount,
#     }


def _get_product_with_deferred_schedule(product_name):
    """
    Load complete Product document because deferred schedule is a child table.
    """
    product_doc = frappe.get_doc("Product", product_name)

    if product_doc.commission_type != "Deferred":
        frappe.throw(
            _("Product {0} is not configured as Deferred").format(
                product_name
            )
        )

    if not product_doc.deferred_commission_schedule:
        frappe.throw(
            _("Deferred Commission Schedule is missing in Product: {0}").format(
                product_name
            )
        )

    return product_doc


def _validate_deferred_schedule(product_doc):
    """
    Validate enabled Product deferred commission schedule rows.
    Returns schedule rows sorted by year_no.
    """
    enabled_rows = []
    used_years = set()

    for row in product_doc.deferred_commission_schedule:
        if not row.enabled:
            continue

        year_no = cint(row.year_no)
        commission_rate = flt(row.commission_rate)

        if year_no <= 0:
            frappe.throw(
                _("Deferred Year No must be greater than zero in Product: {0}").format(
                    product_doc.name
                )
            )

        if year_no in used_years:
            frappe.throw(
                _("Duplicate Deferred Year No {0} in Product: {1}").format(
                    year_no,
                    product_doc.name
                )
            )

        if commission_rate < 0:
            frappe.throw(
                _("Deferred Commission Rate cannot be negative for Year {0}").format(
                    year_no
                )
            )

        used_years.add(year_no)
        enabled_rows.append({
            "year_no": year_no,
            "commission_rate": commission_rate,
            "remarks": _safe_str(row.remarks),
        })

    if not enabled_rows:
        frappe.throw(
            _("No enabled Deferred Commission Schedule rows found in Product: {0}").format(
                product_doc.name
            )
        )

    return sorted(enabled_rows, key=lambda row: row["year_no"])


def _generate_deferred_commission_schedule(commission_doc, product_doc, eligible_amount):
    """
    Generate the full annual deferred payout schedule in the Commission child table.

    Due-date rule:
    - Year 1: first day of next calendar month after Commission record creation.
    - Year 2: one year after Year 1 due date.
    - Year N: Year 1 due date plus N-1 years.

    Example:
    Commission created on 2026-08-19:
    - Year 1 due: 2026-09-01
    - Year 2 due: 2027-09-01
    """
    commission_meta = frappe.get_meta("Commission")

    if not commission_meta.has_field("deferred_commission_details"):
        frappe.throw(
            _("Commission field 'deferred_commission_details' does not exist")
        )

    if commission_doc.deferred_commission_details:
        frappe.throw(
            _("Deferred commission schedule already exists for Commission: {0}").format(
                commission_doc.name
            )
        )

    schedule_rows = _validate_deferred_schedule(product_doc)

    # Commission document creation date controls the deferred due cycle.
    source_date = getdate(commission_doc.creation)

    # First day of next month.
    first_due_date = add_to_date(
        source_date.replace(day=1),
        months=1,
        as_string=True,
    )

    total_deferred_amount = 0
    total_deferred_rate = 0

    for schedule in schedule_rows:
        year_no = schedule["year_no"]
        rate = schedule["commission_rate"]

        gross_commission = (eligible_amount * rate) / 100
        tds = gross_commission * 0.02
        security_deposit = gross_commission * 0.10
        netpay = gross_commission - (tds + security_deposit)

        due_date = add_to_date(
            first_due_date,
            years=year_no - 1,
            as_string=True,
        )

        commission_doc.append(
            "deferred_commission_details",
            {
                "year_no": year_no,
                "commission_rate": rate,
                "eligible_amount": eligible_amount,
                "gross_commission": gross_commission,
                "due_date": due_date,
                "status": "Pending",
                "tds": tds,
                "security_deposit": security_deposit,
                "netpay": netpay,
                "remarks": schedule["remarks"],
            },
        )

        total_deferred_amount += gross_commission
        total_deferred_rate += rate

    return {
        "total_deferred_amount": total_deferred_amount,
        "total_deferred_rate": total_deferred_rate,
        "first_due_date": first_due_date,
        "schedule_count": len(schedule_rows),
    }


@frappe.whitelist()
def calculate_commission_for_all():
    """
    Calculate commission on ALL Commission documents.
    Calls calculate_commission_amount(docname) for each document.
    """
    frappe.only_for(("System Manager",))

    # Get all Commission names
    commission_names = frappe.get_all(
        "Commission",
        filters={"docstatus": ("<", 2)},  # ignore cancelled if any
        pluck="name",
    )

    if not commission_names:
        return {
            "status": "completed",
            "total_processed": 0,
            "success_count": 0,
            "error_count": 0,
            "errors": [],
        }

    success_count = 0
    error_count = 0
    errors = []

    for docname in commission_names:
        try:
            # Call existing method
            calculate_commission_amount(docname)
            success_count += 1
        except Exception:
            error_count += 1
            errors.append(
                f"{docname}: {frappe.get_traceback()}"
            )
            # Optionally log
            frappe.log_error(
                frappe.get_traceback(),
                f"Commission Calculation Error - {docname}",
            )

    return {
        "status": "completed",
        "total_processed": len(commission_names),
        "success_count": success_count,
        "error_count": error_count,
        "errors": errors,
    }


@frappe.whitelist()
def mark_due_deferred_commissions(payment_date=None):
    """
    Mark deferred schedule rows as Due when their due_date has arrived.
    Actual payment remains a manual action.
    """
    frappe.only_for(("System Manager",))

    payment_date = getdate(payment_date) if payment_date else getdate()

    result = frappe.db.sql(
        """
        UPDATE `tabDeferred Commission Detail`
        SET status = 'Due'
        WHERE parenttype = 'Commission'
        AND parentfield = 'deferred_commission_details'
        AND status = 'Pending'
        AND due_date <= %s
        """,
        payment_date,
    )

    frappe.db.commit()

    return {
        "status": "success",
        "payment_date": payment_date,
        "message": _("Deferred commission rows marked as Due"),
    }


@frappe.whitelist()
def get_due_deferred_commissions(payment_date=None):
    """
    Return Deferred Commission Detail rows that are due and not yet paid.
    """
    frappe.only_for(("System Manager",))

    payment_date = getdate(payment_date) if payment_date else getdate()

    return frappe.db.sql(
        """
        SELECT
            c.name AS commission_name,
            c.agent_code,
            c.agent_name,
            c.scheme_code,
            c.customer_account_number,
            c.customer_account_name,
            d.name AS deferred_detail_name,
            d.year_no,
            d.commission_rate,
            d.eligible_amount,
            d.gross_commission,
            d.tds,
            d.security_deposit,
            d.netpay,
            d.due_date,
            d.status
        FROM `tabDeferred Commission Detail` d
        INNER JOIN `tabCommission` c
            ON c.name = d.parent
        WHERE d.parenttype = 'Commission'
        AND d.parentfield = 'deferred_commission_details'
        AND d.status IN ('Pending', 'Due')
        AND d.due_date <= %s
        AND c.docstatus < 2
        ORDER BY d.due_date, c.agent_code, c.name
        """,
        payment_date,
        as_dict=True,
    )


@frappe.whitelist()
def mark_deferred_commission_paid(
    commission_name,
    deferred_detail_name,
    payment_reference=None,
    paid_on=None,
):
    """
    Mark exactly one deferred annual installment as paid.
    Stops duplicate payment of the same year.
    """
    frappe.only_for(("System Manager",))

    paid_on = getdate(paid_on) if paid_on else getdate()

    commission_doc = frappe.get_doc("Commission", commission_name)

    deferred_row = next(
        (
            row for row in commission_doc.deferred_commission_details
            if row.name == deferred_detail_name
        ),
        None,
    )

    if not deferred_row:
        frappe.throw(_("Deferred Commission Detail row not found"))

    if deferred_row.status == "Paid":
        frappe.throw(
            _("Deferred commission for Year {0} is already paid").format(
                deferred_row.year_no
            )
        )

    if getdate(deferred_row.due_date) > paid_on:
        frappe.throw(
            _("This deferred commission is not due until {0}").format(
                deferred_row.due_date
            )
        )

    deferred_row.status = "Paid"
    deferred_row.paid_on = paid_on
    deferred_row.payment_reference = payment_reference

    commission_doc.save(ignore_permissions=True)
    frappe.db.commit()

    return {
        "status": "success",
        "commission_name": commission_doc.name,
        "year_no": deferred_row.year_no,
        "gross_commission": deferred_row.gross_commission,
        "tds": deferred_row.tds,
        "security_deposit": deferred_row.security_deposit,
        "netpay": deferred_row.netpay,
        "paid_on": paid_on,
        "payment_reference": payment_reference,
        "message": _("Deferred commission installment marked as paid"),
    }
