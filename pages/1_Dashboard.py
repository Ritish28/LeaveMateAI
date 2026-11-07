import pandas as pd
import streamlit as st

from app.db import get_connection, setup_database
from app.leave_tools import get_my_leaves
from app.rms_tools import get_my_requests

setup_database()

st.set_page_config(page_title="Dashboard - LeaveMate AI", page_icon="📊", layout="wide")
st.title("📊 Student Dashboard")
st.caption("Demo version: fictional students aur fictional data")


def load_students():
    conn = get_connection()
    rows = conn.execute("SELECT * FROM students ORDER BY id").fetchall()
    conn.close()
    return [dict(r) for r in rows]


students = load_students()
names = {f"{s['name']} ({s['reg_no']})": s for s in students}
choice = st.sidebar.selectbox("Demo student", list(names.keys()), key="dash_student")
student = names[choice]

c1, c2, c3, c4 = st.columns(4)
c1.metric("Naam", student["name"])
c2.metric("Reg No", student["reg_no"])
c3.metric("Program", student["program"])
c4.metric("Section", student["section"])

rms = get_my_requests(student["id"])
leaves = get_my_leaves(student["id"])


def count(items, status):
    return sum(1 for i in items if i["status"] == status)


st.subheader("Status summary")
m1, m2, m3, m4 = st.columns(4)
m1.metric("RMS total", len(rms))
m2.metric("RMS Pending", count(rms, "Pending"))
m3.metric("Leave total", len(leaves))
m4.metric("Leave Pending", count(leaves, "Pending"))

tab1, tab2, tab3 = st.tabs(["RMS requests", "Leave applications", "Status tracking"])

with tab1:
    if rms:
        df = pd.DataFrame(rms)[["id", "category", "subject", "status", "created_at"]]
        st.dataframe(df, width="stretch", hide_index=True)
    else:
        st.info("Abhi koi RMS request nahi hai.")

with tab2:
    if leaves:
        df = pd.DataFrame(leaves)[["id", "leave_type", "start_date", "end_date", "reason", "status", "created_at"]]
        st.dataframe(df, width="stretch", hide_index=True)
    else:
        st.info("Abhi koi leave application nahi hai.")

with tab3:
    kind = st.radio("Kya track karna hai?", ["RMS", "Leave"], horizontal=True)
    items = rms if kind == "RMS" else leaves
    if not items:
        st.info("Track karne ke liye abhi kuch nahi hai.")
    else:
        pick = st.selectbox("Request ID", [i["id"] for i in items])
        item = next(i for i in items if i["id"] == pick)
        st.write(f"**{kind} #{item['id']}** ka status: **{item['status']}**")
        st.write(f"Banai gayi: {item['created_at']}")
        if item["status"] == "Pending":
            st.progress(0.5)
            st.caption("Submitted → **Pending** → Approved / Rejected")
        elif item["status"] == "Cancelled":
            st.progress(1.0)
            st.caption("Submitted → Pending → **Cancelled**")
        else:
            st.progress(1.0)
            st.caption(f"Submitted → Pending → **{item['status']}**")