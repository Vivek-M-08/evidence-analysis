import streamlit as st
from utils.auth import check_credentials
import evidence_analysis_page
import thematic_analysis_page
import story_rating_page
import streamlit.components.v1 as components

# --- CONSTANTS FOR NAVIGATION ---
PAGE_EVIDENCE_ANALYSIS = "Evidence Analysis"
PAGE_THEMATIC_ANALYSIS = "Thematic Analysis"
PAGE_STORY_RATING = "Story Ranker"
NAVIGATABLE_PAGES = [PAGE_EVIDENCE_ANALYSIS, PAGE_THEMATIC_ANALYSIS, PAGE_STORY_RATING]

# Set page configuration (Must be the first Streamlit command)
st.set_page_config(page_title="Evidence Validator", layout="wide", initial_sidebar_state="collapsed")

# --- INITIALIZE SESSION STATE ---
if "logged_in" not in st.session_state:
    st.session_state["logged_in"] = False

if "show_reports" not in st.session_state:
    st.session_state["show_reports"] = False

if "current_page" not in st.session_state:
    st.session_state["current_page"] = PAGE_EVIDENCE_ANALYSIS

def login():
    """Displays the login form."""
    st.title("🔐 Login Page")
    st.markdown("<br>", unsafe_allow_html=True)

    with st.form("login_form"):
        username = st.text_input("Username")
        password = st.text_input("Password", type="password")
        submitted = st.form_submit_button("Login")

        if submitted:
            # Assuming utils.auth is accessible in the environment
            if check_credentials(username, password):
                st.session_state["logged_in"] = True
                st.success("Login successful!")
                st.rerun()
            else:
                st.error("Invalid username or password")

def show_reports():
    """Display the HTML report page with navigation."""
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
    
    # Hide default Streamlit elements
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

# --- MAIN APPLICATION LOGIC ---

if not st.session_state["logged_in"]:
    login()
else:
    if st.session_state["show_reports"]:
        show_reports()
    else:
        # --- TOP NAVIGATION BAR ---
        nav_col1, nav_col2, nav_col3 = st.columns([1, 2, 1])
        
        with nav_col1:
            # Dropdown Navigation/SG Voice Menu
            page_select_options = [
                PAGE_EVIDENCE_ANALYSIS, 
                PAGE_THEMATIC_ANALYSIS, 
                PAGE_STORY_RATING,
                "Action Step (Coming Soon)",
                "Extract Data (Coming Soon)",
            ]
            
            # Find current page index for default selection
            try:
                default_index = page_select_options.index(st.session_state["current_page"])
            except ValueError:
                default_index = 0

            current_selection = st.selectbox(
                "Navigate",
                options=page_select_options,
                index=default_index,
                key="page_nav_selectbox",
                label_visibility="collapsed"
            )

            # Update the page state if a new navigatable page is selected
            if current_selection != st.session_state["current_page"] and current_selection in NAVIGATABLE_PAGES:
                st.session_state["current_page"] = current_selection
                st.rerun()
                
        with nav_col2:
            st.markdown(f"<h2 style='text-align: center;'>{st.session_state['current_page']}</h2>", unsafe_allow_html=True)

        with nav_col3:
            st.markdown("<div style='text-align: right;'>", unsafe_allow_html=True)
            
            # Buttons (Reports and Logout - shown conditionally/with different keys)
            btn_col1, btn_col2 = st.columns(2)
            
            with btn_col1:
                if st.session_state["current_page"] == PAGE_EVIDENCE_ANALYSIS:
                    if st.button("📊 Reports", key="reports_btn_nav"):
                        st.session_state["show_reports"] = True
                        st.rerun()
                else:
                    # Placeholder for other page actions if needed
                    pass
            
            with btn_col2:
                if st.button("🚪 Logout", key="logout_btn_nav_all"):
                    st.session_state.clear()
                    st.rerun()
            
            st.markdown("</div>", unsafe_allow_html=True)
            
        # Colored horizontal line
        st.markdown("""
            <hr style='border: 2px solid #0f4c81; margin-top: 10px; margin-bottom: 20px;' />
        """, unsafe_allow_html=True)
        
        
        # --- RENDER SELECTED PAGE CONTENT ---
        if st.session_state["current_page"] == PAGE_EVIDENCE_ANALYSIS:
            evidence_analysis_page.show()
        elif st.session_state["current_page"] == PAGE_THEMATIC_ANALYSIS:
            thematic_analysis_page.show()
        elif st.session_state["current_page"] == PAGE_STORY_RATING:
            story_rating_page.show()
        else:
            # Placeholder for Coming Soon Pages
            st.info(f"Page: {st.session_state['current_page']} is coming soon!")