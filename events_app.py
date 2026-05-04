import os
from datetime import datetime
from pathlib import Path

import streamlit as st
from dotenv import load_dotenv
from supabase import create_client

# ── SETUP ─────────────────────────────────────────────────────────────────────
_env = Path(__file__).resolve().parent / ".env"
load_dotenv(_env)
SUPABASE_URL = (os.getenv("SUPABASE_URL") or "").strip()
SUPABASE_KEY = (os.getenv("SUPABASE_KEY") or "").strip()

st.set_page_config(page_title="GIX Events", page_icon="📅", layout="wide")

# Error handling: missing credentials
if not SUPABASE_URL or not SUPABASE_KEY:
    st.error("❌ Missing Supabase credentials. Check your .env file.")
    st.stop()

# Error handling: connection failure
try:
    supabase = create_client(SUPABASE_URL, SUPABASE_KEY)
except Exception as e:
    st.error(f"❌ Could not connect to database: {e}")
    st.stop()

st.title("📅 GIX Events")
st.caption("Browse upcoming events at GIX — filter by category to find what interests you.")

# ── FETCH EVENTS ──────────────────────────────────────────────────────────────
try:
    response = supabase.table("events").select("*").order("event_date").execute()
    events = response.data

    # Assert 1: response must be a list
    assert isinstance(events, list), "Expected a list of events from Supabase"

    # Assert 2: each event must have required fields
    for event in events:
        assert "title" in event, "Event missing required field: title"
        assert "category" in event, "Event missing required field: category"
        assert "event_date" in event, "Event missing required field: event_date"

except AssertionError as e:
    st.error(f"❌ Data format error: {e}")
    st.stop()
except Exception as e:
    # Error handling: fetch failure
    st.error(f"❌ Could not load events: {e}")
    st.stop()

# ── FILTERS ───────────────────────────────────────────────────────────────────
if not events:
    st.info("No events found in the database.")
    st.stop()

col1, col2 = st.columns([2, 3])
with col1:
    categories = ["All"] + sorted(set(e["category"] for e in events))
    selected_category = st.selectbox("Filter by category", categories)
with col2:
    search = st.text_input("Search by title or speaker", placeholder="e.g. AI, Workshop")

# ── APPLY FILTERS ─────────────────────────────────────────────────────────────
filtered = events
if selected_category != "All":
    filtered = [e for e in filtered if e["category"] == selected_category]
if search:
    filtered = [
        e for e in filtered
        if search.lower() in e["title"].lower()
        or search.lower() in (e.get("speaker") or "").lower()
    ]

# ── SUMMARY METRICS ───────────────────────────────────────────────────────────
m1, m2, m3, m4 = st.columns(4)
m1.metric("Total Events", len(events))
m2.metric("Showing", len(filtered))
m3.metric("Categories", len(set(e["category"] for e in events)))
m4.metric("Next Event", filtered[0]["event_date"][:10] if filtered else "—")

st.divider()

# ── CATEGORY COLOR MAP ────────────────────────────────────────────────────────
category_emoji = {
    "Guest Lecture": "🎤",
    "Career Panel": "💼",
    "Workshop": "🛠️",
    "Social": "🎉",
    "Other": "📌"
}

# ── DISPLAY EVENTS ────────────────────────────────────────────────────────────
if not filtered:
    st.info("No events match your filters.")
else:
    st.subheader(f"{'All Events' if selected_category == 'All' else selected_category} ({len(filtered)})")

    for event in filtered:
        emoji = category_emoji.get(event["category"], "📌")

        # Format date nicely
        try:
            dt = datetime.fromisoformat(event["event_date"].replace("Z", "+00:00"))
            date_str = dt.strftime("%A, %B %d %Y at %I:%M %p")
        except Exception:
            date_str = event["event_date"][:16]

        with st.expander(f"{emoji} {event['title']} — {event['category']} | {date_str}"):
            col_a, col_b = st.columns(2)
            with col_a:
                st.write(f"**📍 Location:** {event.get('location') or 'TBD'}")
                st.write(f"**🎙️ Speaker:** {event.get('speaker') or 'TBD'}")
                st.write(f"**🏷️ Category:** {event['category']}")
            with col_b:
                st.write(f"**📅 Date:** {date_str}")
                st.write(f"**📝 Description:**")
                st.write(event.get("description") or "No description provided.")
