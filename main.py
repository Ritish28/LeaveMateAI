import re

import streamlit as st

from app.db import get_connection, setup_database
from app.intent_classifier import predict_intent
from app.leave_agent import run_leave_turn
from app.leave_tools import cancel_leave, get_leave_status, get_my_leaves
from app.rms_agent import run_rms_turn
from app.rms_tools import cancel_request, get_my_requests, get_request_status

setup_database()

st.set_page_config(page_title="LeaveMate AI", page_icon="🎟️", layout="wide")

CSS = """
<style>
@import url('https://fonts.googleapis.com/css2?family=Space+Grotesk:wght@400;500;700&family=JetBrains+Mono:wght@400;700&display=swap');

:root {
    --ink: #0A0A0F; --card: #12121A; --amber: #FFB400; --orange: #FF5E1A;
    --lime: #C6FF3D; --text: #EDEDF2; --muted: #8A8A9A;
}
@property --angle {syntax: '<angle>'; initial-value: 0deg; inherits: false;}

html, body, .stMarkdown, .stMarkdown p, .stMarkdown li, p, li, label {font-family: 'Space Grotesk', sans-serif !important;}
[data-testid="stToolbar"], #MainMenu, footer {display: none !important;}
header[data-testid="stHeader"] {background: transparent;}
.block-container {padding-top: 1.2rem; max-width: 1150px;}

/* ---------- moving grid background ---------- */
.stApp {
    background-color: var(--ink);
    background-image:
        radial-gradient(circle at 80% 0%, rgba(255,94,26,0.18), transparent 38%),
        radial-gradient(circle at 0% 100%, rgba(198,255,61,0.10), transparent 35%),
        linear-gradient(rgba(255,255,255,0.045) 1px, transparent 1px),
        linear-gradient(90deg, rgba(255,255,255,0.045) 1px, transparent 1px);
    background-size: auto, auto, 46px 46px, 46px 46px;
    animation: gridDrift 18s linear infinite;
}
@keyframes gridDrift {to {background-position: 0 0, 0 0, 46px 46px, 46px 46px;}}

/* ---------- hero ---------- */
.hero {
    position: relative; padding: 30px 34px; border-radius: 6px; background: var(--card);
    border: 1px solid rgba(255,255,255,0.1); overflow: hidden;
    animation: slideIn 0.7s cubic-bezier(.2,.9,.3,1) both;
}
.hero::before {
    content: ""; position: absolute; left: 0; top: 0; bottom: 0; width: 6px;
    background: linear-gradient(var(--amber), var(--orange));
}
.hero::after {
    content: ""; position: absolute; top: 0; left: -40%; width: 30%; height: 100%;
    background: linear-gradient(100deg, transparent, rgba(255,180,0,0.14), transparent);
    animation: sweep 5s ease-in-out infinite;
}
@keyframes sweep {0% {left: -40%;} 60%,100% {left: 130%;}}
.hero .tag {font-family: 'JetBrains Mono', monospace; font-size: 0.75rem; color: var(--lime); letter-spacing: 3px;}
.hero h1 {
    margin: 6px 0 8px 0; font-size: 3rem; font-weight: 700; letter-spacing: -1.5px; line-height: 1;
    background: linear-gradient(90deg, #fff 0%, var(--amber) 45%, var(--orange) 70%, #fff 100%);
    background-size: 250% auto; -webkit-background-clip: text; background-clip: text; color: transparent;
    animation: shimmer 6s linear infinite;
}
@keyframes shimmer {to {background-position: 250% center;}}
.typed {
    font-family: 'JetBrains Mono', monospace; font-size: 0.98rem; color: var(--text);
    display: inline-block; overflow: hidden; white-space: nowrap; width: 44ch;
    border-right: 2px solid var(--amber);
    animation: typing 3.2s steps(44) 0.4s both, blink 0.8s step-end infinite;
}
@keyframes typing {from {width: 0;} to {width: 44ch;}}
@keyframes blink {50% {border-color: transparent;}}
@keyframes slideIn {from {opacity: 0; transform: translateX(-30px);} to {opacity: 1; transform: translateX(0);}}
@keyframes rise {from {opacity: 0; transform: translateY(16px);} to {opacity: 1; transform: translateY(0);}}

/* ---------- ticker ---------- */
.ticker {
    margin: 14px 0 18px 0; overflow: hidden; white-space: nowrap; border-radius: 4px;
    background: var(--amber); color: #111; font-family: 'JetBrains Mono', monospace;
    font-weight: 700; font-size: 0.8rem; padding: 7px 0; letter-spacing: 2px;
}
.ticker .track {display: inline-block; animation: scroll 26s linear infinite;}
@keyframes scroll {to {transform: translateX(-50%);}}

/* ---------- stat tickets with spinning neon border ---------- */
.stat {
    position: relative; padding: 16px 18px 14px 22px; border-radius: 10px; border: 1px solid transparent;
    background:
        linear-gradient(var(--card), var(--card)) padding-box,
        conic-gradient(from var(--angle), transparent 0%, var(--amber) 12%, transparent 30%, transparent 60%, var(--lime) 75%, transparent 90%) border-box;
    animation: spin 5s linear infinite, rise 0.6s ease both;
    transition: transform .25s ease;
}
@keyframes spin {to {--angle: 360deg;}}
.stat:hover {transform: translateY(-6px) rotate(-0.6deg);}
.stat::before, .stat::after {
    content: ""; position: absolute; left: -7px; width: 14px; height: 14px; border-radius: 50%; background: var(--ink);
}
.stat::before {top: 12px;} .stat::after {bottom: 12px;}
.stat .label {font-family: 'JetBrains Mono', monospace; font-size: 0.68rem; color: var(--muted); letter-spacing: 2px; text-transform: uppercase;}
.stat .value {font-family: 'JetBrains Mono', monospace; font-size: 2.3rem; font-weight: 700; line-height: 1.1; margin-top: 4px;}
.stat .value.a {color: var(--amber);} .stat .value.l {color: var(--lime);}
.stat .bar {height: 3px; margin-top: 8px; background: repeating-linear-gradient(90deg, var(--muted) 0 6px, transparent 6px 10px); opacity: .45;}

/* ---------- section titles ---------- */
.section-title {
    font-family: 'JetBrains Mono', monospace; font-size: 0.78rem; letter-spacing: 3px; color: var(--amber);
    margin: 20px 0 8px 2px; text-transform: uppercase;
}
.section-title::before {content: "// "; color: var(--muted);}

/* ---------- buttons ---------- */
.stButton > button {
    width: 100%; border-radius: 4px; border: 1px solid rgba(255,180,0,0.5); background: transparent;
    color: var(--text); font-family: 'JetBrains Mono', monospace; font-size: 0.82rem; letter-spacing: 1px;
    text-transform: uppercase; padding: 0.75rem 0.4rem; position: relative; overflow: hidden;
    transition: all .25s ease;
}
.stButton > button:hover {
    background: var(--amber); color: #111; border-color: var(--amber);
    transform: translate(-3px, -3px); box-shadow: 5px 5px 0 var(--orange);
}
.stButton > button:active {transform: translate(0, 0); box-shadow: none;}

/* ---------- chat ---------- */
[data-testid="stChatMessage"] {
    background: var(--card); border: 1px solid rgba(255,255,255,0.09); border-left: 4px solid var(--amber);
    border-radius: 6px; padding: 12px 16px; margin-bottom: 10px; animation: rise 0.4s ease both;
}
[data-testid="stChatMessage"]:has([data-testid="stChatMessageAvatarUser"]),
[data-testid="stChatMessage"]:has([data-testid="chatAvatarIcon-user"]) {
    flex-direction: row-reverse; text-align: right; border-left: 1px solid rgba(255,255,255,0.09);
    border-right: 4px solid var(--lime); background: rgba(198,255,61,0.05);
    margin-left: 18%;
}
[data-testid="stChatMessage"]:not(:has([data-testid="stChatMessageAvatarUser"])):not(:has([data-testid="chatAvatarIcon-user"])) {
    margin-right: 18%;
}
[data-testid="stChatInput"] {border: 1px solid var(--amber); border-radius: 6px;}

.typing {display: inline-flex; gap: 6px; padding: 10px 4px;}
.typing span {width: 9px; height: 9px; border-radius: 50%; background: var(--amber); animation: bounce 1s infinite;}
.typing span:nth-child(2) {animation-delay: .15s; background: var(--orange);}
.typing span:nth-child(3) {animation-delay: .3s; background: var(--lime);}
@keyframes bounce {0%,60%,100% {transform: translateY(0); opacity: .5;} 30% {transform: translateY(-9px); opacity: 1;}}

/* ---------- sidebar ID card ---------- */
section[data-testid="stSidebar"] {background: #0D0D14; border-right: 1px solid rgba(255,255,255,0.07);}
.idcard {
    position: relative; margin-top: 10px; padding: 34px 16px 14px 16px; border-radius: 12px; background: var(--card);
    border: 1px solid rgba(255,255,255,0.12); overflow: hidden; animation: rise 0.6s ease both;
}
.idcard .hole {position: absolute; top: 10px; left: 50%; width: 46px; height: 8px; margin-left: -23px;
               border-radius: 8px; background: var(--ink); border: 1px solid rgba(255,255,255,0.15);}
.idcard .stripe {
    position: absolute; left: 0; right: 0; bottom: 0; height: 6px;
    background: linear-gradient(90deg, var(--amber), var(--orange), var(--lime), var(--amber));
    background-size: 300% 100%; animation: holo 4s linear infinite;
}
@keyframes holo {to {background-position: 300% 0;}}
.idcard .avatar {
    width: 58px; height: 58px; border-radius: 12px; display: flex; align-items: center; justify-content: center;
    font-family: 'JetBrains Mono', monospace; font-size: 1.4rem; font-weight: 700; color: #111;
    background: linear-gradient(135deg, var(--amber), var(--orange)); margin-bottom: 10px;
}
.idcard .name {font-weight: 700; font-size: 1.1rem;}
.idcard .meta {font-family: 'JetBrains Mono', monospace; font-size: 0.74rem; color: var(--muted); margin-top: 3px;}
.demo-note {font-family: 'JetBrains Mono', monospace; font-size: 0.68rem; color: var(--muted); margin-top: 14px;}
</style>
"""
st.markdown(CSS, unsafe_allow_html=True)

