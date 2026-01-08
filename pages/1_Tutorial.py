import streamlit as st

from src import session_state, ui_widgets

session_state.ensure_db_session_state()
ui_widgets.render_sidebar_nav()

st.title("Tutorial")
st.write(
    "This page will include a short tutorial and a comparison logic explainer in a later step."
)
