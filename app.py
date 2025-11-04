import streamlit as st
from utils.auth import check_credentials
import evidence_analysis_page
import streamlit.components.v1 as components

st.set_page_config(page_title="Login", layout="wide", initial_sidebar_state="collapsed")

# Initialize login state if not already present
if "logged_in" not in st.session_state:
    st.session_state["logged_in"] = False

if "show_reports" not in st.session_state:
    st.session_state["show_reports"] = False

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

def show_reports():
    """Display the HTML report page with navigation"""
    # Header with navigation
    col1, col2, col3 = st.columns([1, 6, 1])
    
    with col1:
        if st.button("← Back to Analysis", key="back_btn"):
            st.session_state["show_reports"] = False
            st.rerun()
    
    with col2:
        st.markdown("<h2 style='text-align: center;'>📊 MIP Evidence Reports</h2>", unsafe_allow_html=True)
    
    with col3:
        if st.button("🚪 Logout", key="logout_btn"):
            st.session_state.clear()
            st.rerun()
    
    # Colored horizontal line
    st.markdown("""
        <hr style='border: 2px solid #0f4c81; margin-top: 10px; margin-bottom: 20px;' />
    """, unsafe_allow_html=True)
    
    # Hide menu and footer
    st.markdown("""
        <style>
            #MainMenu {visibility: hidden;}
            footer {visibility: hidden;}
        </style>
    """, unsafe_allow_html=True)
    
    # Read and display the HTML file
    try:
        with open("report.html", "r", encoding="utf-8") as f:
            html_content = f.read()
        
        # Display the HTML content
        components.html(html_content, height=1200, scrolling=True)
        
    except FileNotFoundError:
        st.error("report.html file not found. Please ensure the file exists in the same directory.")
    except Exception as e:
        st.error(f"Error loading report: {str(e)}")

# Show login, evidence analysis page, or reports
if not st.session_state["logged_in"]:
    login()
else:
    if st.session_state["show_reports"]:
        show_reports()
    else:
        evidence_analysis_page.show()
