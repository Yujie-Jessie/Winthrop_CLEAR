"""
dashboard_director.py — Director / Police dashboard
Both roles share this single full dashboard (6 tabs).
"""
import streamlit as st
import pandas as pd
from datetime import datetime

from helpers import DISPLAY_NAMES, hide_sensitive_columns, date_filter_ui, apply_date_filter, log_action
from db import hash_password
from ai_flagging import get_ai_flag


def render_director_dashboard(conn, user_id, user_role, username):
    """Full director/police dashboard. Called for both DIRECTOR and POLICE roles."""

    display_name = DISPLAY_NAMES.get(username, username)
    icon = ":material/shield:" if user_role == "POLICE" else ":material/monitor_heart:"
    st.title(f"{icon} {display_name} — Dashboard")

    # Stats
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
            n = sd.get(key, 0)
            st.markdown(f'<div class="stat-card {cls}"><div class="stat-num">{n}</div><div class="stat-label">{label}</div></div>', unsafe_allow_html=True)
    st.markdown("<br>", unsafe_allow_html=True)

    tab1, tab2, tab3, tab4, tab5, tab6 = st.tabs([
        ":material/list_alt: All Cases",
        ":material/fact_check: Review Cases",
        ":material/person_add: Assign Cases",
        ":material/task_alt: Final Review",
        ":material/group: Manage Users",
        ":material/history: Audit Log",
    ])

    # ── Tab 1: All Cases ───────────────────────────────────────────────
    with tab1:
        start, end = date_filter_ui(f"{user_role}_all")
        df = pd.read_sql_query("""
            SELECT c.case_id, c.call_number, c.case_type, c.call_timestamp,
                   c.call_reason, c.action, c.priority_level, c.call_taker,
                   c.call_source, c.jurisdiction, c.vicinity,
                   cl.name AS client, cl.phone, cl.ssn, cl.dob,
                   cl.oln, cl.insurance_co, cl.policy_no,
                   c.current_status, u.name AS created_by
            FROM cases c
            JOIN clients cl ON c.client_id = cl.client_id
            LEFT JOIN users u ON c.created_by = u.user_id
            ORDER BY c.call_timestamp DESC
        """, conn)
        df = apply_date_filter(df, start, end)
        df = hide_sensitive_columns(df, user_role)

        if df.empty:
            st.info("No cases in this date range.")
        else:
            c1, c2, c3 = st.columns(3)
            with c1:
                fs = st.selectbox("Status", ["All"] + sorted(df["current_status"].dropna().unique().tolist()), key=f"{user_role}_fs")
            with c2:
                fp = st.selectbox("Priority", ["All"] + sorted(df["priority_level"].dropna().unique().tolist()), key=f"{user_role}_fp")
            with c3:
                ft = st.selectbox("Case Type", ["All"] + sorted(df["case_type"].dropna().unique().tolist()), key=f"{user_role}_ft")
            filtered = df.copy()
            if fs != "All": filtered = filtered[filtered["current_status"] == fs]
            if fp != "All": filtered = filtered[filtered["priority_level"] == fp]
            if ft != "All": filtered = filtered[filtered["case_type"] == ft]
            st.dataframe(filtered, use_container_width=True, height=400)
            st.caption(f"Showing {len(filtered)} of {len(df)} cases")

            st.divider()
            st.markdown("**View Narrative**")
            if not filtered.empty:
                sel = st.selectbox("Select case",
                    filtered["case_id"].tolist(),
                    format_func=lambda cid: f"#{cid} — {filtered[filtered['case_id']==cid]['client'].values[0]}",
                    key=f"{user_role}_nar")
                _nar_cur = conn.cursor()
                _nar_cur.execute("SELECT narrative, call_reason, location FROM cases WHERE case_id=%s", (sel,))
                row = _nar_cur.fetchone()
                if row and row[0]:
                    st.info(f":material/location_on: **{row[2]}**\n\n**Reason:** {row[1]}\n\n{row[0]}")
                else:
                    st.caption("No narrative recorded.")

    # ── Tab 2: Review Cases ────────────────────────────────────────────
    with tab2:
        st.subheader("Pending Cases — AI-Assisted Review")
        st.caption("Claude analyses each case and recommends whether to flag. Only **Yes** and **Not Sure** cases are shown by default.")

        start_r, end_r = date_filter_ui(f"{user_role}_review")

        show_all = st.toggle("Show all cases (including AI-recommended No)", value=False, key=f"{user_role}_show_all")

        pending_df = pd.read_sql_query("""
            SELECT c.case_id, cl.name AS client, cl.phone,
                   c.case_type, c.call_reason, c.location,
                   c.priority_level, c.call_taker, c.call_timestamp,
                   c.narrative, c.ai_flag, c.ai_reason, u.name AS created_by
            FROM cases c
            JOIN clients cl ON c.client_id = cl.client_id
            LEFT JOIN users u ON c.created_by = u.user_id
            WHERE c.current_status = 'Pending' AND (c.bh_relevant IS TRUE OR c.bh_relevant IS NULL)
            ORDER BY c.priority_level ASC, c.call_timestamp ASC
        """, conn)
        pending_df = apply_date_filter(pending_df, start_r, end_r)

        if pending_df.empty:
            st.success(":material/check_circle: No pending cases.")
        else:
            # Run AI analysis for cases that don't have it yet
            needs_analysis = pending_df[pending_df["ai_flag"].isna()]
            if not needs_analysis.empty:
                with st.spinner(f"Analysing {len(needs_analysis)} case(s) with Claude..."):
                    for _, r in needs_analysis.iterrows():
                        get_ai_flag(
                            int(r["case_id"]), r["case_type"], r["call_reason"],
                            r["priority_level"], r["narrative"], conn
                        )
                # Reload with fresh AI data
                pending_df = pd.read_sql_query("""
                    SELECT c.case_id, cl.name AS client, cl.phone,
                           c.case_type, c.call_reason, c.location,
                           c.priority_level, c.call_taker, c.call_timestamp,
                           c.narrative, c.ai_flag, c.ai_reason, u.name AS created_by
                    FROM cases c
                    JOIN clients cl ON c.client_id = cl.client_id
                    LEFT JOIN users u ON c.created_by = u.user_id
                    WHERE c.current_status = 'Pending' AND (c.bh_relevant IS TRUE OR c.bh_relevant IS NULL)
                    ORDER BY c.priority_level ASC, c.call_timestamp ASC
                """, conn)
                pending_df = apply_date_filter(pending_df, start_r, end_r)

            # Filter unless show_all is toggled
            display_df = pending_df if show_all else pending_df[pending_df["ai_flag"].isin(["Yes", "Not Sure", None])]

            # Summary counts
            yes_count      = len(pending_df[pending_df["ai_flag"] == "Yes"])
            notsure_count  = len(pending_df[pending_df["ai_flag"] == "Not Sure"])
            no_count       = len(pending_df[pending_df["ai_flag"] == "No"])
            m1, m2, m3 = st.columns(3)
            m1.metric(":material/error: Flag: Yes",      yes_count)
            m2.metric(":material/help: Flag: Not Sure", notsure_count)
            m3.metric(":material/check_circle: Flag: No",       no_count)
            st.divider()

            if display_df.empty:
                st.info("No cases match the current filter.")
            else:
                ai_badge = {
                    "Yes":      ":material/error: **AI: Flag Yes**",
                    "Not Sure": ":material/help: **AI: Not Sure**",
                    "No":       ":material/check_circle: **AI: Flag No**",
                }
                pri_label = {"1": ":material/flag: Priority 1", "2": ":material/flag: Priority 2", "3": ":material/flag: Priority 3", "4": ":material/flag: Priority 4"}

                for _, row in display_df.iterrows():
                    cid  = int(row["case_id"])
                    pri  = str(row["priority_level"])
                    narr = row["narrative"] if row["narrative"] else "_No narrative recorded._"
                    ts   = str(row["call_timestamp"])[:16]
                    flag = row["ai_flag"] or "Not Sure"
                    reason = row["ai_reason"] or ""

                    with st.container():
                        # Row 1: ID + client + timestamp + location
                        r1a, r1b, r1c = st.columns([1, 3, 3])
                        with r1a:
                            st.markdown(f'### #{cid}')
                        with r1b:
                            st.markdown(f"**{row['client']}** &nbsp; `{row['phone']}`")
                        with r1c:
                            st.caption(f":material/schedule: {ts} &nbsp;&nbsp; :material/location_on: {row['location']}")

                        # Row 2: Type / Call Reason / Priority
                        r2a, r2b, r2c = st.columns([2, 3, 2])
                        with r2a:
                            st.markdown(f"**Type:** `{row['case_type']}`")
                        with r2b:
                            st.markdown(f"**Call Reason:** {row['call_reason']}")
                        with r2c:
                            st.markdown(f"**Priority:** {pri_label.get(pri, pri)}")

                        # Row 3: AI recommendation
                        badge = ai_badge.get(flag, ":material/help: **AI: Not Sure**")
                        if flag == "Yes":
                            st.error(f"{badge} — {reason}")
                        elif flag == "Not Sure":
                            st.warning(f"{badge} — {reason}")
                        else:
                            st.success(f"{badge} — {reason}")

                        # Row 4: Narrative
                        with st.expander(":material/list_alt: Narrative", expanded=True):
                            st.markdown(narr)

                        # Row 5: Note + Approve + Dismiss
                        a1, a2, a3 = st.columns([3, 1, 1])
                        with a1:
                            note_key = f"rev_note_{cid}_{user_role}"
                            st.text_input("Note", key=note_key,
                                          label_visibility="collapsed",
                                          placeholder="Add a review note (optional)...")
                        with a2:
                            if st.button(":material/check_circle: Approve", key=f"approve_{cid}_{user_role}",
                                         use_container_width=True, type="primary"):
                                _cur = conn.cursor()
                                _cur.execute("UPDATE cases SET current_status='Outreach Pending' WHERE case_id=%s", (cid,))
                                _cur = conn.cursor()
                                _cur.execute("INSERT INTO case_reviews (case_id, reviewed_by, decision, review_note) VALUES (%s,%s,%s,%s)",
                                             (cid, user_id, "Approve", st.session_state.get(note_key, "")))
                                log_action(conn, user_id, "APPROVE_CASE", f"Case {cid} approved by {username}")
                                st.rerun()
                        with a3:
                            if st.button(":material/cancel: Dismiss", key=f"dismiss_{cid}_{user_role}",
                                         use_container_width=True):
                                _cur = conn.cursor()
                                _cur.execute("UPDATE cases SET current_status='Dismissed' WHERE case_id=%s", (cid,))
                                _cur = conn.cursor()
                                _cur.execute("INSERT INTO case_reviews (case_id, reviewed_by, decision, review_note) VALUES (%s,%s,%s,%s)",
                                             (cid, user_id, "Dismiss", st.session_state.get(note_key, "")))
                                log_action(conn, user_id, "DISMISS_CASE", f"Case {cid} dismissed by {username}")
                                st.rerun()

                        st.divider()

    # ── Tab 3: Assign Cases ────────────────────────────────────────────
    with tab3:
        st.subheader("Assign Accepted Cases to Social Workers")
        start_a, end_a = date_filter_ui(f"{user_role}_assign")
        accepted_df = pd.read_sql_query("""
            SELECT c.case_id, cl.name AS client, cl.phone,
                   c.case_type, c.call_reason, c.priority_level, c.call_timestamp,
                   oc.contact_note AS outreach_note
            FROM cases c
            JOIN clients cl ON c.client_id = cl.client_id
            LEFT JOIN outreach_contacts oc ON c.case_id = oc.case_id
            WHERE c.current_status = 'Accepted'
            ORDER BY c.priority_level ASC, c.call_timestamp ASC
        """, conn)
        accepted_df = apply_date_filter(accepted_df, start_a, end_a)
        workers_df = pd.read_sql_query(
            "SELECT user_id, name FROM users WHERE role='SOCIAL_WORKER' AND is_active=1", conn)

        if accepted_df.empty:
            st.info("No accepted cases to assign.")
        elif workers_df.empty:
            st.warning("No active social workers.")
        else:
            st.dataframe(accepted_df, use_container_width=True, height=300)
            st.divider()
            ca1, ca2 = st.columns(2)
            with ca1:
                assign_id = st.selectbox("Case ID", accepted_df["case_id"].tolist(), key=f"{user_role}_asgn_case")
            with ca2:
                worker_name = st.selectbox("Assign to", workers_df["name"].tolist(), key=f"{user_role}_asgn_worker")
            if st.button(":material/check_circle: Confirm Assignment", type="primary", key=f"{user_role}_asgn_btn"):
                wid = workers_df[workers_df["name"] == worker_name]["user_id"].values[0]
                _cur = conn.cursor()
                _cur.execute("UPDATE cases SET current_status='Assigned' WHERE case_id=%s", (int(assign_id),))
                _cur = conn.cursor()
                _cur.execute("INSERT INTO assignments (case_id, worker_id, assigned_by, last_updated, progress_note) VALUES (%s,%s,%s,%s,%s)",
                             (int(assign_id), int(wid), user_id, datetime.now(), "Assigned"))
                log_action(conn, user_id, "ASSIGN_CASE", f"Case {assign_id} → {worker_name}")
                st.success(f"Case {assign_id} assigned to **{worker_name}**.")
                st.rerun()

    # ── Tab 4: Final Review ────────────────────────────────────────────
    with tab4:
        st.subheader("Final Review — Cases Awaiting Completion Approval")
        st.caption("Social workers have marked these cases complete. Approve to close, or send back for further work.")

        start_fr, end_fr = date_filter_ui(f"{user_role}_fr")

        fr_df = pd.read_sql_query("""
            SELECT c.case_id, cl.name AS client, cl.phone,
                   c.case_type, c.call_reason, c.location,
                   c.priority_level, c.call_timestamp,
                   a.progress_note, a.last_updated,
                   u.name AS assigned_worker
            FROM cases c
            JOIN clients cl ON c.client_id = cl.client_id
            JOIN assignments a ON c.case_id = a.case_id
            JOIN users u ON a.worker_id = u.user_id
            WHERE c.current_status = 'Pending Completion'
            ORDER BY a.last_updated DESC
        """, conn)
        fr_df = apply_date_filter(fr_df, start_fr, end_fr, col="last_updated")

        if fr_df.empty:
            st.success(":material/check_circle: No cases awaiting final review.")
        else:
            st.info(f"**{len(fr_df)}** case(s) awaiting your approval.")
            st.divider()

            for _, row in fr_df.iterrows():
                cid  = int(row["case_id"])
                ts   = str(row["call_timestamp"])[:16]
                upd  = str(row["last_updated"])[:16] if row["last_updated"] else "—"

                with st.container():
                    r1a, r1b, r1c = st.columns([1, 3, 3])
                    with r1a:
                        st.markdown(f"### #{cid}")
                    with r1b:
                        st.markdown(f"**{row['client']}** &nbsp; `{row['phone']}`")
                    with r1c:
                        st.caption(f":material/event: Call: {ts} &nbsp;&nbsp; :material/update: Updated: {upd}")

                    r2a, r2b, r2c = st.columns([2, 3, 2])
                    with r2a:
                        st.markdown(f"**Type:** `{row['case_type']}`")
                    with r2b:
                        st.markdown(f"**Call Reason:** {row['call_reason']}")
                    with r2c:
                        st.markdown(f"**Assigned to:** {row['assigned_worker']}")

                    with st.expander(":material/clinical_notes: SW Progress Note", expanded=True):
                        st.markdown(row["progress_note"] or "_No progress note recorded._")

                    a1, a2, a3 = st.columns([3, 1, 1])
                    with a1:
                        fb_key = f"fr_note_{cid}_{user_role}"
                        st.text_input("Note", key=fb_key,
                                      label_visibility="collapsed",
                                      placeholder="Add a closing note (optional)...")
                    with a2:
                        if st.button(":material/check_circle: Approve Close", key=f"fr_approve_{cid}_{user_role}",
                                     use_container_width=True, type="primary"):
                            _cur = conn.cursor()
                            _cur.execute("UPDATE cases SET current_status='Completed' WHERE case_id=%s", (cid,))
                            _cur = conn.cursor()
                            _cur.execute("INSERT INTO case_reviews (case_id, reviewed_by, decision, review_note) VALUES (%s,%s,%s,%s)",
                                         (cid, user_id, "Close Approved", st.session_state.get(fb_key, "")))
                            log_action(conn, user_id, "CLOSE_APPROVED", f"Case {cid} closed by {username}")
                            st.rerun()
                    with a3:
                        if st.button(":material/undo: Send Back", key=f"fr_sendback_{cid}_{user_role}",
                                     use_container_width=True):
                            _cur = conn.cursor()
                            _cur.execute("UPDATE cases SET current_status='Assigned' WHERE case_id=%s", (cid,))
                            _cur = conn.cursor()
                            _cur.execute("INSERT INTO case_reviews (case_id, reviewed_by, decision, review_note) VALUES (%s,%s,%s,%s)",
                                         (cid, user_id, "Sent Back", st.session_state.get(fb_key, "")))
                            log_action(conn, user_id, "CASE_SENT_BACK", f"Case {cid} sent back by {username}")
                            st.rerun()

                    st.divider()

    # ── Tab 5: Manage Users ────────────────────────────────────────────
    with tab5:
        st.subheader("All Users")
        df_users = pd.read_sql_query(
            "SELECT user_id, name, role, is_active, created_at FROM users", conn)
        st.dataframe(df_users, use_container_width=True)

        st.divider()
        st.subheader("Add New User")
        cu1, cu2, cu3 = st.columns(3)
        with cu1:
            new_name = st.text_input("Username", key=f"{user_role}_new_name")
        with cu2:
            new_pass = st.text_input("Password", type="password", key=f"{user_role}_new_pass")
        with cu3:
            new_role = st.selectbox("Role",
                ["SOCIAL_WORKER", "INTAKE", "OUTREACH_POLICE", "POLICE", "DIRECTOR"],
                key=f"{user_role}_new_role")
        if st.button(":material/add: Create User", key=f"{user_role}_create_user"):
            if new_name and new_pass:
                try:
                    _cur = conn.cursor()
                    _cur.execute("INSERT INTO users (name, password, role) VALUES (%s,%s,%s)",
                                 (new_name, hash_password(new_pass), new_role))
                    log_action(conn, user_id, "CREATE_USER", f"Created {new_name} ({new_role})")
                    st.success(f"User '{new_name}' created.")
                    st.rerun()
                except Exception:
                    st.error("Username already exists or an error occurred.")
            else:
                st.warning("Fill in all fields.")

        st.divider()
        st.subheader("Enable / Disable User")
        others = df_users[df_users["name"] != username]["name"].tolist()
        if others:
            target = st.selectbox("Select User", others, key=f"{user_role}_target")
            trow   = df_users[df_users["name"] == target].iloc[0]
            if trow["is_active"]:
                if st.button(f":material/block: Disable {target}", key=f"{user_role}_disable"):
                    _cur = conn.cursor()
                    _cur.execute("UPDATE users SET is_active=0 WHERE name=%s", (target,))
                    log_action(conn, user_id, "DISABLE_USER", target); st.warning(f"{target} disabled."); st.rerun()
            else:
                if st.button(f":material/check_circle: Enable {target}", key=f"{user_role}_enable"):
                    _cur = conn.cursor()
                    _cur.execute("UPDATE users SET is_active=1 WHERE name=%s", (target,))
                    log_action(conn, user_id, "ENABLE_USER", target); st.success(f"{target} enabled."); st.rerun()

    # ── Tab 6: Audit Log ───────────────────────────────────────────────
    with tab6:
        df_audit = pd.read_sql_query("""
            SELECT a.log_id, u.name AS username, a.action, a.detail, a.timestamp
            FROM audit_log a
            LEFT JOIN users u ON a.user_id = u.user_id
            ORDER BY a.timestamp DESC LIMIT 200
        """, conn)
        st.dataframe(df_audit, use_container_width=True, height=500)
