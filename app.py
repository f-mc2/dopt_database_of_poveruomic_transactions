import streamlit as st

st.set_page_config(page_title="DOPT Finance", layout="wide")
st.title("DOPT Finance Dashboard")
st.write("Use the sidebar to navigate between pages.")

if hasattr(st.sidebar, "page_link"):
    st.sidebar.page_link("pages/1_Home.py", label="Home")
