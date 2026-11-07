import streamlit as st

st.set_page_config(page_title="LeaveMate AI", page_icon="🎓")

st.title("🎓 LeaveMate AI")
st.write("Hello! Mera pehla Streamlit page chal raha hai.")

name = st.text_input("Tumhara naam kya hai?")
if name:
    st.success(f"Namaste {name}! LeaveMate AI me swagat hai.")