from datetime import date

from app.llm import ask_llm_json

today = date.today().isoformat()

messages = [
    "Kal se 2 din ki leave chahiye, bukhar hai",
    "Meri attendance 12 October ko galat mark hui hai, RMS raise karna hai",
    "I need leave next Monday",
]

for m in messages:
    prompt = f"""Aaj ki date {today} hai.
Student ke message se details nikalo. Sirf JSON do, aur kuch nahi.
Keys: leave_type, start_date (YYYY-MM-DD), end_date (YYYY-MM-DD), reason, rms_category, rms_description.
Jo cheez message me nahi hai uski value null rakho. Kuch andaza mat lagao.
leave_type sirf inme se: Medical, Personal, Family Emergency, Academic Event.
rms_category sirf inme se: Attendance Issue, Academic Issue, Technical Problem, Administrative Request.

Message: {m}"""
    print("Message:", m)
    print("Result :", ask_llm_json(prompt))
    print()