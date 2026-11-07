from app.rms_agent import run_rms_turn
from app.rms_tools import get_student_by_reg_no

student = get_student_by_reg_no("12300004")  # Priya
session = {}

turns = [
    "RMS raise karna hai",
    "Meri attendance 12 October ko DBMS class me galat mark hui hai, main present tha",
    "haan",
]

for t in turns:
    print("USER :", t)
    print("BOT  :", run_rms_turn(student["id"], t, session))
    print()