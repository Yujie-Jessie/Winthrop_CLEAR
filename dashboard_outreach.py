"""
dashboard_outreach.py — Outreach Police dashboard
"""
import streamlit as st
import pandas as pd

from helpers import hide_sensitive_columns, date_filter_ui, apply_date_filter, log_action


def render_outreach_dashboard(conn, user_id, user_role, username):
    st.title(":material/cell_tower: Outreach Police Dashboard")

    _cur = conn.cursor()
    _cur.execute("SELECT current_status, COUNT(*) FROM cases GROUP BY current_status")
    stats = _cur.fetchall()
    sd = {r[0]: r[1] for r in stats}
    cols = st.columns(6)
    for col, (cls, label, key) in zip(cols, [
        ("pending",   "Pending",            "Pending"),
        ("outreach",  "Outreach Pending",   "Outreach Pending"),
        ("accepted",  "Accepted",           "Accepted"),
        ("assigned",  "Assigned",           "Assigned"),
        ("done",      "Pending Completion", "Pending Completion"),
        ("dismissed", "Completed",          "Completed"),
    ]):
        with col:
            n2 = sd.get(key, 0)
            st.markdown(f'<div class="stat-card {cls}"><div class="stat-num">{n2}</div><div class="stat-label">{label}</div></div>', unsafe_allow_html=True)
    st.markdown("<br>", unsafe_allow_html=True)

    tab1, tab2, tab3, tab4, tab5 = st.tabs([
        ":material/list_alt: All Cases", ":material/inbox: Outreach Queue", ":material/call: Log Contact", ":material/folder: Contact History", ":material/search: Case Progress"])

    with tab1:
        s, e = date_filter_ui("op_all")
        df_all = pd.read_sql_query("""
            SELECT c.case_id, c.call_number, c.case_type, c.call_timestamp,
                   c.call_reason, c.action, c.priority_level, c.call_taker, c.call_source,
                   cl.name AS client, cl.ssn, cl.dob, cl.oln, cl.insurance_co, cl.policy_no,
                   c.current_status, u.name AS created_by
            FROM cases c JOIN clients cl ON c.client_id=cl.client_id
            LEFT JOIN users u ON c.created_by=u.user_id
            ORDER BY c.call_timestamp DESC
        """, conn)
        df_all = apply_date_filter(df_all, s, e)
        df_all = hide_sensitive_columns(df_all, user_role)
        if df_all.empty:
            st.info("No cases.")
        else:
            f1, f2 = st.columns(2)
            with f1:
                fs = st.selectbox("Status", ["All"] + sorted(df_all["current_status"].dropna().unique().tolist()), key="op_fs")
            with f2:
                fp = st.selectbox("Priority", ["All"] + sorted(df_all["priority_level"].dropna().unique().tolist()), key="op_fp")
            flt = df_all.copy()
            if fs != "All": flt = flt[flt["current_status"] == fs]
            if fp != "All": flt = flt[flt["priority_level"] == fp]
            st.dataframe(flt, use_container_width=True, height=400)
            st.caption(f"Showing {len(flt)} of {len(df_all)}")

    with tab2:
        st.subheader("Cases Awaiting Outreach Contact")
        s, e = date_filter_ui("op_queue")
        q = pd.read_sql_query("""
            SELECT c.case_id, cl.name AS client, cl.phone,
                   c.case_type, c.call_reason, c.location, c.priority_level, c.call_timestamp
            FROM cases c JOIN clients cl ON c.client_id=cl.client_id
            WHERE c.current_status IN ('Outreach Pending','Callback')
            ORDER BY c.priority_level ASC, c.call_timestamp ASC
        """, conn)
        q = apply_date_filter(q, s, e)
        if not q.empty:
            st.dataframe(q, use_container_width=True, height=420)
        else:
            st.info("Queue empty.")

    with tab3:
        st.subheader("Log a Contact Attempt")
        cdf = pd.read_sql_query("""
            SELECT c.case_id, cl.name AS client, cl.phone, c.case_type, c.call_reason
            FROM cases c JOIN clients cl ON c.client_id=cl.client_id
            WHERE c.current_status IN ('Outreach Pending','Callback') ORDER BY c.case_id
        """, conn)
        if cdf.empty:
            st.info("No cases available.")
        else:
            sel = st.selectbox("Select Case", cdf["case_id"].tolist(),
                format_func=lambda cid: f"Case {cid} — {cdf[cdf['case_id']==cid]['client'].values[0]}",
                key="op_sel")
            r = cdf[cdf["case_id"]==sel].iloc[0]
            st.markdown(f"> **{r['client']}** | {r['phone']} | {r['case_type']} | {r['call_reason']}")
            st.divider()
            outcome = st.radio("Outcome", ["Accepted","Refused","Callback"], horizontal=True, key="op_outcome")
            st.info({"Accepted":":material/check_circle: Client agreed.","Refused":":material/cancel: Client declined.","Callback":":material/undo: No answer — revisit."}[outcome])
            cnote = st.text_area("Contact Note (required)", key="op_note")
            if st.button(":material/save: Submit", type="primary", key="op_submit"):
                if not cnote.strip():
                    st.warning("Note required.")
                else:
                    _cur = conn.cursor()
                    _cur.execute("UPDATE cases SET current_status=%s WHERE case_id=%s", (outcome, int(sel)))
                    _cur = conn.cursor()
                    _cur.execute("INSERT INTO outreach_contacts (case_id,officer_id,outcome,contact_note) VALUES (%s,%s,%s,%s)",
                                 (int(sel), user_id, outcome, cnote))
                    log_action(conn, user_id, "OUTREACH_RESULT", f"Case {sel} → {outcome}"); st.success(f"Case {sel} → **{outcome}**"); st.rerun()

    with tab4:
        st.subheader("My Contact History")
        h = pd.read_sql_query("""
            SELECT oc.contact_id, c.case_id, cl.name AS client, cl.phone,
                   oc.outcome, oc.contact_note, oc.contacted_at
            FROM outreach_contacts oc
            JOIN cases c ON oc.case_id=c.case_id JOIN clients cl ON c.client_id=cl.client_id
            WHERE oc.officer_id=%s ORDER BY oc.contacted_at DESC
        """, conn, params=(user_id,))
        if h.empty:
            st.info("No history yet.")
        else:
            st.dataframe(h, use_container_width=True, height=450)
            c1, c2, c3 = st.columns(3)
            c1.metric("Accepted", len(h[h["outcome"]=="Accepted"]))
            c2.metric("Refused",  len(h[h["outcome"]=="Refused"]))
            c3.metric("Callback", len(h[h["outcome"]=="Callback"]))

    with tab5:
        st.subheader("Track Case Progress")
        all_c = pd.read_sql_query("""
            SELECT c.case_id, cl.name AS client, c.current_status, c.priority_level, c.call_timestamp
            FROM cases c JOIN clients cl ON c.client_id=cl.client_id ORDER BY c.case_id DESC
        """, conn)
        if not all_c.empty:
            tid = st.selectbox("Select Case", all_c["case_id"].tolist(), key="op_track")
            _det_cur = conn.cursor()
            _det_cur.execute("""
                SELECT c.case_id, cl.name, cl.phone, c.call_reason, c.location,
                       c.priority_level, c.current_status, c.call_timestamp, u.name
                FROM cases c JOIN clients cl ON c.client_id=cl.client_id
                LEFT JOIN users u ON c.created_by=u.user_id WHERE c.case_id=%s
            """, (tid,))
            det = _det_cur.fetchone()
            if det:
                st.markdown(f"**Case #{det[0]}** | Status: **{det[6]}** | Priority: {det[5]}")
                st.markdown(f"**Client:** {det[1]} | {det[2]} | **Location:** {det[4]}")
                st.markdown(f"**Reason:** {det[3]}")
                st.divider()
                _con_cur = conn.cursor()
                _con_cur.execute(
                    "SELECT outcome, contact_note, contacted_at FROM outreach_contacts WHERE case_id=%s ORDER BY contacted_at DESC",
                    (tid,))
                contacts = _con_cur.fetchall()
                if contacts:
                    for o, n, t in contacts:
                        st.info(f"**{o}** ({t}) — {n}")
                else:
                    st.caption("No contact attempts yet.")
                _asgn_cur = conn.cursor()
                _asgn_cur.execute("""
                    SELECT a.progress_note, a.last_updated, u.name FROM assignments a
                    LEFT JOIN users u ON a.worker_id=u.user_id WHERE a.case_id=%s
                """, (tid,))
                asgn = _asgn_cur.fetchone()
                st.divider()
                if asgn:
                    st.info(f"**Assigned to:** {asgn[2]} | **Updated:** {asgn[1]}\n\n{asgn[0]}")
                else:
                    st.caption("Not yet assigned to a social worker.")
