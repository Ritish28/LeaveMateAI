from datetime import date, timedelta
from app.rms_tools import get_student_by_reg_no
from app.leave_tools import (
    create_leave_application,
    get_my_leaves,
    get_leave_status,
    cancel_leave,
)

student = get_student_by_reg_no("12300001")
other = get_student_by_reg_no("12300002")

tomorrow = date.today() + timedelta(days=1)
day_after = date.today() + timedelta(days=2)
reason = "Mujhe bukhar hai, doctor ne rest bola hai."

print("1. Sahi leave:")
r = create_leave_application(student["id"], "Medical", str(tomorrow), str(day_after), reason)
print(r)

print("\n2. Overlapping leave (block hona chahiye):")
print(create_leave_application(student["id"], "Medical", str(tomorrow), str(tomorrow), reason))

print("\n3. Past date (reject hona chahiye):")
print(create_leave_application(student["id"], "Personal", "2020-01-01", "2020-01-02", reason))

print("\n4. 10 din ki leave (reject hona chahiye):")
far = date.today() + timedelta(days=30)
print(create_leave_application(student["id"], "Personal", str(far), str(far + timedelta(days=9)), reason))

print("\n5. Galat date format (reject hona chahiye):")
print(create_leave_application(student["id"], "Personal", "kal", "parso", reason))

print("\n6. Meri leaves:")
for lv in get_my_leaves(student["id"]):
    print(lv["id"], lv["leave_type"], lv["start_date"], lv["end_date"], lv["status"])

print("\n7. Simran se Aarav ki leave dekhna (None aana chahiye):")
print(get_leave_status(other["id"], r["leave_id"] or 1))