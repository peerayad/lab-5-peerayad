import os
from pathlib import Path

import bcrypt
from dotenv import load_dotenv
from supabase import create_client

_env = Path(__file__).resolve().parent / ".env"
load_dotenv(_env)
SUPABASE_URL = (os.getenv("SUPABASE_URL") or "").strip()
SUPABASE_KEY = (os.getenv("SUPABASE_KEY") or "").strip()

if not SUPABASE_URL or not SUPABASE_KEY:
    raise SystemExit(f"Missing SUPABASE_URL or SUPABASE_KEY (checked {_env})")

supabase = create_client(SUPABASE_URL, SUPABASE_KEY)

# Define users and their real passwords
users = [
    ("maason", "maason123"),
    ("kevin", "kevin123"),
    ("student1", "student123"),
    ("student2", "student456"),
]

for username, password in users:
    hashed = bcrypt.hashpw(password.encode(), bcrypt.gensalt()).decode()
    supabase.table("users").update({"password_hash": hashed}).eq("username", username).execute()
    print(f"✅ Password set for {username}")

print("Done!")
