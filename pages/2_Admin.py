import pandas as pd
import streamlit as st

from app.admin_tools import NEW_STATUSES, list_all, set_status
from app.db import setup_database

setup_database()

st.set_page_config(page_title="Admin (Demo) - LeaveMate AI", page_icon="🛠️", layout="wide")
st.title("🛠️ Demo Admin Panel")
st.warning("Ye sirf demo ke liye hai: asli university me admin alag system se approve karta hai.")

kind = st.radio("Kya dekhna hai?", ["RMS", "Leave"], horizontal=True)
items = list_all(kind)

if not items:
    st.info("Abhi koi entry nahi hai.")
else:
    df = pd.DataFrame(items)
    cols = ["id", "student_name", "reg_no", "status", "created_at"]
    cols.insert(3, "category" if kind == "RMS" else "leave_type")
    st.dataframe(df[cols], width="stretch", hide_index=True)

    pending = [i for i in items if i["status"] == "Pending"]
    st.subheader("Status badlo")
    if not pending:
        st.info("Koi Pending request nahi hai.")
    else:
        pick = st.selectbox("Pending request ID", [i["id"] for i in pending])
        new_status = st.selectbox("Naya status", NEW_STATUSES)
        if st.button("Update status"):
            result = set_status(kind, pick, new_status)
            if result["success"]:
                st.success(result["message"])
                st.rerun()
            else:
                st.error(result["message"])