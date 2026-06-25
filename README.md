# Public Health Case Management — Setup & Structure

A role-based Streamlit dashboard backed by PostgreSQL, with AI-assisted case
flagging via the Claude API.

---

## 1. Setup from scratch

### Step 1 — Put all files in one folder
Place every file from this package into the same folder, e.g. `d:\CLEAR`.
`app.py` imports the other files, so they must all sit side by side.

### Step 2 — Install Python dependencies
Open a terminal in the project folder and run:

    pip install -r requirements.txt

### Step 3 — Get your two secrets
- **DATABASE_URL** — a PostgreSQL connection string. If you don't have one, a
  free database from Neon (neon.tech) or Supabase works. It looks like:
  `postgresql://user:password@host/dbname?sslmode=require`
- **ANTHROPIC_API_KEY** — from https://console.anthropic.com -> API Keys ->
  Create Key. Add a little credit under Billing (the API is pay-per-use).

### Step 4 — Create the secrets file
Streamlit reads secrets from `.streamlit/secrets.toml`. Create it like this
(the folder name starts with a dot and is hidden in Windows Explorer, so the
terminal is the easy way):

    cd /d d:\CLEAR
    mkdir .streamlit
    notepad .streamlit\secrets.toml

When Notepad asks to create the file, say yes, then paste:

    DATABASE_URL = "postgresql://user:password@host/dbname?sslmode=require"
    ANTHROPIC_API_KEY = "sk-ant-..."

Save and close. (See `secrets.toml.example` for the same template.)

### Step 5 — Run
    cd /d d:\CLEAR
    streamlit run app.py

### Step 6 — Log in
On first run the app auto-creates the tables and these seed accounts:

| Username | Password | Role |
|---|---|---|
| dir_health | health123 | Director |
| dir_sw | sw123 | Director |
| police | police123 | Police |
| outreach1 | out123 | Outreach Police |
| intake1 | intake123 | Intake |
| worker1 | worker123 | Social Worker |

---

## 2. What each file does

| File | Responsibility | Edit it to change... |
|---|---|---|
| `app.py` | Entry point: page setup, styles, DB init, login, routing | startup flow, add/remove a role |
| `db.py` | DB connection, table creation, seed accounts, hashing | table schema, default accounts |
| `permissions.py` | Per-role permission table | who can do what |
| `helpers.py` | Logging, sensitive-column hiding, date filters, display names | shared utilities |
| `ai_flagging.py` | Claude API call for case flagging (cache bug fixed) | AI prompt, model, timeout |
| `styles.py` | Global CSS | the look of the app |
| `auth.py` | Sidebar login / logout | the login screen |
| `dashboard_director.py` | Director / Police dashboard (6 tabs) | the director view |
| `dashboard_outreach.py` | Outreach Police dashboard | the outreach view |
| `dashboard_intake.py` | Intake new-case entry | the intake form |
| `dashboard_social_worker.py` | Social Worker workspace | the social worker view |

---

## 3. Dependency graph

    app.py
     |- styles.py
     |- db.py
     |- auth.py                     --> db.py, helpers.py
     |- dashboard_director.py       --> helpers.py, db.py, ai_flagging.py
     |- dashboard_outreach.py       --> helpers.py
     |- dashboard_intake.py         --> helpers.py
     |- dashboard_social_worker.py  --> helpers.py

The low-level modules (`db`, `helpers`, `permissions`, `ai_flagging`, `styles`)
depend on no dashboard, so editing one dashboard won't break the others.

---

## 4. Notes
- `.streamlit/secrets.toml` is NOT included in this package (it holds private
  keys). Create your own as described in Step 4.
- Behavior is identical to the original single-file version, plus a fix for the
  AI call that previously retried on every rerun and froze the page.
