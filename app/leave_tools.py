from datetime import date, datetime
from app.db import get_connection

LEAVE_TYPES = ["Medical", "Personal", "Family Emergency", "Academic Event"]
MAX_LEAVE_DAYS = 7  # demo rule


def parse_date(text):
    """'2026-10-25' format ko date me badalta hai. Galat ho to None."""
    try:
        return datetime.strptime(text, "%Y-%m-%d").date()
    except (ValueError, TypeError):
        return None


def validate_leave(student_id, leave_type, start_date, end_date, reason):
    """
    Leave ke saare rules check karta hai (save nahi karta).
    Return: {"valid": True/False, "message": "..."}
    """
    if leave_type not in LEAVE_TYPES:
        return {"valid": False, "message": f"Leave type galat hai. Options: {', '.join(LEAVE_TYPES)}"}

    start = parse_date(start_date)
    end = parse_date(end_date)
    if start is None or end is None:
        return {"valid": False, "message": "Date format galat hai. Format: YYYY-MM-DD (jaise 2026-10-25)."}

    if start < date.today():
        return {"valid": False, "message": "Start date past me nahi ho sakti."}
    if end < start:
        return {"valid": False, "message": "End date start date se pehle nahi ho sakti."}

    days = (end - start).days + 1
    if days > MAX_LEAVE_DAYS:
        return {"valid": False, "message": f"Ek application me max {MAX_LEAVE_DAYS} din ki leave mil sakti hai. Tumne {days} din maange."}

    reason = (reason or "").strip()
    if len(reason) < 10:
        return {"valid": False, "message": "Reason bahut chhota hai (kam se kam 10 characters)."}

    # Overlap check: sirf Pending leaves ke saath
    conn = get_connection()
    overlap = conn.execute(
        """SELECT id, start_date, end_date FROM leave_applications
           WHERE student_id = ? AND status = 'Pending'
             AND start_date <= ? AND end_date >= ?""",
        (student_id, end_date, start_date),
    ).fetchone()
    conn.close()

    if overlap:
        return {
            "valid": False,
            "message": f"In dates par pehle se Pending leave hai (ID {overlap['id']}: {overlap['start_date']} se {overlap['end_date']}).",
        }

    return {"valid": True, "message": f"Sab rules pass. Total {days} din."}


def create_leave_application(student_id, leave_type, start_date, end_date, reason):
    """Validate karke leave save karta hai."""
    check = validate_leave(student_id, leave_type, start_date, end_date, reason)
    if not check["valid"]:
        return {"success": False, "message": check["message"], "leave_id": None}

    conn = get_connection()
    student = conn.execute("SELECT id FROM students WHERE id = ?", (student_id,)).fetchone()
    if not student:
        conn.close()
        return {"success": False, "message": "Student nahi mila.", "leave_id": None}

    cur = conn.execute(
        """INSERT INTO leave_applications (student_id, leave_type, start_date, end_date, reason)
           VALUES (?, ?, ?, ?, ?)""",
        (student_id, leave_type, start_date, end_date, reason.strip()),
    )
    conn.commit()
    new_id = cur.lastrowid
    conn.close()
    return {"success": True, "message": f"Leave application save ho gayi. ID: {new_id}", "leave_id": new_id}


def get_my_leaves(student_id):
    """Sirf us student ki leaves."""
    conn = get_connection()
    rows = conn.execute(
        "SELECT * FROM leave_applications WHERE student_id = ? ORDER BY id DESC",
        (student_id,),
    ).fetchall()
    conn.close()
    return [dict(r) for r in rows]


def get_leave_status(student_id, leave_id):
    """Status sirf owner ko milega."""
    conn = get_connection()
    row = conn.execute(
        "SELECT * FROM leave_applications WHERE id = ? AND student_id = ?",
        (leave_id, student_id),
    ).fetchone()
    conn.close()
    return dict(row) if row else None


def cancel_leave(student_id, leave_id):
    """Pending leave cancel karta hai (sirf owner)."""
    conn = get_connection()
    row = conn.execute(
        "SELECT status FROM leave_applications WHERE id = ? AND student_id = ?",
        (leave_id, student_id),
    ).fetchone()

    if not row:
        conn.close()
        return {"success": False, "message": "Leave application nahi mili."}
    if row["status"] != "Pending":
        conn.close()
        return {"success": False, "message": f"Sirf Pending leave cancel ho sakti hai. Abhi status: {row['status']}"}

    conn.execute(
        "UPDATE leave_applications SET status = 'Cancelled' WHERE id = ? AND student_id = ?",
        (leave_id, student_id),
    )
    conn.commit()
    conn.close()
    return {"success": True, "message": f"Leave {leave_id} cancel ho gayi."}