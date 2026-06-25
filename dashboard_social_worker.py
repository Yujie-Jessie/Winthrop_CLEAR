"""
dashboard_social_worker.py — Social Worker workspace
"""
import streamlit as st
import pandas as pd
from datetime import datetime

from helpers import date_filter_ui, apply_date_filter, log_action


def render_social_worker_dashboard(conn, user_id, user_role, username):
    st.title(":material/clinical_notes: Social Worker Workspace")
    tab1, tab2 = st.tabs([":material/folder_open: My Active Cases", ":material/task_alt: Completed Cases"])

    with tab1:
        s, e = date_filter_ui("sw_active")
        df_a = pd.read_sql_query("""
            SELECT c.case_id, cl.name AS client, c.case_type, c.call_reason,
                   c.location, c.priority_level, c.current_status,
                   a.progress_note, a.last_updated, c.call_timestamp
            FROM cases c JOIN assignments a ON c.case_id=a.case_id
            JOIN clients cl ON c.client_id=cl.client_id
            WHERE a.worker_id=%s AND c.current_status NOT IN ('Completed','Pending Completion')
            ORDER BY c.priority_level ASC
        """, conn, params=(user_id,))
        df_a = apply_date_filter(df_a, s, e)
        if df_a.empty:
            st.info("No active cases.")
        else:
            st.dataframe(df_a[["case_id","client","case_type","call_reason","location","priority_level","current_status"]],
                         use_container_width=True)
            st.divider()
            st.subheader("Update a Case")
            sel = st.selectbox("Select Case", df_a["case_id"].tolist())
            note = st.text_area("Progress Note")
            new_st = st.radio("New Status", ["In Progress","Pending Completion"], horizontal=True)
            if st.button(":material/save: Submit Update", type="primary"):
                if not note.strip():
                    st.warning("Add a progress note first.")
                else:
                    _cur = conn.cursor()
                    _cur.execute("UPDATE cases SET current_status=%s WHERE case_id=%s", (new_st, int(sel)))
                    _cur = conn.cursor()
                    _cur.execute("UPDATE assignments SET progress_note=%s, last_updated=%s WHERE case_id=%s AND worker_id=%s",
                                 (note, datetime.now(), int(sel), user_id))
                    log_action(conn, user_id, "UPDATE_CASE", f"Case {sel} → {new_st}"); st.success("Updated."); st.rerun()

    with tab2:
        s, e = date_filter_ui("sw_done")
        df_d = pd.read_sql_query("""
            SELECT c.case_id, cl.name AS client, c.case_type, c.call_reason,
                   c.location, a.progress_note, a.last_updated, c.call_timestamp,
                   c.current_status
            FROM cases c JOIN assignments a ON c.case_id=a.case_id
            JOIN clients cl ON c.client_id=cl.client_id
            WHERE a.worker_id=%s AND c.current_status IN ('Completed','Pending Completion')
            ORDER BY a.last_updated DESC
        """, conn, params=(user_id,))
        df_d = apply_date_filter(df_d, s, e)
        if df_d.empty:
            st.info("No completed cases.")
        else:
            st.dataframe(df_d, use_container_width=True)
            pending_c = len(df_d[df_d.get("current_status", pd.Series()) == "Pending Completion"]) if "current_status" in df_d.columns else 0
            done_c = len(df_d[df_d.get("current_status", pd.Series()) == "Completed"]) if "current_status" in df_d.columns else len(df_d)
            if pending_c:
                st.warning(f"⏳ {pending_c} case(s) awaiting director final review.")
            if done_c:
                st.success(f"🎉 {done_c} case(s) fully completed.")
