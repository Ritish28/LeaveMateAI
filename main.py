import re

import streamlit as st

from app.db import get_connection, setup_database
from app.intent_classifier import predict_intent
from app.leave_agent import run_leave_turn
from app.leave_tools import cancel_leave, get_leave_status, get_my_leaves
from app.rms_agent import run_rms_turn
from app.rms_tools import cancel_request, get_my_requests, get_request_status

setup_database()

st.set_page_config(page_title="LeaveMate AI", page_icon="🎓", layout="centered")

CSS = """
<style>
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&display=swap');

:root {--bg: #0B0D12; --card: #12151C; --line: rgba(255,255,255,0.08);
       --accent: #34D399; --muted: #8B90A0; --text: #E6E8EE;}

html, body, .stMarkdown, .stMarkdown p, .stMarkdown li, p, li, label, button, input, textarea {
    font-family: 'Inter', sans-serif !important;
}
[data-testid="stToolbar"], #MainMenu, footer {display: none !important;}
header[data-testid="stHeader"] {background: transparent;}
.stApp {
    background: radial-gradient(ellipse at 50% -10%, rgba(52,211,153,0.10), transparent 55%), var(--bg);
}
.block-container {padding-top: 1.6rem; max-width: 780px;}

@keyframes fadeUp {from {opacity: 0; transform: translateY(10px);} to {opacity: 1; transform: translateY(0);}}
@keyframes pulse {0% {box-shadow: 0 0 0 0 rgba(52,211,153,0.6);} 70% {box-shadow: 0 0 0 8px rgba(52,211,153,0);} 100% {box-shadow: 0 0 0 0 rgba(52,211,153,0);}}

/* header */
.top {display: flex; align-items: center; justify-content: space-between; margin-bottom: 14px; animation: fadeUp .5s ease both;}
.brand {display: flex; align-items: center; gap: 12px;}
.logo {width: 42px; height: 42px; border-radius: 12px; display: flex; align-items: center; justify-content: center;
       font-size: 1.3rem; background: linear-gradient(135deg, #34D399, #22B8CF);}
.brand h1 {margin: 0; font-size: 1.35rem; font-weight: 700; letter-spacing: -0.3px;}
.brand span {font-size: 0.82rem; color: var(--muted);}
.status {display: flex; align-items: center; gap: 8px; font-size: 0.8rem; color: var(--muted);
         background: var(--card); border: 1px solid var(--line); padding: 6px 12px; border-radius: 999px;}
.dot {width: 8px; height: 8px; border-radius: 50%; background: var(--accent); animation: pulse 2s infinite;}

/* stats */
.stats {display: flex; gap: 10px; margin: 6px 0 16px 0; animation: fadeUp .6s ease both;}
.pill {flex: 1; background: var(--card); border: 1px solid var(--line); border-radius: 14px; padding: 12px 14px;
       transition: border-color .2s ease, transform .2s ease;}
.pill:hover {border-color: rgba(52,211,153,0.5); transform: translateY(-2px);}
.pill .n {font-size: 1.5rem; font-weight: 700; line-height: 1.1;}
.pill .n.hot {color: var(--accent);}
.pill .l {font-size: 0.72rem; color: var(--muted); margin-top: 2px;}

/* quick action chips */
.stButton > button {
    width: 100%; border-radius: 999px; border: 1px solid var(--line); background: var(--card);
    color: var(--text); font-weight: 500; font-size: 0.85rem; padding: 0.55rem 0.4rem; transition: all .2s ease;
}
.stButton > button:hover {border-color: var(--accent); color: var(--accent); background: rgba(52,211,153,0.08); transform: translateY(-2px);}
.stButton > button:active {transform: scale(0.97);}

/* chat */
[data-testid="stChatMessage"] {
    background: var(--card); border: 1px solid var(--line); border-radius: 16px;
    padding: 12px 16px; margin: 8px 0; max-width: 88%; animation: fadeUp .35s ease both;
}
[data-testid="stChatMessage"]:has([data-testid="stChatMessageAvatarUser"]),
[data-testid="stChatMessage"]:has([data-testid="chatAvatarIcon-user"]) {
    margin-left: auto; flex-direction: row-reverse; text-align: right;
    background: rgba(52,211,153,0.12); border-color: rgba(52,211,153,0.35);
}
[data-testid="stChatInput"] {border-radius: 16px; border: 1px solid var(--line); background: var(--card);}
[data-testid="stChatInput"]:focus-within {border-color: var(--accent); box-shadow: 0 0 0 3px rgba(52,211,153,0.15);}

.typing {display: inline-flex; gap: 5px; padding: 8px 2px;}
.typing span {width: 7px; height: 7px; border-radius: 50%; background: var(--accent); animation: bounce 1s infinite;}
.typing span:nth-child(2) {animation-delay: .15s;} .typing span:nth-child(3) {animation-delay: .3s;}
@keyframes bounce {0%,60%,100% {transform: translateY(0); opacity: .4;} 30% {transform: translateY(-6px); opacity: 1;}}

/* sidebar */
section[data-testid="stSidebar"] {background: #0E1016; border-right: 1px solid var(--line);}
.me {margin-top: 12px; padding: 14px; border-radius: 14px; background: var(--card); border: 1px solid var(--line);}
.me .av {width: 44px; height: 44px; border-radius: 50%; display: flex; align-items: center; justify-content: center;
         font-weight: 700; color: #06281D; background: linear-gradient(135deg, #34D399, #22B8CF); margin-bottom: 8px;}
.me .nm {font-weight: 600;} .me .mt {font-size: 0.78rem; color: var(--muted); margin-top: 2px;}
.note {font-size: 0.72rem; color: var(--muted); margin-top: 14px; line-height: 1.5;}
</style>
"""
st.markdown(CSS, unsafe_allow_html=True)


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

    if st.session_state.get("pending_cancel") and find_number(text) and len(cleaned) < 20:
        if "leave" in cleaned or "rms" in cleaned:
            return cancel_reply(student, text)
        st.session_state.pending_cancel = False
        return "RMS ya leave? Aise likho: **cancel rms 3** ya **cancel leave 4**."

    if leave_session.get("stage") or rms_session.get("stage"):
        if cleaned in STOP_WORDS:
            leave_session.clear()
            rms_session.clear()
            return "Theek hai, band kar diya."
        if leave_session.get("stage"):
            return run_leave_turn(student["id"], text, leave_session)
        return run_rms_turn(student["id"], text, rms_session)

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


