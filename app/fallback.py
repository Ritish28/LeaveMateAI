import re
from datetime import date, timedelta

from app.rms_tools import CATEGORIES

TYPE_KEYWORDS = {
    "Medical": ["bukhar", "fever", "medical", "doctor", "sick", "tabiyat", "bimar", "hospital", "dawai"],
    "Family Emergency": ["emergency", "accident"],
    "Academic Event": ["hackathon", "academic", "conference", "competition", "workshop"],
    "Personal": ["shaadi", "function", "personal", "ghar", "trip", "wedding"],
}

CATEGORY_KEYWORDS = {
    "Attendance Issue": ["attendance", "present", "absent", "proxy"],
    "Academic Issue": ["marks", "result", "exam", "timetable", "grade", "backlog", "internal"],
    "Technical Problem": ["portal", "login", "ums", "upload", "payment", "password", "website", "error"],
    "Administrative Request": ["certificate", "noc", "id card", "hostel", "bonafide", "transcript", "receipt"],
}


def fallback_leave(message, today=None):
    """LLM ke bina leave details nikalta hai (simple rules)."""
    today = today or date.today()
    t = message.lower()
    out = {"leave_type": None, "start_date": None, "end_date": None, "reason": None}

    for leave_type, words in TYPE_KEYWORDS.items():
        if any(w in t for w in words):
            out["leave_type"] = leave_type
            break

    start = None
    iso = re.findall(r"\d{4}-\d{2}-\d{2}", t)
    if iso:
        out["start_date"] = iso[0]
        if len(iso) > 1:
            out["end_date"] = iso[1]
    elif re.search(r"\bparso\b|day after tomorrow", t):
        start = today + timedelta(days=2)
    elif re.search(r"\bkal\b|tomorrow", t):
        start = today + timedelta(days=1)
    elif re.search(r"\baaj\b|today", t):
        start = today

    if start:
        out["start_date"] = start.isoformat()

    if out["start_date"] and not out["end_date"]:
        days = re.search(r"(\d+)\s*(?:din|day|days)", t)
        has_from = re.search(r"\b(from|se)\b", t)
        base = start or date.fromisoformat(out["start_date"]) if re.fullmatch(r"\d{4}-\d{2}-\d{2}", out["start_date"]) else None
        if days and base:
            out["end_date"] = (base + timedelta(days=int(days.group(1)) - 1)).isoformat()
        elif not has_from:
            out["end_date"] = out["start_date"]

    reason = re.search(r"(?:kyunki|kyuki|because|due to)\s+(.+)", message, re.IGNORECASE)
    if reason:
        out["reason"] = reason.group(1).strip()
    elif out["leave_type"] == "Medical":
        out["reason"] = message.strip()

    return out


def fallback_rms(message):
    """LLM ke bina RMS category aur description nikalta hai."""
    t = message.lower()
    out = {"category": None, "description": None}
    for category in CATEGORIES:
        if any(w in t for w in CATEGORY_KEYWORDS[category]):
            out["category"] = category
            out["description"] = message.strip()  # keyword mila matlab problem batayi gayi hai
            break
    return out