from app.rms_tools import (
    get_student_by_reg_no,
    create_rms_request,
    get_my_requests,
    get_request_status,
    cancel_request,
)

student = get_student_by_reg_no("12300001")
print("Student:", student["name"])

print("\n1. Nayi request save:")
r = create_rms_request(student["id"], "Attendance Issue", "Attendance galat mark hui", "Meri attendance 12 Oct ko galat mark hui hai, please check karein.")
print(r)

print("\n2. Wahi request dobara (duplicate block hona chahiye):")
print(create_rms_request(student["id"], "Attendance Issue", "Attendance galat mark hui", "Meri attendance 12 Oct ko galat mark hui hai, please check karein."))

print("\n3. Galat category (reject hona chahiye):")
print(create_rms_request(student["id"], "Random", "Kuch bhi subject", "Kuch bhi description yahan"))

print("\n4. Meri saari requests:")
for req in get_my_requests(student["id"]):
    print(req["id"], req["category"], req["status"])

print("\n5. Doosre student (Simran) se Aarav ki request dekhna (None aana chahiye):")
other = get_student_by_reg_no("12300002")
print(get_request_status(other["id"], r["request_id"] or 1))