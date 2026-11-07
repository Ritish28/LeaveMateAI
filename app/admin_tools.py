from app.db import get_connection

TABLES = {"RMS": "rms_requests", "Leave": "leave_applications"}
NEW_STATUSES = ["Approved", "Rejected"]


def list_all(kind):
    """Demo admin: saare students ki requests (naam ke saath)."""
    table = TABLES[kind]
    conn = get_connection()
    rows = conn.execute(
        f"""SELECT t.*, s.name AS student_name, s.reg_no
            FROM {table} t JOIN students s ON s.id = t.student_id
            ORDER BY t.id DESC"""
    ).fetchall()
    conn.close()
    return [dict(r) for r in rows]


def set_status(kind, item_id, new_status):
    """Sirf Pending request ko Approved/Rejected karta hai."""
    if kind not in TABLES:
        return {"success": False, "message": "Invalid type."}
    if new_status not in NEW_STATUSES:
        return {"success": False, "message": "Invalid status."}

    table = TABLES[kind]
    conn = get_connection()
    row = conn.execute(f"SELECT status FROM {table} WHERE id = ?", (item_id,)).fetchone()
    if not row:
        conn.close()
        return {"success": False, "message": "Request nahi mili."}
    if row["status"] != "Pending":
        conn.close()
        return {"success": False, "message": f"Sirf Pending ka status badal sakta hai. Abhi: {row['status']}"}

    conn.execute(f"UPDATE {table} SET status = ? WHERE id = ?", (new_status, item_id))
    conn.commit()
    conn.close()
    return {"success": True, "message": f"{kind} #{item_id} ab {new_status} hai."}