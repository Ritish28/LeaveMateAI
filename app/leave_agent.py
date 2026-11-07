import re
from app.fallback import fallback_leave
from app.leave_tools import LEAVE_TYPES, create_leave_application, parse_date, validate_leave
from datetime import date
from typing import Optional, TypedDict

from langgraph.graph import END, StateGraph

from app.leave_tools import LEAVE_TYPES, create_leave_application, validate_leave
from app.llm import ask_llm_json

FIELDS = ["leave_type", "start_date", "end_date", "reason"]
QUESTIONS = {
    "leave_type": f"Kaunsi type ki leave chahiye? Options: {', '.join(LEAVE_TYPES)}",
    "start_date": "Leave kis date se chahiye? (jaise kal, ya 2026-10-28)",
    "end_date": "Leave kis date tak chahiye?",
    "reason": "Leave ka reason kya hai? (thoda detail me likho)",
}


class LeaveState(TypedDict):
    student_id: int
    message: str
    details: dict          # ab tak jama hui details
    stage: str
    asking: str            # abhi kaunsa field poochh rahe hain             # "collecting" ya "confirming"
    reply: str             # user ko dikhane wala jawab
    done: bool             # kya ye flow khatam ho gaya
    saved: Optional[bool]  # sirf tab True jab DB me save hua


def extract_node(state: LeaveState):
    """Pehle simple jawab bina LLM ke pakdo, phir LLM, phir fallback."""
    details = dict(state["details"])
    asking = state.get("asking", "")
    message = state["message"].strip()
    lowered = message.lower()

    # 1. Bot ne jo poochha uska seedha jawab (LLM call nahi, quota bachta hai)
    if asking in ("start_date", "end_date") and parse_date(message):
        details[asking] = message
        return {"details": details}
    if asking == "leave_type":
        for lt in LEAVE_TYPES:
            if lowered == lt.lower():
                details["leave_type"] = lt
                return {"details": details}
    if asking == "reason" and len(message) >= 10:
        details["reason"] = message
        return {"details": details}

    # 2. LLM, aur fail ho to fallback
    today = date.today().isoformat()
    prompt = f"""Aaj ki date {today} hai.
Student ke message se leave ki details nikalo. Sirf JSON do.
Keys: leave_type, start_date (YYYY-MM-DD), end_date (YYYY-MM-DD), reason.
Jo cheez message me nahi hai uski value null rakho. Kuch andaza ya invent mat karo.
Agar message me saaf likha hai ki sirf ek din ki leave chahiye (jaise "kal ki leave") to end_date = start_date.
Agar sirf "from" date di hai aur end ka zikr nahi, to end_date null rakho.
leave_type sirf inme se: {', '.join(LEAVE_TYPES)}.

Message: {message}"""

    try:
        new = ask_llm_json(prompt) or {}
    except RuntimeError:
        new = fallback_leave(message)

    for key in FIELDS:
        value = new.get(key)
        if value and not details.get(key):
            details[key] = value
    return {"details": details}

def check_node(state: LeaveState):
    """Dekhta hai kaunsi cheez abhi bhi missing hai."""
    for key in FIELDS:
        if not state["details"].get(key):
            return {"stage": "collecting", "reply": QUESTIONS[key], "done": False, "asking": key}
    return {"stage": "validating", "asking": ""}

def validate_node(state: LeaveState):
    """Python rules check karta hai (LLM nahi)."""
    d = state["details"]
    result = validate_leave(state["student_id"], d["leave_type"], d["start_date"], d["end_date"], d["reason"])
    if not result["valid"]:
        # galat date wagairah hata do taaki dobara poochh sake
        return {"reply": f"Problem: {result['message']}\nSahi details dobara bhejo.", "stage": "collecting", "done": False,
                "details": {k: v for k, v in d.items() if k not in ("start_date", "end_date")}}
    summary = (
        f"Ye leave application ready hai:\n"
        f"- Type: {d['leave_type']}\n- From: {d['start_date']}\n- To: {d['end_date']}\n- Reason: {d['reason']}\n\n"
        f"{result['message']}\n**Submit kar du? (haan / nahi)**"
    )
    return {"reply": summary, "stage": "confirming", "done": False}


def route_after_check(state: LeaveState):
    return "validate" if state["stage"] == "validating" else END


def build_graph():
    g = StateGraph(LeaveState)
    g.add_node("extract", extract_node)
    g.add_node("check", check_node)
    g.add_node("validate", validate_node)
    g.set_entry_point("extract")
    g.add_edge("extract", "check")
    g.add_conditional_edges("check", route_after_check, {"validate": "validate", END: END})
    g.add_edge("validate", END)
    return g.compile()


_graph = build_graph()

YES = {"haan", "han", "ha", "yes", "y", "ok", "submit", "kar do", "kardo", "confirm"}
NO = {"nahi", "nahin", "no", "n", "cancel", "mat karo"}


def run_leave_turn(student_id, message, session):
    """
    Ek turn chalata hai. `session` ek dict hai jo chat ke beech yaad rakhta hai:
    {"details": {...}, "stage": "collecting" | "confirming"}
    Return: reply text
    """
    text = re.sub(r"[^\w\s]", "", message.lower()).strip()

    # Confirmation stage: sirf haan/nahi dekho, LLM nahi
    if session.get("stage") == "confirming":
        if text in YES:
            d = session["details"]
            result = create_leave_application(student_id, d["leave_type"], d["start_date"], d["end_date"], d["reason"])
            session.clear()
            if result["success"]:
                return f"Leave application submit ho gayi. ID: {result['leave_id']}"
            return f"Submit nahi hui: {result['message']}"
        if text in NO:
            session.clear()
            return "Theek hai, leave application cancel kar di. Kuch aur chahiye?"
        return "Kripya sirf **haan** ya **nahi** likho."

    # Collecting stage: graph chalao
    state = {
        "student_id": student_id,
        "message": message,
        "details": session.get("details", {}),
        "stage": "collecting",
        "reply": "",
        "done": False,
        "asking": session.get("asking", ""),
        "saved": None,
    }
    try:
        out = _graph.invoke(state)
    except RuntimeError:
        return "AI abhi busy hai. Thodi der baad apna message dobara bhejo. (Tumhari ab tak ki details safe hain.)"
    
    session["details"] = out["details"]
    session["stage"] = out["stage"]
    session["asking"] = out.get("asking", "")
    return out["reply"]