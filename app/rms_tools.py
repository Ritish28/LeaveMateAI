from app.db import get_connection

# Allowed categories (RMS agent baad me inhi me se choose karega)
CATEGORIES = [
    "Attendance Issue",
    "Academic Issue",
    "Technical Problem",
    "Administrative Request",
]


def get_student_by_reg_no(reg_no):
    """Student ki details nikalta hai. Nahi mila to None."""
    conn = get_connection()
    row = conn.execute(
        "SELECT * FROM students WHERE reg_no = ?", (reg_no,)
    ).fetchone()
    conn.close()
    return dict(row) if row else None


def create_rms_request(student_id, category, subject, description):
    """
    RMS request save karta hai.
    Return: {"success": True/False, "message": "...", "request_id": number ya None}
    """
    # 1. Validation
    if category not in CATEGORIES:
        return {"success": False, "message": "Invalid category.", "request_id": None}

    subject = (subject or "").strip()
    description = (description or "").strip()

    if len(subject) < 5:
        return {"success": False, "message": "Subject bahut chhota hai (kam se kam 5 characters).", "request_id": None}
    if len(description) < 10:
        return {"success": False, "message": "Description bahut chhota hai (kam se kam 10 characters).", "request_id": None}

    conn = get_connection()

    # 2. Student exist karta hai?
    student = conn.execute(
        "SELECT id FROM students WHERE id = ?", (student_id,)
    ).fetchone()
    if not student:
        conn.close()
        return {"success": False, "message": "Student nahi mila.", "request_id": None}

    # 3. Duplicate check: same student, same category, same subject, abhi Pending
    duplicate = conn.execute(
        """SELECT id FROM rms_requests
           WHERE student_id = ? AND category = ? AND subject = ? AND status = 'Pending'""",
        (student_id, category, subject),
    ).fetchone()
    if duplicate:
        conn.close()
        return {
            "success": False,
            "message": f"Ye request pehle se Pending hai (ID: {duplicate['id']}).",
            "request_id": duplicate["id"],
        }

    # 4. Save
    cur = conn.execute(
        "INSERT INTO rms_requests (student_id, category, subject, description) VALUES (?, ?, ?, ?)",
        (student_id, category, subject, description),
    )
    conn.commit()
    new_id = cur.lastrowid
    conn.close()

    return {"success": True, "message": f"Request save ho gayi. ID: {new_id}", "request_id": new_id}


def get_my_requests(student_id):
    """Sirf us student ki requests (ownership safe)."""
    conn = get_connection()
    rows = conn.execute(
        "SELECT * FROM rms_requests WHERE student_id = ? ORDER BY id DESC",
        (student_id,),
    ).fetchall()
    conn.close()
    return [dict(r) for r in rows]


def get_request_status(student_id, request_id):
    """Status batata hai, lekin sirf agar request us student ki ho."""
    conn = get_connection()
    row = conn.execute(
        "SELECT * FROM rms_requests WHERE id = ? AND student_id = ?",
        (request_id, student_id),
    ).fetchone()
    conn.close()
    return dict(row) if row else None


def cancel_request(student_id, request_id):
    """Pending request cancel karta hai (sirf owner kar sakta hai)."""
    conn = get_connection()
    row = conn.execute(
        "SELECT status FROM rms_requests WHERE id = ? AND student_id = ?",
        (request_id, student_id),
    ).fetchone()

    if not row:
        conn.close()
        return {"success": False, "message": "Request nahi mili."}
    if row["status"] != "Pending":
        conn.close()
        return {"success": False, "message": f"Sirf Pending request cancel ho sakti hai. Abhi status: {row['status']}"}

    conn.execute(
        "UPDATE rms_requests SET status = 'Cancelled' WHERE id = ? AND student_id = ?",
        (request_id, student_id),
    )
    conn.commit()
    conn.close()
    return {"success": True, "message": f"Request {request_id} cancel ho gayi."}