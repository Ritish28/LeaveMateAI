import sqlite3
from pathlib import Path

# Database file ka path: LeaveMateAI/database/leavemate.db
DB_PATH = Path(__file__).resolve().parent.parent / "database" / "leavemate.db"


def get_connection():
    """Database se connection kholta hai."""
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)  # folder na ho to bana do
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row  # rows ko naam se access kar sakte hain
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


def create_tables():
    """3 tables banata hai (agar pehle se nahi hain)."""
    conn = get_connection()
    cur = conn.cursor()

    cur.execute("""
        CREATE TABLE IF NOT EXISTS students (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            reg_no TEXT UNIQUE NOT NULL,
            name TEXT NOT NULL,
            email TEXT NOT NULL,
            program TEXT NOT NULL,
            section TEXT NOT NULL
        )
    """)

    cur.execute("""
        CREATE TABLE IF NOT EXISTS rms_requests (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            student_id INTEGER NOT NULL,
            category TEXT NOT NULL,
            subject TEXT NOT NULL,
            description TEXT NOT NULL,
            status TEXT NOT NULL DEFAULT 'Pending',
            created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (student_id) REFERENCES students(id)
        )
    """)

    cur.execute("""
        CREATE TABLE IF NOT EXISTS leave_applications (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            student_id INTEGER NOT NULL,
            leave_type TEXT NOT NULL,
            start_date TEXT NOT NULL,
            end_date TEXT NOT NULL,
            reason TEXT NOT NULL,
            status TEXT NOT NULL DEFAULT 'Pending',
            created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (student_id) REFERENCES students(id)
        )
    """)

    conn.commit()
    conn.close()


def add_sample_students():
    """5 fictional students daalta hai (sirf agar table khali ho)."""
    conn = get_connection()
    cur = conn.cursor()

    count = cur.execute("SELECT COUNT(*) FROM students").fetchone()[0]
    if count == 0:
        students = [
            ("12300001", "Aarav Sharma", "aarav@demo.test", "B.Tech CSE", "K23AA"),
            ("12300002", "Simran Kaur", "simran@demo.test", "B.Tech CSE", "K23AB"),
            ("12300003", "Rohan Verma", "rohan@demo.test", "BCA", "K23BC"),
            ("12300004", "Priya Singh", "priya@demo.test", "B.Tech ECE", "K23CD"),
            ("12300005", "Arjun Mehta", "arjun@demo.test", "MBA", "K23EF"),
        ]
        cur.executemany(
            "INSERT INTO students (reg_no, name, email, program, section) VALUES (?, ?, ?, ?, ?)",
            students,
        )
        conn.commit()

    conn.close()


def setup_database():
    """Ek hi call me sab setup."""
    create_tables()
    add_sample_students()


if __name__ == "__main__":
    setup_database()
    print("Database ready! File:", DB_PATH)