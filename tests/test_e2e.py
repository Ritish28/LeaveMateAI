import csv
import tempfile
from datetime import date, timedelta
from pathlib import Path

import app.db as db

# Asli database ki jagah temporary database (asli data safe)
db.DB_PATH = Path(tempfile.mkdtemp()) / "test.db"
db.setup_database()

import app.leave_agent as leave_agent
import app.rms_agent as rms_agent
from app.intent_classifier import predict_intent
from app.leave_agent import run_leave_turn
from app.leave_tools import get_my_leaves
from app.rms_agent import run_rms_turn
from app.rms_tools import (
    cancel_request,
    create_rms_request,
    get_my_requests,
    get_request_status,
)


def llm_down(prompt):
    raise RuntimeError("LLM band (test)")


# LLM band karke agent ko fallback mode me test karenge
leave_agent.ask_llm_json = llm_down
rms_agent.ask_llm_json = llm_down

rows = []


def add(part, name, ok, detail=""):
    rows.append((part, name, "PASS" if ok else "FAIL", detail))
    print(("PASS" if ok else "FAIL"), "-", name)
    if not ok and detail:
        print("      detail:", detail)


# ---------------- PART A: intent routing (20 naye messages) ----------------
routing = [
    ("mujhe apni attendance theek karwani hai RMS karo", "create_rms"),
    ("Hostel ke liye request raise karni hai", "create_rms"),
    ("My attendance was marked absent by mistake", "create_rms"),
    ("I want to take a sick leave from tomorrow", "apply_leave"),
    ("Kal mujhe college nahi aana leave laga do", "apply_leave"),
    ("Mujhe bukhar hai kal ki chhutti lagani hai", "apply_leave"),
    ("Meri leave ka status kya hai", "check_status"),
    ("Mera RMS approve hua kya", "check_status"),
    ("Is my request approved", "check_status"),
    ("Show me my submitted leaves", "view_history"),
    ("Meri sab requests ek saath dikhao", "view_history"),
    ("Request history dikhao", "view_history"),
    ("Please cancel my pending leave", "cancel_request"),
    ("Meri RMS request cancel kar do please", "cancel_request"),
    ("How long does leave approval take", "ask_process"),
    ("RMS kitne din me approve hota hai", "ask_process"),
    ("What documents do I need for RMS", "ask_process"),
    ("Hi, how is it going", "other"),
    ("Dhanyavaad", "other"),
    ("Who won the cricket match yesterday", "other"),
]

print("\n=== PART A: Intent routing ===")
correct = 0
for msg, expected in routing:
    r = predict_intent(msg)
    ok = r["intent"] == expected
    correct += ok
    add("A", msg, ok, f"expected={expected} got={r['intent']} conf={r['confidence']}")

# ---------------- PART B: agent flows aur safety ----------------
print("\n=== PART B: Agent flows (fallback mode) ===")

# RMS happy path (student 1)
s = {}
r1 = run_rms_turn(1, "Meri attendance galat mark hui hai", s)
add("B", "RMS: summary dikhti hai", "ready hai" in r1, r1)
r2 = run_rms_turn(1, "haan", s)
add("B", "RMS: haan par save hota hai", "submit ho gayi" in r2 and len(get_my_requests(1)) == 1, r2)

# RMS duplicate
s = {}
run_rms_turn(1, "Meri attendance galat mark hui hai", s)
r = run_rms_turn(1, "haan", s)
add("B", "RMS: duplicate block hota hai", "Submit nahi hui" in r and len(get_my_requests(1)) == 1, r)

# RMS follow-up sawaal, phir nahi (student 2)
s = {}
r = run_rms_turn(2, "RMS raise karna hai", s)
add("B", "RMS: category missing to poochta hai", "Ye kis type" in r, r)
r = run_rms_turn(2, "Technical Problem", s)
add("B", "RMS: phir description poochta hai", "detail" in r.lower(), r)
r = run_rms_turn(2, "UMS portal pe login nahi ho raha hai", s)
add("B", "RMS: sab milne par summary", "ready hai" in r, r)
run_rms_turn(2, "nahi", s)
add("B", "RMS: nahi bolne par save nahi hota", len(get_my_requests(2)) == 0)

