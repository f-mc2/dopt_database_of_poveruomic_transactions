import streamlit as st

st.set_page_config(page_title="Database of Poveruomic Transactions", page_icon="\U0001F4B6", initial_sidebar_state="auto", layout="wide")
st.title("DoPT Finance Dashboard")
st.write("Use the sidebar to navigate between pages.")

if hasattr(st.sidebar, "page_link"):
    st.sidebar.page_link("pages/1_Home.py", label="Home")
