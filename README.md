# GIX Equipment Tracker

A **Streamlit** web app for the GIX equipment room. It tracks **inventory** (with sequential **asset tags**) and a full **borrow / return lifecycle** backed by **Supabase**. Users sign in with roles: **approvers** (staff) manage approvals and confirmations; **requesters** (students) submit borrow requests and mark returns.

---

## What it does

| Area | Description |
|------|-------------|
| **Inventory** | List equipment with filters (category, status, search), optional CSV export, edit/delete (approvers). |
| **Borrow workflow** | Students request items → staff approve (equipment becomes `checked_out`) → students mark “returned” → staff confirm (equipment becomes `available` again). |
| **Requests** | Each flow is stored in `borrow_requests` with timestamps and who approved/confirmed. |
| **Bulk add** | Approvers can add one item or import many rows from CSV (asset tags are **auto-generated**; do not put `asset_tag` in the CSV). |

**Request / equipment status (high level)**

- **Borrow request:** `pending_approval` → `approved` or `rejected` → (after return) `pending_return` → `returned`
- **Equipment row:** `available` ↔ `checked_out` (simple physical state in the `equipment` table)

---

## Tech stack

- **Python 3.8+** (see `requirements.txt` for pins)
- **Streamlit** — UI
- **Supabase** — PostgreSQL + API (`supabase-py`)
- **bcrypt** — password verification against `users.password_hash`

---

## Project layout (main files)

| File | Purpose |
|------|---------|
| `app.py` | Main Streamlit app (login, role-based tabs, all features). |
| `requirements.txt` | Pinned dependencies (`pip install -r requirements.txt`). |
| `borrow_requests.sql` | SQL to create the `borrow_requests` table (run once in Supabase). |
| `hash_passwords.py` | One-off script to set bcrypt hashes in `users` (run locally; keep DB credentials private). |
| `.env` | **Not in git** — your Supabase URL and anon key (see below). |

---

## Database expectations (Supabase)

The app assumes at least:

1. **`equipment`** — inventory (e.g. `id`, `name`, `category`, `status`, `notes`, `asset_tag`, `returned_at`, …).
2. **`users`** — logins: `username`, `password_hash` (bcrypt), `full_name`, `role` (`approver` or `requester`).
3. **`borrow_requests`** — create with `borrow_requests.sql` (or equivalent). Links to `equipment` via `equipment_id`.

Enable **Row Level Security (RLS)** and policies that match your class requirements; the app uses the **anon** key from the environment, so your Supabase policies must allow the operations the app performs.

---

## Local setup (for TAs / developers)

1. **Clone the repo** and create a virtual environment:

   ```bash
   python -m venv venv
   source venv/bin/activate   # Windows: venv\Scripts\activate
   pip install -r requirements.txt
   ```

2. **Create `.env`** in the project root (same folder as `app.py`):

   ```env
   SUPABASE_URL=https://YOUR_PROJECT.supabase.co
   SUPABASE_KEY=YOUR_ANON_OR_SERVICE_KEY
   ```

3. **Run the app:**

   ```bash
   streamlit run app.py
   ```

4. Open the URL Streamlit prints (usually `http://localhost:8501`).

**Optional:** To refresh password hashes for seed users, configure `.env`, then run `python hash_passwords.py` once (adjust user list inside the script to match your `users` table).

---

## Deploy on Streamlit Community Cloud

1. Push this repo to GitHub (without committing `.env`).
2. In [Streamlit Cloud](https://streamlit.io/cloud), **New app** → pick the repo, branch, and **Main file path:** `app.py`.
3. Under **Secrets**, add **TOML** format (not shell):

   ```toml
   SUPABASE_URL = "https://YOUR_PROJECT.supabase.co"
   SUPABASE_KEY = "YOUR_ANON_KEY"
   ```

4. Redeploy after changing secrets.

Streamlit Cloud injects secrets as environment variables; the app reads `SUPABASE_URL` and `SUPABASE_KEY` via `os.getenv` after `load_dotenv()`. For deployment you may rely on the platform env alone if `.env` is absent.

---

## Using the app (by role)

### After login

- The header shows **full name**, **username**, and **role** (Approver vs Requester).
- Use **Log Out** to clear the session.

### Requester (student)

| Tab | Action |
|-----|--------|
| **Browse Equipment** | View inventory (filters, table). |
| **My Borrow Requests** | Submit a new borrow request for available gear; see your own request history. |
| **Return Equipment** | For items you borrowed that are **approved**, mark them as returned (waits for staff confirmation). |

### Approver (staff)

| Tab | Action |
|-----|--------|
| **Browse** | Full inventory, export (current view / full list), edit or delete items. |
| **Approve Requests** | Multi-select pending requests; **Approve** or **Reject** in batch. |
| **Confirm Returns** | Multi-select items in **pending_return**; confirm so gear goes back to **available**. |
| **All Requests** | Filter and review all borrow requests. |
| **Add Item** | Add one piece of equipment (gets next sequential asset tag). |
| **Upload CSV** | Bulk import `name`, `category`, `notes` (no `asset_tag` column). |

Demo login hints appear on the login screen for local/testing; **change or remove demo accounts in production** and use strong passwords.

---

## Tips for grading / testing

1. Sign in as **requester** → request an **available** item.  
2. Sign in as **approver** → **Approve** that request → equipment should show **checked_out**.  
3. As **requester** → **Return** the item → request moves toward staff confirmation.  
4. As **approver** → **Confirm return** → equipment should be **available** again.

If something fails, check the browser error text and Supabase **logs / RLS policies** for blocked queries.

---

## License / course use

Built for **TECHIN510** / GIX lab coursework; adapt as your instructor allows.