# Confirmation guard (student 4)
s = {}
run_rms_turn(4, "Mere marks galat aaye hain", s)
r = run_rms_turn(4, "shayad", s)
add("B", "RMS: haan/nahi ke bina save nahi hota", "haan" in r and len(get_my_requests(4)) == 0, r)

# Leave happy path (student 2)
s = {}
r1 = run_leave_turn(2, "Kal se 2 din ki leave chahiye, bukhar hai", s)
add("B", "Leave: summary dikhti hai", "ready hai" in r1, r1)
r2 = run_leave_turn(2, "haan", s)
add("B", "Leave: haan par save hota hai", "submit ho gayi" in r2 and len(get_my_leaves(2)) == 1, r2)

# Leave overlap
s = {}
r = run_leave_turn(2, "Kal se 2 din ki leave chahiye, bukhar hai", s)
add("B", "Leave: overlap block hota hai", "Pending leave" in r and len(get_my_leaves(2)) == 1, r)

# Leave past date (student 3)
s = {}
r = run_leave_turn(3, "leave from 2020-01-01 to 2020-01-02 bukhar hai", s)
add("B", "Leave: past date reject hoti hai", "past" in r, r)

# Leave 10 din
start = date.today() + timedelta(days=30)
end = start + timedelta(days=9)
s = {}
r = run_leave_turn(3, f"leave from {start} to {end} bukhar hai", s)
add("B", "Leave: 7 din se zyada reject hoti hai", "max 7" in r, r)
add("B", "Leave: reject par kuch save nahi hua", len(get_my_leaves(3)) == 0)

# Leave missing details (student 4)
s = {}
r = run_leave_turn(4, "Mujhe kal ki leave chahiye", s)
add("B", "Leave: type missing to poochta hai", "Kaunsi type" in r, r)

# ---------------- PART C: tools (security) ----------------
print("\n=== PART C: Tools aur security ===")
rid = get_my_requests(1)[0]["id"]
add("C", "Ownership: doosre student ko status nahi dikhta", get_request_status(5, rid) is None)
add("C", "Ownership: doosra student cancel nahi kar sakta", cancel_request(5, rid)["success"] is False)
add("C", "Owner apni Pending request cancel kar sakta hai", cancel_request(1, rid)["success"] is True)
add("C", "Cancelled request dobara cancel nahi hoti", cancel_request(1, rid)["success"] is False)
add("C", "Galat category reject hoti hai",
    create_rms_request(1, "Random", "Kuch subject", "Kuch description yahan")["success"] is False)
add("C", "Chhota description reject hota hai",
    create_rms_request(1, "Technical Problem", "Kuch subject", "chhota")["success"] is False)
res = create_rms_request(3, "Technical Problem", "Test subject", "'); DROP TABLE students;-- test text")
conn = db.get_connection()
n_students = conn.execute("SELECT COUNT(*) FROM students").fetchone()[0]
conn.close()
add("C", "SQL injection jaisa text table nahi todta", res["success"] is True and n_students == 5)

# ---------------- Summary + CSV ----------------
a_total = len(routing)
b_rows = [r for r in rows if r[0] in ("B", "C")]
b_pass = sum(1 for r in b_rows if r[2] == "PASS")
print("\n==================== SUMMARY ====================")
print(f"Part A (intent routing, 20 naye messages): {correct}/{a_total} = {correct / a_total:.0%}")
print(f"Part B+C (agent flows aur security):       {b_pass}/{len(b_rows)} passed")

out = Path(__file__).parent / "e2e_results.csv"
with open(out, "w", newline="", encoding="utf-8") as f:
    w = csv.writer(f)
    w.writerow(["part", "test", "result", "detail"])
    w.writerows(rows)
print("Results saved:", out)