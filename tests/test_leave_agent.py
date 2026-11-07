from app.leave_agent import run_leave_turn
from app.rms_tools import get_student_by_reg_no

student = get_student_by_reg_no("12300003")  # Rohan
session = {}

turns = [
    "I need leave from 2026-11-03",
    "Family function hai, ghar jaana hai",
    "Personal",
    "2026-11-04",
    "haan",
]

for t in turns:
    print("USER :", t)
    print("BOT  :", run_leave_turn(student["id"], t, session))
    print()