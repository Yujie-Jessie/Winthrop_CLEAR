"""
db.py — Database layer
Database connection, table creation, seed accounts, and password hashing.
"""
import streamlit as st
import psycopg2
import hashlib


@st.cache_resource
def get_db_url():
    return st.secrets["DATABASE_URL"]


def get_db_connection():
    """Always returns a fresh, open connection."""
    url = get_db_url()
    conn = psycopg2.connect(url, sslmode="require")
    conn.autocommit = True   # simpler: no manual commit needed
    return conn


def hash_password(pw):
    return hashlib.sha256(pw.encode()).hexdigest()


def init_db():
    conn = get_db_connection()
    c = conn.cursor()

    c.execute("""
        CREATE TABLE IF NOT EXISTS users (
            user_id    SERIAL PRIMARY KEY,
            name       TEXT UNIQUE NOT NULL,
            password   TEXT NOT NULL,
            role       TEXT NOT NULL,
            is_active  INTEGER DEFAULT 1,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)

    c.execute("""
        CREATE TABLE IF NOT EXISTS clients (
            client_id    SERIAL PRIMARY KEY,
            name         TEXT,
            phone        TEXT,
            ssn          TEXT,
            dob          TEXT,
            race         TEXT,
            sex          TEXT,
            oln          TEXT,
            insurance_co TEXT,
            policy_no    TEXT
        )
    """)

    c.execute("""
        CREATE TABLE IF NOT EXISTS cases (
            case_id        SERIAL PRIMARY KEY,
            client_id      INTEGER REFERENCES clients(client_id),
            call_number    TEXT,
            case_type      TEXT,
            call_timestamp TIMESTAMP,
            location       TEXT,
            call_reason    TEXT,
            action         TEXT,
            priority_level TEXT,
            call_taker     TEXT,
            call_source    TEXT,
            jurisdiction   TEXT,
            vicinity       TEXT,
            narrative      TEXT,
            current_status TEXT DEFAULT 'Pending',
            created_by     INTEGER REFERENCES users(user_id),
            ai_flag        TEXT,
            ai_reason      TEXT,
            bh_relevant    BOOLEAN DEFAULT TRUE
        )
    """)

    # Migrate: add AI columns to existing DBs
    for _col, _typ in [("ai_flag", "TEXT"), ("ai_reason", "TEXT"), ("bh_relevant", "BOOLEAN DEFAULT TRUE")]:
        try:
            c.execute(f"ALTER TABLE cases ADD COLUMN {_col} {_typ}")
        except Exception:
            pass  # column already exists

    c.execute("""
        CREATE TABLE IF NOT EXISTS case_reviews (
            review_id   SERIAL PRIMARY KEY,
            case_id     INTEGER REFERENCES cases(case_id),
            reviewed_by INTEGER REFERENCES users(user_id),
            decision    TEXT,
            review_note TEXT,
            reviewed_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)

    c.execute("""
        CREATE TABLE IF NOT EXISTS outreach_contacts (
            contact_id   SERIAL PRIMARY KEY,
            case_id      INTEGER REFERENCES cases(case_id),
            officer_id   INTEGER REFERENCES users(user_id),
            outcome      TEXT,
            contact_note TEXT,
            contacted_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)

    c.execute("""
        CREATE TABLE IF NOT EXISTS assignments (
            assignment_id SERIAL PRIMARY KEY,
            case_id       INTEGER REFERENCES cases(case_id),
            worker_id     INTEGER REFERENCES users(user_id),
            assigned_by   INTEGER REFERENCES users(user_id),
            last_updated  TIMESTAMP,
            progress_note TEXT
        )
    """)

    c.execute("""
        CREATE TABLE IF NOT EXISTS audit_log (
            log_id    SERIAL PRIMARY KEY,
            user_id   INTEGER,
            action    TEXT,
            detail    TEXT,
            timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)

    # Seed default accounts (only if users table is empty)
    c.execute("SELECT COUNT(*) FROM users")
    if c.fetchone()[0] == 0:
        seed_users = [
            ("dir_health", hash_password("health123"), "DIRECTOR"),
            ("dir_sw",     hash_password("sw123"),     "DIRECTOR"),
            ("police",     hash_password("police123"), "POLICE"),
            ("outreach1",  hash_password("out123"),    "OUTREACH_POLICE"),
            ("intake1",    hash_password("intake123"), "INTAKE"),
            ("worker1",    hash_password("worker123"), "SOCIAL_WORKER"),
        ]
        for name, pw, role in seed_users:
            c.execute(
                "INSERT INTO users (name, password, role) VALUES (%s, %s, %s) ON CONFLICT (name) DO NOTHING",
                (name, pw, role),
            )

    # Seed 30 example cases (only if the cases table is empty) — all dated March 2026
    c.execute("SELECT COUNT(*) FROM cases")
    if c.fetchone()[0] == 0:
        # Attribute the example cases to the intake officer
        c.execute("SELECT user_id FROM users WHERE name='intake1'")
        _r = c.fetchone()
        intake_id = _r[0] if _r else None

        # (name, phone, case_type, call_timestamp, location, call_reason, priority, call_source, narrative, status)
        sample_cases = [
            ("Marcus Delaney", "617-555-0142", "Mental Health", "2026-03-02 14:20", "112 Shirley St", "Adult son in acute distress, expressing he does not want to be here", "1", "911", "Family called after 34-year-old male locked himself in a bedroom expressing hopelessness. No weapons reported. Mother on scene.", "Pending"),
            ("Tina Powers", "617-555-0188", "Substance Use", "2026-03-03 22:05", "47 Pleasant St", "Possible overdose, unresponsive male", "1", "911", "Bystander found male slumped in a doorway with shallow breathing. Naloxone administered by responding officer; patient revived and refused transport.", "Pending"),
            ("Robert Aguilar", "617-555-0203", "Wellness Check", "2026-03-03 09:40", "8 Crest Ave", "Neighbor has not seen elderly resident in several days", "3", "Telephone Call", "Neighbor requests a welfare check on a 78-year-old who lives alone. Mail is piling up and there is no answer at the door.", "Pending"),
            ("Jasmine Carter", "617-555-0219", "Domestic Violence", "2026-03-04 19:30", "23 Bowdoin St", "Verbal dispute escalating between partners", "2", "911", "Caller reports shouting and items being thrown next door. History of prior calls to this address.", "Pending"),
            ("Daniel Foss", "617-555-0234", "Homelessness", "2026-03-05 07:15", "Winthrop Center bus shelter", "Individual sleeping in transit shelter, appears unwell", "3", "Initiated", "Officer initiated contact with an unsheltered individual showing signs of cold exposure. Declined a shelter referral.", "Pending"),
            ("Olivia Brennan", "617-555-0251", "Mental Health", "2026-03-06 11:50", "59 Main St", "Caller experiencing a panic attack, requesting help", "2", "Telephone Call", "30-year-old female reported severe anxiety and chest tightness. Alert and oriented; asked for someone to talk to.", "Pending"),
            ("Victor Nguyen", "617-555-0267", "Substance Use", "2026-03-06 23:40", "14 Revere St", "Intoxicated individual causing a disturbance", "3", "911", "Male reportedly intoxicated and yelling in the street. No injuries. Cooperative on arrival.", "Pending"),
            ("Grace Sullivan", "617-555-0285", "Juvenile - Mental Health", "2026-03-07 16:10", "Winthrop High School", "School counselor concerned about a student", "2", "Telephone Call", "Counselor reports a 16-year-old expressing self-harm ideation. Parent contacted; student safe on campus.", "Pending"),
            ("Henry Cole", "617-555-0298", "Wellness Check", "2026-03-08 13:25", "31 Sunnyside Ave", "Employer reports worker not showing up and unreachable", "4", "Telephone Call", "Routine welfare check requested by employer. No prior concerns noted.", "Pending"),
            ("Maria Santos", "617-555-0312", "Mental Health", "2026-03-09 20:55", "76 Washington Ave", "Caller describes neighbor behaving erratically", "2", "911", "Reports of an individual pacing outside, talking to themselves, appearing disoriented. No aggression reported.", "Pending"),
            ("Kevin Walsh", "617-555-0327", "Substance Use", "2026-03-10 18:15", "5 Hermon St", "Family requests help for a relative's addiction", "3", "Telephone Call", "Sister calling about brother's worsening alcohol use, missed work, and isolation. Seeking resources.", "Pending"),
            ("Angela Reyes", "617-555-0341", "Domestic Violence", "2026-03-11 21:05", "62 Pauline St", "Caller reports being threatened by partner", "1", "911", "Female caller whispering, states partner is intoxicated and threatening. Children in the home. Officers dispatched.", "Pending"),
            ("Thomas Pike", "617-555-0359", "Homelessness", "2026-03-12 08:30", "Veterans Rd underpass", "Encampment reported, welfare concern", "4", "Initiated", "Outreach contact with two unsheltered individuals. Provided information on the warming center.", "Pending"),
            ("Lily Chen", "617-555-0372", "Juvenile - Alcohol/Substance", "2026-03-13 23:20", "Crest Ave seawall", "Group of minors reported drinking", "3", "911", "Report of several teens with alcohol near the seawall. One appeared intoxicated; parents notified.", "Pending"),
            ("Frank Morrow", "617-555-0388", "Mental Health", "2026-03-14 15:45", "19 Bartlett Rd", "Veteran in crisis, family requesting help", "1", "911", "Family reports a veteran with PTSD experiencing a flashback and agitation. Firearms previously removed from home. Crisis team requested.", "Pending"),
            ("Sandra Lopez", "617-555-0401", "Wellness Check", "2026-03-15 10:05", "44 Somerset Ave", "Out-of-state relative requests a check", "4", "Telephone Call", "Daughter out of state has not reached her mother by phone in two days. Requesting a welfare check.", "Pending"),
            ("Derek Hall", "617-555-0418", "Substance Use", "2026-03-16 02:30", "Main St & Pleasant St", "Possible impaired individual in the roadway", "2", "911", "Male wandering near the intersection, unsteady, possible substance impairment. Guided to safety.", "Pending"),
            ("Nicole Adams", "617-555-0433", "Mental Health", "2026-03-17 17:55", "88 Shirley St", "Caller reports suicidal statements by a family member", "1", "911", "Spouse reports partner made statements about ending their life and has access to means. Immediate response requested.", "Pending"),
            ("Omar Haddad", "617-555-0447", "Other", "2026-03-18 12:40", "27 Buchanan St", "Hoarding conditions, welfare concern", "3", "Telephone Call", "Property manager reports unsafe living conditions and a resident refusing assistance.", "Pending"),
            ("Patricia Doyle", "617-555-0462", "Wellness Check", "2026-03-19 09:15", "53 Cottage Park Rd", "Elderly resident fall, no injury reported", "3", "911", "Neighbor heard a call for help. 81-year-old fell, no apparent injury, declined transport. Lives alone.", "Pending"),
            ("Jordan Blake", "617-555-0479", "Juvenile - Mental Health", "2026-03-20 14:00", "Winthrop Middle School", "Student left class in distress", "2", "Telephone Call", "13-year-old reportedly ran from a classroom crying and was found safe. School requesting follow-up support.", "Pending"),
            ("Rosa Martinez", "617-555-0491", "Domestic Violence", "2026-03-21 20:10", "16 Cliff Ave", "Neighbor reports an ongoing disturbance", "2", "911", "Repeated disturbances reported at the residence. No injuries this incident; safety-plan information provided.", "Pending"),
            ("Eric Sandberg", "617-555-0508", "Substance Use", "2026-03-22 19:25", "9 Grovers Ave", "Overdose reversal, follow-up requested", "1", "911", "Patient revived with naloxone and transported. Family requesting outreach for treatment options.", "Pending"),
            ("Hannah Webb", "617-555-0523", "Mental Health", "2026-03-23 11:30", "71 Sturgis St", "Caller reports increasing isolation and despair", "3", "Telephone Call", "Caller describes persistent low mood and withdrawal over several weeks. No immediate risk stated.", "Pending"),
            ("Carlos Mendez", "617-555-0537", "Homelessness", "2026-03-24 06:50", "Public Landing", "Individual living in a vehicle, welfare check", "4", "Initiated", "Contact made with a person residing in a vehicle. Accepted information on housing services.", "Pending"),
            ("Beverly Tran", "617-555-0549", "Wellness Check", "2026-03-25 13:10", "38 Woodside Ave", "Caregiver concerned about a client", "4", "Telephone Call", "Home health aide unable to reach a client and requesting a check. No prior emergencies.", "Pending"),
            ("Gary Phillips", "617-555-0561", "Mental Health", "2026-03-26 22:45", "12 Hermon St", "Individual in acute psychiatric distress", "1", "911", "Male reportedly responding to internal stimuli and distressed but not violent. Crisis clinician requested for evaluation.", "Pending"),
            ("Denise Okafor", "617-555-0574", "Substance Use", "2026-03-27 16:35", "65 Washington Ave", "Family seeking detox resources", "3", "Telephone Call", "Mother seeking help for an adult child's opioid use. No acute medical issue at the time of the call.", "Pending"),
            ("Steven Kraus", "617-555-0586", "Juvenile - Alcohol/Substance", "2026-03-29 21:50", "Ingleside Park", "Minor found intoxicated", "2", "911", "15-year-old found intoxicated at the park, no injuries. Released to a guardian; referral to youth services suggested.", "Pending"),
            ("Alice Bennett", "617-555-0599", "Wellness Check", "2026-03-30 10:20", "21 Cottage Hill Rd", "Welfare check on a resident with dementia", "3", "Telephone Call", "Family reports a resident with dementia not answering the phone. Requesting a check; no known immediate danger.", "Pending"),
        ]

        for i, (cname, phone, ctype, cts, loc, reason, pri, csrc, narr, status) in enumerate(sample_cases, start=1):
            c.execute(
                "INSERT INTO clients (name, phone) VALUES (%s, %s) RETURNING client_id",
                (cname, phone),
            )
            cl_id = c.fetchone()[0]
            c.execute("""
                INSERT INTO cases (client_id, call_number, case_type, call_timestamp,
                    location, call_reason, action, priority_level, call_taker,
                    call_source, jurisdiction, vicinity, narrative, current_status, created_by)
                VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)
            """, (cl_id, f"WIN-2026-{i:04d}", ctype, cts, loc, reason, "",
                  pri, "Dispatch", csrc, "WINTHROP", "", narr, status, intake_id))
