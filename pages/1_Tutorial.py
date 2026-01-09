import streamlit as st

from src import session_state, ui_widgets

st.set_page_config(
    page_title="Tutorial",
    page_icon="\U0001F4B6",
    initial_sidebar_state="auto",
    layout="wide",
)

session_state.ensure_db_session_state()
ui_widgets.render_sidebar_nav()

st.title("Tutorial")
st.write(
    "This page will include a short tutorial and a comparison logic explainer in a later step."
)
