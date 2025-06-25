import streamlit as st
from utils.auth import check_credentials
import evidence_analysis_page

st.set_page_config(page_title="Login", layout="centered")

# Initialize login state if not already present
if "logged_in" not in st.session_state:
    st.session_state["logged_in"] = False

def login():
    st.title("🔐 Login Page")
    st.markdown("<br>", unsafe_allow_html=True)

    with st.form("login_form"):
        username = st.text_input("Username")
        password = st.text_input("Password", type="password")
        submitted = st.form_submit_button("Login")

        if submitted:
            if check_credentials(username, password):
                st.session_state["logged_in"] = True
                st.success("Login successful!")
                st.rerun()
            else:
                st.error("Invalid username or password")

# Show login or evidence analysis page
if not st.session_state["logged_in"]:
    login()
else:
    evidence_analysis_page.show()
