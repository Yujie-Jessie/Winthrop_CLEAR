"""
permissions.py — Role-based permissions
Central definition of what each role is allowed to do.
Change permissions here only.
"""
import streamlit as st

# POLICE gets the exact same permissions as DIRECTOR
_DIRECTOR_PERMS = {
    "view_all_cases": True,
    "review_cases":   True,
    "assign_case":    True,
    "create_case":    False,
    "update_case":    True,
    "view_reports":   True,
    "manage_users":   True,
    "view_audit_log": True,
    "outreach":       False,
}

PERMISSIONS = {
    "DIRECTOR":        _DIRECTOR_PERMS,
    "POLICE":          _DIRECTOR_PERMS,   # identical to DIRECTOR
    "OUTREACH_POLICE": {
        "view_all_cases": True,
        "review_cases":   True,
        "assign_case":    False,
        "create_case":    False,
        "update_case":    False,
        "view_reports":   False,
        "manage_users":   False,
        "view_audit_log": False,
        "outreach":       True,
    },
    "SOCIAL_WORKER": {
        "view_all_cases": False,
        "review_cases":   False,
        "assign_case":    False,
        "create_case":    False,
        "update_case":    True,
        "view_reports":   False,
        "manage_users":   False,
        "view_audit_log": False,
        "outreach":       False,
    },
    "INTAKE": {
        "view_all_cases": False,
        "review_cases":   False,
        "assign_case":    False,
        "create_case":    True,
        "update_case":    False,
        "view_reports":   False,
        "manage_users":   False,
        "view_audit_log": False,
        "outreach":       False,
    },
}


def can(role, action):
    return PERMISSIONS.get(role, {}).get(action, False)


def require_permission(role, action):
    if not can(role, action):
        st.markdown(
            '<div class="access-denied"><span class="material-symbols-outlined" '
            'style="vertical-align:-4px;font-size:18px;">lock</span> '
            "Access Denied — You don't have permission to perform this action.</div>",
            unsafe_allow_html=True,
        )
        st.stop()
