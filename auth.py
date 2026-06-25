"""
auth.py — Sidebar: login, logout, and the logged-in user's profile
"""
import streamlit as st
from db import get_db_connection, hash_password
from helpers import log_action, DISPLAY_NAMES


def render_sidebar():
    """Renders the sidebar (login form when logged out, profile + logout when logged in)."""
    with st.sidebar:
        st.markdown("## :material/monitor_heart: Health CMS")
        st.markdown("---")

        if not st.session_state.logged_in:
            st.markdown("### Sign In")
            login_name = st.text_input("Username", key="login_name")
            login_pass = st.text_input("Password", type="password", key="login_pass")

            if st.button("Login"):
                if login_name and login_pass:
                    conn = get_db_connection()
                    _lcur = conn.cursor()
                    _lcur.execute(
                        "SELECT user_id, name, role, is_active FROM users WHERE name=%s AND password=%s",
                        (login_name, hash_password(login_pass)),
                    )
                    row = _lcur.fetchone()
                    if row is None:
                        st.error("Invalid username or password.")
                    elif row[3] == 0:
                        st.error("Account is disabled. Contact your administrator.")
                    else:
                        st.session_state.logged_in = True
                        st.session_state.user_id   = row[0]
                        st.session_state.username  = row[1]
                        st.session_state.user_role = row[2]
                        conn2 = get_db_connection()
                        log_action(conn2, row[0], "LOGIN", f"User {row[1]} logged in")
                        conn2.close()
                        st.rerun()
                else:
                    st.warning("Please fill in both fields.")

            st.markdown("---")
            st.markdown("**Accounts**")
            st.markdown("""
| Username | Password | Role |
|---|---|---|
| dir_health | health123 | Director |
| dir_sw | sw123 | Director |
| police | police123 | Police |
| outreach1 | out123 | Outreach |
| intake1 | intake123 | Intake |
| worker1 | worker123 | Social Worker |
            """)

        else:
            badge_map = {
                "DIRECTOR":        "badge-director",
                "POLICE":          "badge-police",
                "OUTREACH_POLICE": "badge-outreach",
                "SOCIAL_WORKER":   "badge-worker",
                "INTAKE":          "badge-intake",
            }
            label_map = {
                "DIRECTOR":        "Director",
                "POLICE":          "Police",
                "OUTREACH_POLICE": "Outreach Police",
                "SOCIAL_WORKER":   "Social Worker",
                "INTAKE":          "Intake Officer",
            }
            display_name = DISPLAY_NAMES.get(st.session_state.username, st.session_state.username)
            badge_cls    = badge_map.get(st.session_state.user_role, "badge-worker")
            role_lbl     = label_map.get(st.session_state.user_role, st.session_state.user_role)

            st.markdown(f":material/person: **{display_name}**")
            st.markdown(f'<span class="role-badge {badge_cls}">{role_lbl}</span>', unsafe_allow_html=True)
            st.markdown("---")

            if st.button("Logout"):
                conn = get_db_connection()
                log_action(conn, st.session_state.user_id, "LOGOUT", f"User {st.session_state.username} logged out")
                for k in ["logged_in", "user_id", "username", "user_role"]:
                    st.session_state[k] = None
                st.session_state.logged_in = False
                st.rerun()
