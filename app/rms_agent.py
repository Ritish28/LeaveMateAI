import re
from typing import TypedDict

from langgraph.graph import END, StateGraph

from app.fallback import fallback_rms
from app.llm import ask_llm_json
from app.rms_tools import CATEGORIES, create_rms_request

FIELDS = ["category", "description"]
QUESTIONS = {
    "category": f"Ye kis type ki problem hai? Options: {', '.join(CATEGORIES)}",
    "description": "Problem detail me batao (kab, kya galat hua). Kam se kam ek poori line likho.",
}


class RmsState(TypedDict):
    student_id: int
    message: str
    details: dict
    stage: str
    reply: str


def make_subject(text, limit=60):
    """Shabd ke beech me kate bina subject banata hai."""
    text = text.strip()
    if len(text) <= limit:
        return text
    return text[:limit].rsplit(" ", 1)[0] + "..."


def polish(details):
    """Subject aur description ko formal English me likhta hai. LLM fail ho to original rakhta hai."""
    original = details["description"]
    prompt = f"""Ek student ki RMS request hai. Category: {details['category']}.
Student ka message (Hinglish ho sakta hai): {original}
Sirf JSON do: {{"subject": "...", "description": "..."}}
subject: formal English, max 10 words.
description: formal English, 1 se 3 sentences, sirf wahi facts jo student ne bataye.
Koi date, naam ya detail invent mat karo."""
    try:
        data = ask_llm_json(prompt) or {}
    except RuntimeError:
        data = {}

    subject = (data.get("subject") or "").strip()
    desc = (data.get("description") or "").strip()
    if len(subject) < 5 or len(desc) < 10:  # LLM fail ho to simple fallback
        subject = f"{details['category']}: {make_subject(original, 40)}"
        desc = original
    details["subject"] = subject
    details["description_en"] = desc


def extract_node(state: RmsState):
    """Pehle simple jawab bina LLM ke pakdo, phir LLM, phir fallback."""
    details = dict(state["details"])
    message = state["message"].strip()
    lowered = message.lower()

    # 1. Category seedha likhi ho
    if not details.get("category"):
        for c in CATEGORIES:
            if lowered == c.lower():
                details["category"] = c
                return {"details": details}

    # 2. Category mil chuki hai, ab user ne detail likhi (LLM call nahi)
    if details.get("category") and not details.get("description") and len(message) >= 10:
        details["description"] = message
        return {"details": details}

    # 3. LLM, aur fail ho to fallback
    prompt = f"""Student ke message se RMS request ki details nikalo. Sirf JSON do.
Keys: category, description.
category sirf inme se: {', '.join(CATEGORIES)}.
Hint: attendance galat mark hona = Attendance Issue; marks/result/exam/timetable = Academic Issue;
portal/login/upload/payment page ki dikkat = Technical Problem; certificate/NOC/ID card/hostel = Administrative Request.
description: student ne jo problem batayi usi ko saaf line me likho. Kuch invent mat karo.
Agar message me problem ki detail nahi hai (sirf "RMS raise karna hai" jaisa hai) to description null rakho.
Jo cheez message me nahi hai uski value null rakho.

Message: {message}"""

    try:
        new = ask_llm_json(prompt) or {}
    except RuntimeError:
        new = fallback_rms(message)

    category = new.get("category")
    if category in CATEGORIES and not details.get("category"):
        details["category"] = category

    if new.get("description") and not details.get("description"):
        details["description"] = message  # user ke apne shabd
    return {"details": details}


def check_node(state: RmsState):
    details = dict(state["details"])
    for key in FIELDS:
        if not details.get(key):
            return {"stage": "collecting", "reply": QUESTIONS[key], "details": details}
    if not details.get("subject"):
        polish(details)  # sirf ek baar chalta hai
    return {"stage": "confirming", "reply": _summary(details), "details": details}


def _summary(d):
    return (
        f"Ye RMS request ready hai:\n"
        f"- Category: {d['category']}\n- Subject: {d['subject']}\n- Description: {d['description_en']}\n\n"
        f"**Submit kar du? (haan / nahi)**"
    )


def build_graph():
    g = StateGraph(RmsState)
    g.add_node("extract", extract_node)
    g.add_node("check", check_node)
    g.set_entry_point("extract")
    g.add_edge("extract", "check")
    g.add_edge("check", END)
    return g.compile()


_graph = build_graph()

YES = {"haan", "han", "ha", "yes", "y", "ok", "submit", "kar do", "kardo", "confirm"}
NO = {"nahi", "nahin", "no", "n", "cancel", "mat karo"}


def run_rms_turn(student_id, message, session):
    """Ek turn chalata hai. session = {"details": {...}, "stage": ...}. Return: reply text."""
    text = re.sub(r"[^\w\s]", "", message.lower()).strip()

    # Confirmation: sirf haan/nahi, LLM nahi
    if session.get("stage") == "confirming":
        if text in YES:
            d = session["details"]
            full = d["description_en"]
            if full.strip() != d["description"].strip():
                full += f"\n\nStudent's original message: {d['description']}"
            result = create_rms_request(student_id, d["category"], d["subject"], full)
            session.clear()
            if result["success"]:
                return f"RMS request submit ho gayi. ID: {result['request_id']}"
            return f"Submit nahi hui: {result['message']}"
        if text in NO:
            session.clear()
            return "Theek hai, RMS request cancel kar di. Kuch aur chahiye?"
        return "Kripya sirf **haan** ya **nahi** likho."

    state = {
        "student_id": student_id,
        "message": message,
        "details": session.get("details", {}),
        "stage": "collecting",
        "reply": "",
    }
    try:
        out = _graph.invoke(state)
    except RuntimeError:
        return "AI abhi busy hai. Thodi der baad apna message dobara bhejo. (Tumhari ab tak ki details safe hain.)"
    session["details"] = out["details"]
    session["stage"] = out["stage"]
    return out["reply"]