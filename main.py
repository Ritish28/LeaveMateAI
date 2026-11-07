import re

import streamlit as st

from app.db import get_connection, setup_database
from app.intent_classifier import predict_intent
from app.leave_agent import run_leave_turn
from app.leave_tools import cancel_leave, get_leave_status, get_my_leaves
from app.rms_agent import run_rms_turn
from app.rms_tools import cancel_request, get_my_requests, get_request_status

setup_database()

st.set_page_config(page_title="LeaveMate AI", page_icon="🎓")
st.title("🎓 LeaveMate AI")
st.caption("Demo version: fictional students aur fictional data")


def load_students():
    conn = get_connection()
    rows = conn.execute("SELECT * FROM students ORDER BY id").fetchall()
    conn.close()
    return [dict(r) for r in rows]


def find_number(text):
    match = re.search(r"\d+", text)
    return int(match.group()) if match else None


def history_reply(student):
    rms = get_my_requests(student["id"])
    leaves = get_my_leaves(student["id"])
    lines = ["**Tumhari RMS requests:**"]
    lines += [f"- #{r['id']} | {r['category']} | {r['status']}" for r in rms] or ["- Koi request nahi mili."]
    lines += ["", "**Tumhari leave applications:**"]
    lines += [
        f"- #{l['id']} | {l['leave_type']} | {l['start_date']} se {l['end_date']} | {l['status']}"
        for l in leaves
    ] or ["- Koi leave nahi mili."]
    return "\n".join(lines)


def status_reply(student, text):
    is_leave = "leave" in text.lower() or "chhutti" in text.lower()
    number = find_number(text)

    if is_leave:
        item = get_leave_status(student["id"], number) if number else (get_my_leaves(student["id"]) or [None])[0]
        label = "Leave"
    else:
        item = get_request_status(student["id"], number) if number else (get_my_requests(student["id"]) or [None])[0]
        label = "RMS request"

    if not item:
        return f"{label} nahi mili. (Number sahi hai? Ya abhi tak koi {label} save nahi hui.)"
    return f"{label} #{item['id']} ka status: **{item['status']}**"


STOP_WORDS = {
    "rehne do", "rehnede", "rehne de", "cancel", "stop",
    "chhodo", "chhod do", "ruko", "nevermind", "nahi chahiye",
}


def cancel_reply(student, text):
    number = find_number(text)
    lowered = text.lower()
    is_leave = "leave" in lowered or "chhutti" in lowered
    is_rms = "rms" in lowered or "request" in lowered

    if not number:
        st.session_state.pending_cancel = True
        return "Kaunsi cancel karni hai? Aise likho: **cancel rms 3** ya **cancel leave 4**."

    st.session_state.pending_cancel = False
    if is_leave:
        return cancel_leave(student["id"], number)["message"]
    if is_rms:
        return cancel_request(student["id"], number)["message"] + " (RMS)"
    return "RMS ya leave? Aise likho: **cancel rms 3** ya **cancel leave 4**."


PROCESS_INFO = (
    "**Process (demo rules):**\n"
    "- **RMS:** attendance, academic, technical ya administrative problem ke liye. "
    "Mujhe problem batao, main category dhundhke request ready karungi, aur **tumhari haan ke baad** hi submit hogi.\n"
    "- **Leave types:** Medical, Personal, Family Emergency, Academic Event.\n"
    "- **Leave rules:** past date nahi, ek application me max 7 din, aur Pending leave ke saath overlap nahi.\n"
    "- Sirf **Pending** request cancel ho sakti hai.\n\n"
    "_Ye hamare demo ke rules hain, real LPU rules nahi._"
)


def reply(student, text):
    leave_session = st.session_state.leave_session
    rms_session = st.session_state.rms_session
    cleaned = text.lower().strip()

    # 1. Bot ne cancel ka number poochha tha?
    if st.session_state.get("pending_cancel") and find_number(text) and len(cleaned) < 20:
        if "leave" in cleaned or "rms" in cleaned:
            return cancel_reply(student, text)
        st.session_state.pending_cancel = False
        return "RMS ya leave? Aise likho: **cancel rms 3** ya **cancel leave 4**."

    # 2. Koi flow chal raha hai to usi me rehna hai
    if leave_session.get("stage") or rms_session.get("stage"):
        if cleaned in STOP_WORDS:
            leave_session.clear()
            rms_session.clear()
            return "Theek hai, band kar diya."
        if leave_session.get("stage"):
            return run_leave_turn(student["id"], text, leave_session)
        return run_rms_turn(student["id"], text, rms_session)

    # 3. Naya message: intent pakdo
    result = predict_intent(text)
    intent = result["intent"]
    debug = f"_(intent: {intent}, confidence: {result['confidence']})_"

    if not result["confident"]:
        return f"Mujhe pura samajh nahi aaya. Kya tum dobara thoda alag tarah se bata sakte ho?\n\n{debug}"
    if intent == "apply_leave":
        return f"{run_leave_turn(student['id'], text, leave_session)}\n\n{debug}"
    if intent == "create_rms":
        return f"{run_rms_turn(student['id'], text, rms_session)}\n\n{debug}"
    if intent == "view_history":
        return f"{history_reply(student)}\n\n{debug}"
    if intent == "check_status":
        return f"{status_reply(student, text)}\n\n{debug}"
    if intent == "cancel_request":
        return f"{cancel_reply(student, text)}\n\n{debug}"
    if intent == "ask_process":
        return f"{PROCESS_INFO}\n\n{debug}"
    return f"Hi! Main RMS, leave, status aur history me madad kar sakti hoon.\n\n{debug}"


# ---- Sidebar: student choose ----
students = load_students()
names = {f"{s['name']} ({s['reg_no']})": s for s in students}
choice = st.sidebar.selectbox("Demo student", list(names.keys()))
student = names[choice]
st.sidebar.write(f"Program: {student['program']}")
st.sidebar.write(f"Section: {student['section']}")

# Student badle to chat reset
if st.session_state.get("current_reg") != student["reg_no"]:
    st.session_state.current_reg = student["reg_no"]
    st.session_state.leave_session = {}
    st.session_state.rms_session = {}
    st.session_state.pending_cancel = False
    st.session_state.messages = [
        {"role": "assistant", "content": f"Hi {student['name']}! Main LeaveMate AI hoon. Batao kya karna hai?"}
    ]

# ---- Chat ----
for m in st.session_state.messages:
    with st.chat_message(m["role"]):
        st.markdown(m["content"])

user_text = st.chat_input("Apna message likho (English ya Hinglish)...")
if user_text:
    st.session_state.messages.append({"role": "user", "content": user_text})
    answer = reply(student, user_text)
    st.session_state.messages.append({"role": "assistant", "content": answer})
    st.rerun()