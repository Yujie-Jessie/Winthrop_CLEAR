"""
helpers.py — Shared utility functions + constants
Audit logging, sensitive-column hiding, date filtering, and post-login display names.
"""
import streamlit as st
import pandas as pd
from datetime import date

# Full display names shown after login (sidebar + dashboard titles)
DISPLAY_NAMES = {
    "dir_health": "Director of Public Health & Social Services",
    "dir_sw":     "Director of Social Worker",
    "police":     "Police",
    "outreach1":  "Outreach Officer",
    "intake1":    "Intake Officer",
    "worker1":    "Social Worker",
}


def log_action(conn, user_id, action, detail=""):
    _cur = conn.cursor()
    _cur.execute(
        "INSERT INTO audit_log (user_id, action, detail) VALUES (%s,%s,%s)",
        (user_id, action, detail),
    )


def can_view_sensitive_data(role):
    return role in ["DIRECTOR", "POLICE", "OUTREACH_POLICE"]


def hide_sensitive_columns(df, user_role):
    if not can_view_sensitive_data(user_role):
        for col in ["ssn", "dob", "oln", "insurance_co", "policy_no"]:
            if col in df.columns:
                df = df.drop(columns=[col])
    return df


def date_filter_ui(key_prefix):
    col1, col2 = st.columns(2)
    with col1:
        # Default the "From date" to the start of 2026
        start = st.date_input("From date", value=date(2026, 1, 1), key=f"{key_prefix}_start")
    with col2:
        end = st.date_input("To date", value=date.today(), key=f"{key_prefix}_end")
    return start, end


def apply_date_filter(df, start, end, col="call_timestamp"):
    if col not in df.columns or df.empty:
        return df
    df[col] = pd.to_datetime(df[col], errors="coerce")
    return df[(df[col].dt.date >= start) & (df[col].dt.date <= end)]
