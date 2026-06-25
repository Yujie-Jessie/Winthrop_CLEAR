"""
app.py — Main entry point (the file you run)

Run it the same way as before:   streamlit run app.py

This file only does the "wiring":
  set up the page -> inject styles -> init the database -> handle login
  -> route the user to the dashboard for their role.
All the actual logic lives in the individual module files.
"""
import streamlit as st

from styles import inject_css
from db import init_db, get_db_connection
from auth import render_sidebar
from dashboard_director import render_director_dashboard
from dashboard_outreach import render_outreach_dashboard
from dashboard_intake import render_intake_dashboard
from dashboard_social_worker import render_social_worker_dashboard

# ── Page config (must be the first Streamlit call) ───────────────────
st.set_page_config(
    page_title="Public Health Case Management",
    page_icon=":material/monitor_heart:",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ── Inject global CSS ────────────────────────────────────────────────
inject_css()

# ── Initialize the database (creates tables + seed accounts on first run)
try:
    init_db()
except Exception as e:
    st.error(f"DB init error: {e}")
    st.stop()

# ── Session state defaults ───────────────────────────────────────────
if "logged_in" not in st.session_state:
    st.session_state.logged_in = False
    st.session_state.user_id   = None
    st.session_state.username  = None
    st.session_state.user_role = None

# ── Sidebar (login / logout) ─────────────────────────────────────────
render_sidebar()

# ── Not logged in: show the landing page and stop ────────────────────
if not st.session_state.logged_in:
    st.markdown("""
    <div style="text-align:center;padding:80px 0;">
      <h1 style="font-size:48px;"><span class="material-symbols-outlined" style="font-size:56px;color:#1565C0;">monitor_heart</span></h1>
      <h2 style="color:#1a1a2e;">Public Health Case Management</h2>
      <p style="color:#6b7280;">Please sign in using the sidebar to continue.</p>
    </div>""", unsafe_allow_html=True)
    st.stop()

# ── Logged in: pull the current user's info + a DB connection ─────────
user_id   = st.session_state.user_id
user_role = st.session_state.user_role
username  = st.session_state.username
conn      = get_db_connection()

# ── Routing: dispatch to the dashboard for the user's role ───────────
if user_role in ("DIRECTOR", "POLICE"):
    render_director_dashboard(conn, user_id, user_role, username)
elif user_role == "OUTREACH_POLICE":
    render_outreach_dashboard(conn, user_id, user_role, username)
elif user_role == "INTAKE":
    render_intake_dashboard(conn, user_id, user_role, username)
elif user_role == "SOCIAL_WORKER":
    render_social_worker_dashboard(conn, user_id, user_role, username)
