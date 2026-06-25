"""
dashboard_intake.py — Intake Officer dashboard (new-case entry)
"""
import streamlit as st
import pandas as pd
from datetime import datetime, date

from helpers import date_filter_ui, apply_date_filter, log_action


def render_intake_dashboard(conn, user_id, user_role, username):
    st.title(":material/phone_in_talk: Intake Officer — New Case Entry")

    with st.form("intake_form"):
        st.subheader("Client Information")
        c1, c2 = st.columns(2)
        with c1: client_name  = st.text_input("Client Name *")
        with c2: client_phone = st.text_input("Phone Number")
        c3, c4, c5 = st.columns(3)
        with c3: client_ssn  = st.text_input("SSN")
        with c4: client_dob  = st.date_input("Date of Birth", value=date.today())
        with c5: client_race = st.selectbox("Race", ["","White","Black","Hispanic","Asian","Native American","Other"])
        c6, c7, c8 = st.columns(3)
        with c6: client_sex      = st.radio("Sex", ["M","F","Other"], horizontal=True)
        with c7: client_oln      = st.text_input("Driver License Number")
        with c8: client_insurance = st.text_input("Insurance Company")
        client_policy = st.text_input("Policy Number")

        st.subheader("Case Details")
        c9, c10 = st.columns(2)
        with c9:
            call_number = st.text_input("Call Number")
            case_type   = st.selectbox("Case Type *", [
                "","Wellness Check","Mental Health","Substance Use",
                "Domestic Violence","Homelessness",
                "Juvenile - Alcohol/Substance","Juvenile - Mental Health","Other"])
            call_reason = st.text_area("Call Reason *")
            narrative   = st.text_area("Narrative / Notes")
        with c10:
            location     = st.text_input("Location / Address")
            vicinity     = st.text_input("Vicinity / Area")
            jurisdiction = st.text_input("Jurisdiction", value="WINTHROP")
            action       = st.text_input("Action")
            call_taker   = st.text_input("Call Taker Name")
            call_source  = st.selectbox("Call Source", ["","Telephone Call","911","Radio","Initiated","Walk-In","Other"])
            priority     = st.selectbox("Call Priority *", ["1 - Critical","2 - High","3 - Medium","4 - Low"])
        c11, c12 = st.columns(2)
        with c11: call_date = st.date_input("Call Date *", value=date.today())
        with c12: call_time = st.time_input("Call Time *", value=datetime.now().time())
        submitted = st.form_submit_button(":material/assignment: Submit Case", type="primary")

    if submitted:
        if not client_name or not call_reason or case_type == "":
            st.error("Client name, case type, and call reason are required.")
        else:
            _cur = conn.cursor()
            _cur.execute("SELECT client_id FROM clients WHERE name=%s AND phone=%s",
                               (client_name, client_phone))

            row = _cur.fetchone()
            if row:
                client_id = row[0]
                _cur = conn.cursor()
                _cur.execute("UPDATE clients SET ssn=%s,dob=%s,race=%s,sex=%s,oln=%s,insurance_co=%s,policy_no=%s WHERE client_id=%s",
                             (client_ssn, client_dob.strftime("%Y-%m-%d"), client_race, client_sex,
                              client_oln, client_insurance, client_policy, client_id))
            else:
                _cur = conn.cursor()
                _ins2_cur = conn.cursor()
                _ins2_cur.execute("INSERT INTO clients (name,phone,ssn,dob,race,sex,oln,insurance_co,policy_no) VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s) RETURNING client_id",
                                   (client_name, client_phone, client_ssn, client_dob.strftime("%Y-%m-%d"),
                                    client_race, client_sex, client_oln, client_insurance, client_policy))
                client_id = _ins2_cur.fetchone()[0]

            pri_short = priority.split(" - ")[0]
            call_ts = datetime.combine(call_date, call_time).strftime("%Y-%m-%d %H:%M")
            _cur = conn.cursor()
            _cur.execute("""
                INSERT INTO cases (client_id, call_number, case_type, call_timestamp, location,
                    call_reason, action, priority_level, call_taker, call_source,
                    jurisdiction, vicinity, narrative, current_status, created_by)
                VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,'Pending',%s)
            """, (client_id, call_number, case_type, call_ts, location, call_reason, action,
                  pri_short, call_taker, call_source, jurisdiction, vicinity, narrative, user_id))
            log_action(conn, user_id, "CREATE_CASE", f"New case for '{client_name}' — {case_type}")
            st.success(":material/check_circle: Case submitted. Pending review.")

    st.divider()
    st.subheader("My Submitted Cases")
    s, e = date_filter_ui("intake_my")
    df_my = pd.read_sql_query("""
        SELECT c.case_id, c.call_number, c.case_type, cl.name AS client,
               c.call_reason, c.priority_level, c.current_status, c.call_timestamp
        FROM cases c JOIN clients cl ON c.client_id=cl.client_id
        WHERE c.created_by=%s ORDER BY c.call_timestamp DESC
    """, conn, params=(user_id,))
    df_my = apply_date_filter(df_my, s, e)
    if df_my.empty:
        st.info("No cases in this date range.")
    else:
        st.dataframe(df_my, use_container_width=True)
        st.caption(f"{len(df_my)} case(s)")
