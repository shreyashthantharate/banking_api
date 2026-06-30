import frappe
from frappe import _


@frappe.whitelist()
def sync_employees_to_finacle():
    """
    Cron Job function to sync new Employee records to Finacle via direct SQL INSERT.
    Only syncs records where custom_finacle_synced = 0.
    """
    try:
        import psycopg2
    except ImportError:
        msg = "psycopg2 is not installed. Cannot sync to Finacle."
        frappe.logger().error(msg)
        frappe.log_error(msg, "Finacle Sync Import Error")
        return

    employees = frappe.get_all(
        "Employee",
        filters={"custom_finacle_synced": 0},
        fields=[
            "name",
            "employee_name",
            "first_name",
            "last_name",
            "user_id",
            "sol_id",
        ],
    )

    if not employees:
        frappe.logger().info("Finacle Sync: No new employees found to sync.")
        return

    settings = frappe.get_single("Finacle Settings")
    host = (settings.host or "").strip()
    port = settings.port
    db_name = (settings.database_name or "").strip()
    user = (settings.user or "").strip()
    password = settings.get_password("password")

    if not all([host, port, db_name, user, password]):
        msg = "Finacle Settings are incomplete."
        frappe.logger().error(msg)
        frappe.log_error(msg, "Finacle Sync Config Error")
        return

    connection = None
    cursor = None

    try:
        connection = psycopg2.connect(
            host=host,
            port=port,
            user=user,
            password=password,
            dbname=db_name,
        )
        cursor = connection.cursor()

        for emp in employees:
            finacle_emp_id = f"SAH0{emp.name}"
            emp_name = (emp.employee_name or "")[:50]
            emp_short_name = (emp.first_name or emp_name)[:15]
            sol_id = (emp.sol_id or "").strip()

            if not sol_id:
                error_data = {
                    "status": "failed",
                    "error": "sol_id is missing in Employee record",
                    "employee": emp.name,
                    "finacle_employee_id": finacle_emp_id,
                }

                log_sync_attempt(
                    emp.name,
                    finacle_emp_id,
                    {},
                    error_data,
                    "Failed",
                )
                continue

            insert_query = """
                INSERT INTO tbaadm."get"
                (
                    emp_id, entity_cre_flg, del_flg, emp_intls, sol_id, emp_name, emp_short_name,
                    emp_sign_power_num, emp_sign_power_amt, emp_desig, emp_stat, tot_mod_times,
                    lchg_user_id, lchg_time, rcre_user_id, rcre_time, is_head_teller, ts_cnt,
                    alt1_emp_name, alt1_emp_short_name
                )
                VALUES
                (
                    %s, 'Y', 'N', NULL, %s, %s, %s,
                    0, 0.0000, NULL, NULL, 0,
                    'SYSTEM', NOW(), 'SYSTEM', NOW(), 'N', 1,
                    NULL, NULL
                )
            """

            query_values = (
                finacle_emp_id,
                sol_id,
                emp_name,
                emp_short_name,
            )

            try:
                cursor.execute(insert_query, query_values)
                connection.commit()

                frappe.db.set_value("Employee", emp.name,
                                    "custom_finacle_synced", 1)

                log_sync_attempt(
                    emp.name,
                    finacle_emp_id,
                    query_values,
                    {
                        "status": "success",
                        "message": "Record inserted to Finacle DB"
                    },
                    "Success",
                )

            except Exception as e:
                connection.rollback()
                error_trace = frappe.get_traceback()
                error_data = {
                    "status": "failed",
                    "error": str(e),
                    "traceback": error_trace,
                    "employee": emp.name,
                    "finacle_employee_id": finacle_emp_id,
                    "sol_id": sol_id,
                }

                frappe.log_error(
                    error_trace,
                    f"Finacle Employee Sync Failed: {emp.name}"
                )

                log_sync_attempt(
                    emp.name,
                    finacle_emp_id,
                    query_values,
                    error_data,
                    "Failed",
                )

    except Exception:
        error_trace = frappe.get_traceback()
        frappe.logger().error(error_trace)
        frappe.log_error(error_trace, "Finacle DB Connection / Sync Failure")

    finally:
        if cursor:
            cursor.close()
        if connection:
            connection.close()


def log_sync_attempt(employee, finacle_emp_id, request_data, response_data, status):
    """
    Creates an entry in 'Finacle EDR Sync Log' tracking table
    """
    doc = frappe.get_doc({
        "doctype": "Finacle EDR Sync Log",
        "employee": employee,
        "finacle_employee_id": finacle_emp_id,
        "request_data": frappe.as_json(request_data),
        "response_data": frappe.as_json(response_data),
        "status": status,
        "sync_time": frappe.utils.now()
    })
    doc.insert(ignore_permissions=True)
    frappe.db.commit()