TICKER_TEXT = "RMS &nbsp;●&nbsp; LEAVE &nbsp;●&nbsp; STATUS &nbsp;●&nbsp; HINGLISH SUPPORTED &nbsp;●&nbsp; CONFIRM BEFORE SUBMIT &nbsp;●&nbsp; OWNERSHIP SAFE &nbsp;●&nbsp; "
st.markdown(
    f"""
    <div class="hero">
        <div class="tag">STUDENT SERVICES // AI AGENT</div>
        <h1>LeaveMate AI</h1>
        <span class="typed">Leave. RMS. Status. Hinglish me. Bas bol do.</span>
    </div>
    <div class="ticker"><div class="track">{TICKER_TEXT * 4}</div></div>
    """,
    unsafe_allow_html=True,
)


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
    <div class="idcard">
        <div class="hole"></div>
        <div class="avatar">{initials}</div>
        <div class="name">{student['name']}</div>
        <div class="meta">{student['program']}</div>
        <div class="meta">SECTION {student['section']} · REG {student['reg_no']}</div>
        <div class="stripe"></div>
    </div>
    """,
    unsafe_allow_html=True,
)
show_debug = st.sidebar.toggle("Show intent debug", value=False)
st.sidebar.markdown(
    '<div class="demo-note">DEMO MODE: fictional students, fictional data. Not connected to the real LPU system.</div>',
    unsafe_allow_html=True,
)

if st.session_state.get("current_reg") != student["reg_no"]:
    st.session_state.current_reg = student["reg_no"]
    st.session_state.leave_session = {}
    st.session_state.rms_session = {}
    st.session_state.pending_cancel = False
    st.session_state.messages = [
        {"role": "assistant", "content": f"Hi {student['name']}! Main LeaveMate AI hoon. Batao kya karna hai?"}
    ]

# ---- Live stat tickets ----
rms_all = get_my_requests(student["id"])
leave_all = get_my_leaves(student["id"])
pending_rms = sum(1 for r in rms_all if r["status"] == "Pending")
pending_leave = sum(1 for l in leave_all if l["status"] == "Pending")

stats = [
    ("RMS requests", len(rms_all), "a"),
    ("RMS pending", pending_rms, "l"),
    ("Leaves", len(leave_all), "a"),
    ("Leave pending", pending_leave, "l"),
]
for col, (label, value, tone) in zip(st.columns(4), stats):
    col.markdown(
        f'<div class="stat"><div class="label">{label}</div>'
        f'<div class="value {tone}">{value:02d}</div><div class="bar"></div></div>',
        unsafe_allow_html=True,
    )

# ---- Quick actions ----
st.markdown('<div class="section-title">Quick actions</div>', unsafe_allow_html=True)
q1, q2, q3, q4 = st.columns(4)
if q1.button("New RMS"):
    st.session_state.quick = "RMS raise karna hai"
if q2.button("Apply leave"):
    st.session_state.quick = "Mujhe leave chahiye"
if q3.button("My requests"):
    st.session_state.quick = "Meri pichli saari requests dikhao"
if q4.button("Check status"):
    st.session_state.quick = "Check my RMS status"

# ---- Chat ----
st.markdown('<div class="section-title">Chat</div>', unsafe_allow_html=True)
for m in st.session_state.messages:
    content = m["content"]
    if not show_debug:
        content = re.sub(r"\n\n_\(intent:.*\)_\s*$", "", content)
    with st.chat_message(m["role"], avatar="🎟️" if m["role"] == "assistant" else "🙂"):
        st.markdown(content)

typed = st.chat_input("Type here... English ya Hinglish")
user_text = typed or st.session_state.pop("quick", None)
if user_text:
    st.session_state.messages.append({"role": "user", "content": user_text})
    loader = st.empty()
    loader.markdown('<div class="typing"><span></span><span></span><span></span></div>', unsafe_allow_html=True)
    answer = reply(student, user_text)
    loader.empty()
    st.session_state.messages.append({"role": "assistant", "content": answer})
    st.rerun()