"""
styles.py — Global CSS styling
All visual styling (colors, cards, badges, sidebar, tabs, etc.) lives here.
Change the look of the app here only.
"""
import streamlit as st


def inject_css():
    st.markdown("""
<style>
    /* ── Fonts ─────────────────────────────────────────────────────── */
    @import url('https://fonts.googleapis.com/css2?family=DM+Sans:wght@300;400;500;600&family=DM+Mono:wght@400;500&display=swap');
    @import url('https://fonts.googleapis.com/css2?family=Material+Symbols+Outlined:opsz,wght,FILL,GRAD@24,400,0,0');
    .material-symbols-outlined {
        font-family: 'Material Symbols Outlined';
        font-weight: normal; font-style: normal;
        line-height: 1; letter-spacing: normal;
        text-transform: none; display: inline-block;
        white-space: nowrap; word-wrap: normal; direction: ltr;
    }

    /* ── Design tokens ─────────────────────────────────────────────── */
    :root {
        --bg-app:       #F0F4F8;
        --bg-card:      #FFFFFF;
        --bg-sidebar:   #0B1929;
        --bg-sidebar-2: #142236;

        --clr-primary:  #1565C0;   /* clinical blue */
        --clr-primary-l:#E3F0FF;
        --clr-success:  #1B7B4B;
        --clr-success-l:#E6F4EE;
        --clr-warning:  #B45309;
        --clr-warning-l:#FEF3C7;
        --clr-danger:   #B91C1C;
        --clr-danger-l: #FEE2E2;
        --clr-purple:   #6D28D9;
        --clr-purple-l: #EDE9FE;
        --clr-cyan:     #0E7490;
        --clr-cyan-l:   #CFFAFE;
        --clr-slate:    #475569;
        --clr-slate-l:  #F1F5F9;

        --text-head:    #0F172A;
        --text-body:    #334155;
        --text-muted:   #64748B;

        --radius:       8px;
        --radius-sm:    5px;
        --shadow:       0 1px 4px rgba(15,23,42,0.08), 0 0 0 1px rgba(15,23,42,0.04);
        --shadow-md:    0 4px 12px rgba(15,23,42,0.10), 0 0 0 1px rgba(15,23,42,0.04);
    }

    /* ── Global ─────────────────────────────────────────────────────── */
    html, body, [class*="css"] {
        font-family: 'DM Sans', sans-serif;
        color: var(--text-body);
    }
    .stApp { background: var(--bg-app) !important; }

    /* ── Stat cards — fixed equal height ────────────────────────────── */
    .stat-card {
        background: var(--bg-card);
        border-radius: var(--radius);
        box-shadow: var(--shadow);
        padding: 18px 20px;
        height: 96px;
        display: flex;
        flex-direction: column;
        justify-content: center;
        border-top: 3px solid transparent;
        border-left: none !important;
        transition: box-shadow 0.15s;
    }
    .stat-card:hover { box-shadow: var(--shadow-md); }

    .stat-card.pending    { border-top-color: #F59E0B; }
    .stat-card.outreach   { border-top-color: var(--clr-purple); }
    .stat-card.accepted   { border-top-color: var(--clr-cyan); }
    .stat-card.assigned   { border-top-color: var(--clr-primary); }
    .stat-card.done       { border-top-color: #F97316; }
    .stat-card.dismissed  { border-top-color: var(--clr-success); }

    .stat-num {
        font-size: 28px;
        font-weight: 600;
        color: var(--text-head);
        line-height: 1;
        margin-bottom: 5px;
        font-variant-numeric: tabular-nums;
    }
    .stat-label {
        font-size: 12px;
        color: var(--text-muted);
        font-weight: 500;
        letter-spacing: 0.02em;
        text-transform: uppercase;
        white-space: nowrap;
    }

    /* ── Role badges ────────────────────────────────────────────────── */
    .role-badge {
        display: inline-block;
        padding: 3px 10px;
        border-radius: 4px;
        font-size: 11px;
        font-weight: 600;
        font-family: 'DM Mono', monospace;
        letter-spacing: 0.06em;
        text-transform: uppercase;
    }
    .badge-director { background: var(--clr-primary-l);  color: var(--clr-primary); }
    .badge-police   { background: var(--clr-purple-l);   color: var(--clr-purple); }
    .badge-outreach { background: var(--clr-cyan-l);     color: var(--clr-cyan); }
    .badge-worker   { background: var(--clr-success-l);  color: var(--clr-success); }
    .badge-intake   { background: var(--clr-warning-l);  color: var(--clr-warning); }

    /* ── Access denied ──────────────────────────────────────────────── */
    .access-denied {
        background: var(--clr-danger-l);
        border: 1px solid #FECACA;
        border-radius: var(--radius);
        padding: 20px;
        color: var(--clr-danger);
        font-weight: 500;
        text-align: center;
    }

    /* ── Sidebar ─────────────────────────────────────────────────────── */
    [data-testid="stSidebar"] {
        background: var(--bg-sidebar) !important;
        border-right: 1px solid #1E3352 !important;
    }
    [data-testid="stSidebar"] * { color: #CBD5E1 !important; }
    [data-testid="stSidebar"] h1,
    [data-testid="stSidebar"] h2,
    [data-testid="stSidebar"] h3 { color: #F1F5F9 !important; }

    [data-testid="stSidebar"] .stTextInput input {
        background: var(--bg-sidebar-2) !important;
        border: 1px solid #2D4A6B !important;
        color: #F1F5F9 !important;
        border-radius: var(--radius-sm) !important;
        font-family: 'DM Mono', monospace !important;
        font-size: 13px !important;
    }
    [data-testid="stSidebar"] .stTextInput input:focus {
        border-color: var(--clr-primary) !important;
        box-shadow: 0 0 0 2px rgba(21,101,192,0.25) !important;
    }
    [data-testid="stSidebar"] .stButton button {
        background: var(--clr-primary) !important;
        color: #FFFFFF !important;
        font-weight: 600 !important;
        border: none !important;
        border-radius: var(--radius-sm) !important;
        width: 100% !important;
        letter-spacing: 0.02em !important;
    }
    [data-testid="stSidebar"] .stButton button:hover {
        background: #1976D2 !important;
    }

    /* ── Main content tweaks ────────────────────────────────────────── */
    h1, h2, h3 { color: var(--text-head) !important; }
    .stDataFrame { border-radius: var(--radius) !important; }
    .stButton > button {
        border-radius: var(--radius-sm) !important;
        font-weight: 500 !important;
        letter-spacing: 0.01em !important;
    }
    /* Primary button */
    .stButton > button[kind="primary"] {
        background: var(--clr-primary) !important;
        border-color: var(--clr-primary) !important;
    }
    /* Tab styling */
    .stTabs [data-baseweb="tab-list"] {
        background: transparent !important;
        border-bottom: 2px solid #E2E8F0 !important;
        gap: 4px !important;
    }
    .stTabs [data-baseweb="tab"] {
        font-size: 13px !important;
        font-weight: 500 !important;
        color: var(--text-muted) !important;
        padding: 8px 16px !important;
        border-radius: var(--radius-sm) var(--radius-sm) 0 0 !important;
    }
    .stTabs [aria-selected="true"] {
        color: var(--clr-primary) !important;
        border-bottom: 2px solid var(--clr-primary) !important;
        background: var(--clr-primary-l) !important;
    }
    /* Metric / info boxes */
    [data-testid="stMetric"] {
        background: var(--bg-card);
        border-radius: var(--radius);
        padding: 12px 16px;
        box-shadow: var(--shadow);
    }
    /* Expander */
    .streamlit-expanderHeader {
        background: var(--clr-slate-l) !important;
        border-radius: var(--radius-sm) !important;
        font-weight: 500 !important;
        color: var(--text-body) !important;
    }
    /* Divider */
    hr { border-color: #E2E8F0 !important; }
</style>
""", unsafe_allow_html=True)