# ---- Sidebar ----
students = load_students()
names = {f"{s['name']} ({s['reg_no']})": s for s in students}
choice = st.sidebar.selectbox("Demo student", list(names.keys()))
student = names[choice]

initials = "".join(w[0] for w in student["name"].split()[:2]).upper()
st.sidebar.markdown(
    f"""
    <div class="me">
        <div class="av">{initials}</div>
        <div class="nm">{student['name']}</div>
        <div class="mt">{student['program']} · {student['section']}</div>
        <div class="mt">Reg {student['reg_no']}</div>
    </div>
    """,
    unsafe_allow_html=True,
)
show_debug = st.sidebar.toggle("Show intent debug", value=False)
st.sidebar.markdown(
    '<div class="note">Demo mode: fictional students aur data. Real LPU system se connected nahi.</div>',
    unsafe_allow_html=True,
)

if st.session_state.get("current_reg") != student["reg_no"]:
    st.session_state.current_reg = student["reg_no"]
    st.session_state.leave_session = {}
    st.session_state.rms_session = {}
    st.session_state.pending_cancel = False
    st.session_state.messages = [
        {"role": "assistant", "content": f"Hi {student['name'].split()[0]}! 👋 Leave ya RMS, jo bhi karna hai bol do."}
    ]

# ---- Header ----
st.markdown(
    """
    <div class="top">
        <div class="brand">
            <div class="logo">🎓</div>
            <div><h1>LeaveMate AI</h1><span>Leave aur RMS, English ya Hinglish me</span></div>
        </div>
        <div class="status"><span class="dot"></span>Online</div>
    </div>
    """,
    unsafe_allow_html=True,
)

# ---- Stats ----
rms_all = get_my_requests(student["id"])
leave_all = get_my_leaves(student["id"])
pending_rms = sum(1 for r in rms_all if r["status"] == "Pending")
pending_leave = sum(1 for l in leave_all if l["status"] == "Pending")
st.markdown(
    f"""
    <div class="stats">
        <div class="pill"><div class="n">{len(rms_all)}</div><div class="l">RMS requests</div></div>
        <div class="pill"><div class="n hot">{pending_rms}</div><div class="l">RMS pending</div></div>
        <div class="pill"><div class="n">{len(leave_all)}</div><div class="l">Leaves</div></div>
        <div class="pill"><div class="n hot">{pending_leave}</div><div class="l">Leave pending</div></div>
    </div>
    """,
    unsafe_allow_html=True,
)

# ---- Quick actions ----
q1, q2, q3, q4 = st.columns(4)
if q1.button("📝 New RMS"):
    st.session_state.quick = "RMS raise karna hai"
if q2.button("🏖️ Apply leave"):
    st.session_state.quick = "Mujhe leave chahiye"
if q3.button("📋 My requests"):
    st.session_state.quick = "Meri pichli saari requests dikhao"
if q4.button("🔎 Status"):
    st.session_state.quick = "Check my RMS status"

# ---- Chat ----
for m in st.session_state.messages:
    content = m["content"]
    if not show_debug:
        content = re.sub(r"\n\n_\(intent:.*\)_\s*$", "", content)
    with st.chat_message(m["role"], avatar="🎓" if m["role"] == "assistant" else "🙂"):
        st.markdown(content)

typed = st.chat_input("Message likho... English ya Hinglish")
user_text = typed or st.session_state.pop("quick", None)
if user_text:
    st.session_state.messages.append({"role": "user", "content": user_text})
    loader = st.empty()
    loader.markdown('<div class="typing"><span></span><span></span><span></span></div>', unsafe_allow_html=True)
    answer = reply(student, user_text)
    loader.empty()
    st.session_state.messages.append({"role": "assistant", "content": answer})
    st.rerun()