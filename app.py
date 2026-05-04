import streamlit as st
from supabase import create_client
from dotenv import load_dotenv
import os
import bcrypt
from datetime import datetime
import pandas as pd
import io
import csv
import requests

# ── SETUP ─────────────────────────────────────────────────────────────────────
load_dotenv()
SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_KEY")

try:
    supabase = create_client(SUPABASE_URL, SUPABASE_KEY)
except Exception as e:
    st.error(f"Could not connect to database: {e}")
    st.stop()

st.set_page_config(page_title="GIX Equipment Tracker", page_icon="📦", layout="wide")

# Responsive design fix
st.markdown("""
<style>
    .stTabs [data-baseweb="tab-list"] {
        flex-wrap: wrap;
        gap: 4px;
    }
    .stTabs [data-baseweb="tab"] {
        white-space: normal;
        font-size: 13px;
        padding: 6px 10px;
    }
    [data-testid="stDataFrame"] {
        overflow-x: auto;
    }
</style>
""", unsafe_allow_html=True)

# ── SESSION STATE ──────────────────────────────────────────────────────────────
if "logged_in" not in st.session_state:
    st.session_state.logged_in = False
if "user" not in st.session_state:
    st.session_state.user = None

# ── LOGIN PAGE ─────────────────────────────────────────────────────────────────
def show_login():
    st.title("📦 GIX Equipment Tracker")
    st.subheader("Please log in")

    col1, col2, col3 = st.columns([1, 2, 1])
    with col2:
        username = st.text_input("Username", placeholder="e.g. student1")
        password = st.text_input("Password", type="password")

        if st.button("🔑 Log In", type="primary", use_container_width=True):
            if not username or not password:
                st.warning("Please enter both username and password.")
            else:
                try:
                    result = supabase.table("users").select("*").eq("username", username).execute()
                    if not result.data:
                        st.error("❌ Username not found.")
                    else:
                        user = result.data[0]
                        if bcrypt.checkpw(password.encode(), user["password_hash"].encode()):
                            st.session_state.logged_in = True
                            st.session_state.user = user
                            st.rerun()
                        else:
                            st.error("❌ Incorrect password.")
                except Exception as e:
                    st.error(f"Login error: {e}")

        st.divider()
        st.caption("Demo accounts:")
        st.caption("Approver: maason / maason123  |  kevin / kevin123")
        st.caption("Requester: student1 / student123  |  student2 / student456")

# ── HEADER ────────────────────────────────────────────────────────────────────
def show_header():
    col1, col2 = st.columns([4, 1])
    with col1:
        st.title("📦 GIX Equipment Tracker")
        user = st.session_state.user
        role_badge = "🟣 Approver" if user["role"] == "approver" else "🔵 Requester"
        st.caption(f"Logged in as **{user['full_name']}** ({user['username']}) — {role_badge}")
    with col2:
        if st.button("🚪 Log Out", use_container_width=True):
            st.session_state.logged_in = False
            st.session_state.user = None
            st.rerun()

# ── HELPERS ───────────────────────────────────────────────────────────────────
def generate_asset_tag():
    """Generate next sequential 8-digit asset tag"""
    result = supabase.table("equipment").select("asset_tag").execute()
    existing_tags = [
        int(item["asset_tag"])
        for item in result.data
        if item.get("asset_tag") and item["asset_tag"].isdigit()
    ]
    next_number = max(existing_tags) + 1 if existing_tags else 1
    return str(next_number).zfill(8)


def generate_barcode(asset_tag):
    """
    Generate a barcode image for an 8-digit asset tag using barcodeapi.org.
    Directly addresses Maason's pain point: barcodes cannot be generated
    inside BlueTally and must be pre-generated externally.
    Returns: bytes (image) or dict with 'error' key
    """
    try:
        url = f"https://barcodeapi.org/api/128/{asset_tag}"
        response = requests.get(url, timeout=5)

        # Contract assertions
        assert response.status_code == 200, \
            f"Barcode API returned status {response.status_code}"
        assert len(response.content) > 0, \
            "Barcode API returned empty content"
        assert response.headers.get("Content-Type", "").startswith("image/"), \
            f"Expected image content, got {response.headers.get('Content-Type')}"

        return response.content

    except AssertionError as e:
        return {"error": str(e)}
    except requests.exceptions.Timeout:
        return {"error": "Barcode API timed out after 5 seconds"}
    except Exception as e:
        return {"error": f"Could not generate barcode: {e}"}


def show_barcode(tag):
    """Display a generated barcode for a given asset tag"""
    barcode = generate_barcode(tag)
    if isinstance(barcode, bytes):
        st.image(
            io.BytesIO(barcode),
            caption=f"Barcode for asset tag {tag} — right-click to save and print"
        )
    else:
        st.warning(f"⚠️ Could not generate barcode: {barcode.get('error')}")


# ── MAIN APP ──────────────────────────────────────────────────────────────────
def show_app():
    show_header()
    user = st.session_state.user
    role = user["role"]

    if role == "approver":
        tab1, tab2, tab3, tab4, tab5, tab6 = st.tabs([
            "📋 Browse",
            "✅ Approve Requests",
            "🔍 Confirm Returns",
            "📊 All Requests",
            "➕ Add Item",
            "📂 Upload CSV"
        ])
    else:
        tab1, tab2, tab3 = st.tabs([
            "📋 Browse Equipment",
            "📝 My Borrow Requests",
            "📦 Return Equipment"
        ])

    # ── TAB 1: BROWSE (both roles) ────────────────────────────────────────────
    with tab1:
        st.subheader("Equipment Inventory")

        try:
            response = supabase.table("equipment").select("*").execute()
            items = response.data
            assert isinstance(items, list), "Expected a list from Supabase"
        except Exception as e:
            st.error(f"Could not load equipment: {e}")
            items = []

        if items:
            col_f1, col_f2, col_f3 = st.columns(3)
            with col_f1:
                categories = ["All"] + sorted(set(i["category"] for i in items))
                selected_category = st.selectbox("Filter by category", categories)
            with col_f2:
                statuses = ["All", "available", "checked_out"]
                selected_status = st.selectbox("Filter by status", statuses)
            with col_f3:
                search = st.text_input("Search by name", placeholder="e.g. Sony")

            tags = [int(i["asset_tag"]) for i in items if i.get("asset_tag") and i["asset_tag"].isdigit()]
            if tags:
                m1, m2, m3, m4 = st.columns(4)
                m1.metric("Total Items", len(items))
                m2.metric("Available", sum(1 for i in items if i["status"] == "available"))
                m3.metric("Checked Out", sum(1 for i in items if i["status"] == "checked_out"))
                m4.metric("Next Asset Tag", str(max(tags) + 1).zfill(8))

            st.divider()

            filtered = items
            if selected_category != "All":
                filtered = [i for i in filtered if i["category"] == selected_category]
            if selected_status != "All":
                filtered = [i for i in filtered if i["status"] == selected_status]
            if search:
                filtered = [i for i in filtered if search.lower() in i["name"].lower()]

            if not filtered:
                st.info("No items match your filters.")
            else:
                table = pd.DataFrame([
                    {
                        "Asset Tag": i.get("asset_tag") or "N/A",
                        "Name": i["name"],
                        "Category": i["category"],
                        "Status": "🟢 Available" if i["status"] == "available" else "🔴 Checked Out",
                        "Notes": i.get("notes") or "—",
                        "Last Returned": i.get("returned_at", "")[:10] if i.get("returned_at") else "—"
                    }
                    for i in filtered
                ])
                st.dataframe(table, use_container_width=True, hide_index=True)
                st.caption(f"Showing {len(filtered)} of {len(items)} items — click any column header to sort")

            # Export + Edit (approver only)
            if role == "approver":
                st.divider()
                st.subheader("📤 Export")
                ec1, ec2 = st.columns(2)
                with ec1:
                    buf = io.StringIO()
                    pd.DataFrame([{
                        "Asset Tag": i.get("asset_tag") or "N/A",
                        "Name": i["name"], "Category": i["category"],
                        "Status": i["status"], "Notes": i.get("notes") or ""
                    } for i in filtered]).to_csv(buf, index=False)
                    st.download_button(
                        f"⬇️ Export current view ({len(filtered)})",
                        buf.getvalue(),
                        f"gix_{datetime.now().strftime('%Y%m%d')}.csv",
                        "text/csv"
                    )
                with ec2:
                    buf2 = io.StringIO()
                    pd.DataFrame([{
                        "Asset Tag": i.get("asset_tag") or "N/A",
                        "Name": i["name"], "Category": i["category"],
                        "Status": i["status"], "Notes": i.get("notes") or ""
                    } for i in items]).to_csv(buf2, index=False)
                    st.download_button(
                        f"⬇️ Export full list ({len(items)})",
                        buf2.getvalue(),
                        f"gix_full_{datetime.now().strftime('%Y%m%d')}.csv",
                        "text/csv"
                    )

                st.divider()
                st.subheader("✏️ Edit Item")
                st.caption("Asset tag cannot be changed.")
                tag_options = [f"{i.get('asset_tag', 'N/A')} — {i['name']}" for i in items]
                selected_option = st.selectbox("Select item to edit", ["— select —"] + tag_options)

                if selected_option != "— select —":
                    selected_tag = selected_option.split(" — ")[0]
                    sel = next((i for i in items if i.get("asset_tag") == selected_tag), None)
                    if sel:
                        st.markdown(f"**Asset Tag (locked):** `{sel.get('asset_tag')}`")
                        ec1, ec2 = st.columns(2)
                        with ec1:
                            new_name = st.text_input("Name", value=sel["name"], key="edit_name")
                            new_cat = st.selectbox(
                                "Category",
                                ["Camera", "Audio", "Laptop", "Cable", "Accessory", "Other"],
                                index=["Camera", "Audio", "Laptop", "Cable", "Accessory", "Other"].index(
                                    sel["category"]) if sel["category"] in
                                    ["Camera", "Audio", "Laptop", "Cable", "Accessory", "Other"] else 5,
                                key="edit_cat"
                            )
                        with ec2:
                            new_notes = st.text_input("Notes", value=sel.get("notes") or "", key="edit_notes")

                        bc1, bc2 = st.columns([1, 4])
                        with bc1:
                            if st.button("💾 Save"):
                                try:
                                    supabase.table("equipment").update({
                                        "name": new_name, "category": new_cat, "notes": new_notes
                                    }).eq("id", sel["id"]).execute()
                                    st.success("✅ Updated!")
                                    st.rerun()
                                except Exception as e:
                                    st.error(f"Error: {e}")
                        with bc2:
                            if st.button("🗑️ Delete", type="secondary"):
                                try:
                                    supabase.table("equipment").delete().eq("id", sel["id"]).execute()
                                    st.success("🗑️ Deleted.")
                                    st.rerun()
                                except Exception as e:
                                    st.error(f"Error: {e}")

                # ── REPRINT BARCODE ──
                st.divider()
                st.subheader("🖨️ Reprint Barcode")
                st.caption("Select any item to regenerate and print its barcode.")

                reprint_options = [
                    f"{i.get('asset_tag', 'N/A')} — {i['name']}"
                    for i in items
                    if i.get("asset_tag")
                ]
                selected_reprint = st.selectbox(
                    "Select item",
                    ["— select an item —"] + reprint_options,
                    key="reprint_select"
                )

                if selected_reprint != "— select an item —":
                    reprint_tag = selected_reprint.split(" — ")[0]
                    reprint_item = next(
                        (i for i in items if i.get("asset_tag") == reprint_tag), None
                    )
                    if reprint_item:
                        col_a, col_b = st.columns(2)
                        with col_a:
                            st.write(f"**Name:** {reprint_item['name']}")
                            st.write(f"**Category:** {reprint_item['category']}")
                            st.write(f"**Status:** {reprint_item['status']}")
                            st.write(f"**Asset Tag:** `{reprint_tag}`")
                        with col_b:
                            if st.button("🖨️ Generate Barcode", type="primary", key="reprint_btn"):
                                show_barcode(reprint_tag)

    # ── REQUESTER TABS ────────────────────────────────────────────────────────
    if role == "requester":

        with tab2:
            st.subheader("📝 My Borrow Requests")
            st.markdown("**Request new equipment:**")

            try:
                available = supabase.table("equipment").select("*").eq("status", "available").execute().data
            except Exception as e:
                st.error(f"Could not load equipment: {e}")
                st.stop()

            if not available:
                st.warning("No equipment currently available.")
            else:
                item_options = [f"{i.get('asset_tag', 'N/A')} — {i['name']}" for i in available]
                selected_item = st.selectbox("Select equipment", item_options)
                request_notes = st.text_area("Reason / notes", placeholder="e.g. need for studio project")

                if st.button("📝 Submit Request", type="primary"):
                    try:
                        selected_tag = selected_item.split(" — ")[0]
                        equipment = next(i for i in available if i.get("asset_tag") == selected_tag)
                        supabase.table("borrow_requests").insert({
                            "equipment_id": equipment["id"],
                            "asset_tag": equipment.get("asset_tag"),
                            "equipment_name": equipment["name"],
                            "student_name": user["full_name"],
                            "requested_at": datetime.now().isoformat(),
                            "status": "pending_approval",
                        }).execute()
                        st.success("✅ Request submitted! Waiting for approval.")
                    except Exception as e:
                        st.error(f"Could not submit: {e}")

            st.divider()
            st.markdown("**My request history:**")
            try:
                my_requests = supabase.table("borrow_requests").select("*") \
                    .eq("student_name", user["full_name"]) \
                    .order("requested_at", desc=True).execute().data

                if not my_requests:
                    st.info("You have no borrow requests yet.")
                else:
                    req_df = pd.DataFrame([
                        {
                            "Status": r["status"],
                            "Equipment": r["equipment_name"],
                            "Asset Tag": r.get("asset_tag") or "N/A",
                            "Requested": r.get("requested_at", "")[:16] if r.get("requested_at") else "—",
                            "Approver": r.get("approver_name") or "—",
                            "Approved": r.get("approved_at", "")[:16] if r.get("approved_at") else "—",
                            "Returned": r.get("returned_at", "")[:16] if r.get("returned_at") else "—",
                            "Confirmed": r.get("confirmed_at", "")[:16] if r.get("confirmed_at") else "—",
                        }
                        for r in my_requests
                    ])
                    st.dataframe(req_df, use_container_width=True, hide_index=True)
            except Exception as e:
                st.error(f"Could not load requests: {e}")

        with tab3:
            st.subheader("📦 Return Equipment")
            st.caption("Mark your borrowed equipment as returned. Staff will confirm.")

            try:
                my_approved = supabase.table("borrow_requests").select("*") \
                    .eq("student_name", user["full_name"]) \
                    .eq("status", "approved").execute().data
            except Exception as e:
                st.error(f"Could not load: {e}")
                st.stop()

            if not my_approved:
                st.success("✅ You have no equipment to return!")
            else:
                return_df = pd.DataFrame([
                    {
                        "Asset Tag": r.get("asset_tag") or "N/A",
                        "Equipment": r["equipment_name"],
                        "Checked Out": r.get("approved_at", "")[:16] if r.get("approved_at") else "—",
                    }
                    for r in my_approved
                ])
                st.dataframe(return_df, use_container_width=True, hide_index=True)

                st.divider()
                return_options = [
                    f"{r.get('asset_tag', 'N/A')} — {r['equipment_name']}"
                    for r in my_approved
                ]
                selected_return = st.selectbox("Select item to return", return_options)
                return_notes = st.text_area("Return notes", placeholder="e.g. returned in good condition")

                if st.button("📦 Mark as Returned", type="primary"):
                    try:
                        selected_tag = selected_return.split(" — ")[0]
                        req = next(r for r in my_approved if r.get("asset_tag") == selected_tag)
                        supabase.table("borrow_requests").update({
                            "status": "pending_return",
                            "returned_at": datetime.now().isoformat(),
                        }).eq("id", req["id"]).execute()
                        st.success("✅ Marked as returned! Waiting for staff confirmation.")
                        st.rerun()
                    except Exception as e:
                        st.error(f"Could not update: {e}")

    # ── APPROVER TABS ─────────────────────────────────────────────────────────
    if role == "approver":

        with tab2:
            st.subheader("✅ Approve Borrow Requests")
            st.caption("Select multiple requests and approve or reject them all at once.")

            try:
                pending = supabase.table("borrow_requests").select("*") \
                    .eq("status", "pending_approval").execute().data
            except Exception as e:
                st.error(f"Error: {e}")
                st.stop()

            if not pending:
                st.success("✅ No pending requests!")
            else:
                st.info(f"{len(pending)} request(s) waiting for approval.")

                pending_df = pd.DataFrame([
                    {
                        "Select": False,
                        "Asset Tag": r.get("asset_tag") or "N/A",
                        "Equipment": r["equipment_name"],
                        "Student": r["student_name"],
                        "Requested": r.get("requested_at", "")[:16] if r.get("requested_at") else "—",
                    }
                    for r in pending
                ])

                edited_df = st.data_editor(
                    pending_df,
                    use_container_width=True,
                    hide_index=True,
                    column_config={
                        "Select": st.column_config.CheckboxColumn("Select", default=False)
                    }
                )

                selected_rows = edited_df[edited_df["Select"]]
                selected_tags = selected_rows["Asset Tag"].tolist()
                tag_set = set(str(t) for t in selected_tags)
                selected_requests = [
                    r for r in pending
                    if str(r.get("asset_tag") or "N/A") in tag_set
                ]

                if selected_requests:
                    st.info(f"{len(selected_requests)} request(s) selected.")

                st.text_input(
                    "Note for all selected (optional)",
                    placeholder="e.g. approved for studio project",
                    key="approver_batch_note",
                )

                bc1, bc2 = st.columns(2)
                with bc1:
                    if st.button("✅ Approve Selected", type="primary", disabled=len(selected_requests) == 0):
                        success = 0
                        for req in selected_requests:
                            try:
                                supabase.table("borrow_requests").update({
                                    "status": "approved",
                                    "approver_name": user["full_name"],
                                    "approved_at": datetime.now().isoformat(),
                                }).eq("id", req["id"]).execute()
                                supabase.table("equipment").update({
                                    "status": "checked_out"
                                }).eq("id", req["equipment_id"]).execute()
                                success += 1
                            except Exception as e:
                                st.error(f"Failed for '{req['equipment_name']}': {e}")
                        if success:
                            st.success(f"✅ {success} request(s) approved!")
                            st.rerun()

                with bc2:
                    if st.button("❌ Reject Selected", type="secondary", disabled=len(selected_requests) == 0):
                        success = 0
                        for req in selected_requests:
                            try:
                                supabase.table("borrow_requests").update({
                                    "status": "rejected",
                                    "approver_name": user["full_name"],
                                    "approved_at": datetime.now().isoformat(),
                                }).eq("id", req["id"]).execute()
                                success += 1
                            except Exception as e:
                                st.error(f"Failed for '{req['equipment_name']}': {e}")
                        if success:
                            st.success(f"❌ {success} request(s) rejected!")
                            st.rerun()

        with tab3:
            st.subheader("🔍 Confirm Returns")
            st.caption("Select multiple returns and confirm them all at once.")

            try:
                pending_return = supabase.table("borrow_requests").select("*") \
                    .eq("status", "pending_return").execute().data
            except Exception as e:
                st.error(f"Error: {e}")
                st.stop()

            if not pending_return:
                st.success("✅ No returns waiting for confirmation!")
            else:
                st.info(f"{len(pending_return)} return(s) to confirm.")

                return_df = pd.DataFrame([
                    {
                        "Select": False,
                        "Asset Tag": r.get("asset_tag") or "N/A",
                        "Equipment": r["equipment_name"],
                        "Student": r["student_name"],
                        "Returned At": r.get("returned_at", "")[:16] if r.get("returned_at") else "—",
                    }
                    for r in pending_return
                ])

                edited_return_df = st.data_editor(
                    return_df,
                    use_container_width=True,
                    hide_index=True,
                    column_config={
                        "Select": st.column_config.CheckboxColumn("Select", default=False)
                    }
                )

                selected_return_rows = edited_return_df[edited_return_df["Select"]]
                selected_return_tags = selected_return_rows["Asset Tag"].tolist()
                return_tag_set = set(str(t) for t in selected_return_tags)
                selected_returns = [
                    r for r in pending_return
                    if str(r.get("asset_tag") or "N/A") in return_tag_set
                ]

                if selected_returns:
                    st.info(f"{len(selected_returns)} return(s) selected.")

                st.text_input(
                    "Note for all selected (optional)",
                    placeholder="e.g. all items returned in good condition",
                    key="confirm_batch_note",
                )

                if st.button("🔍 Confirm Selected Returns", type="primary", disabled=len(selected_returns) == 0):
                    success = 0
                    for req in selected_returns:
                        try:
                            supabase.table("borrow_requests").update({
                                "status": "returned",
                                "confirmer_name": user["full_name"],
                                "confirmed_at": datetime.now().isoformat(),
                            }).eq("id", req["id"]).execute()
                            supabase.table("equipment").update({
                                "status": "available",
                                "returned_at": datetime.now().isoformat()
                            }).eq("id", req["equipment_id"]).execute()
                            success += 1
                        except Exception as e:
                            st.error(f"Failed for '{req['equipment_name']}': {e}")
                    if success:
                        st.success(f"✅ {success} return(s) confirmed! Equipment is now available.")
                        st.rerun()

        with tab4:
            st.subheader("📊 All Borrow Requests")
            try:
                all_requests = supabase.table("borrow_requests").select("*") \
                    .order("requested_at", desc=True).execute().data
                if not all_requests:
                    st.info("No requests yet.")
                else:
                    all_statuses = ["All"] + list(set(r["status"] for r in all_requests))
                    filter_status = st.selectbox("Filter by status", all_statuses)
                    filtered_req = all_requests if filter_status == "All" else \
                        [r for r in all_requests if r["status"] == filter_status]

                    st.dataframe(pd.DataFrame([{
                        "Status": r["status"],
                        "Asset Tag": r.get("asset_tag") or "N/A",
                        "Equipment": r["equipment_name"],
                        "Student": r["student_name"],
                        "Requested": r.get("requested_at", "")[:16] if r.get("requested_at") else "—",
                        "Approver": r.get("approver_name") or "—",
                        "Approved": r.get("approved_at", "")[:16] if r.get("approved_at") else "—",
                        "Returned": r.get("returned_at", "")[:16] if r.get("returned_at") else "—",
                        "Confirmed By": r.get("confirmer_name") or "—",
                        "Confirmed": r.get("confirmed_at", "")[:16] if r.get("confirmed_at") else "—",
                    } for r in filtered_req]), use_container_width=True, hide_index=True)
                    st.caption(f"Showing {len(filtered_req)} of {len(all_requests)} requests")
            except Exception as e:
                st.error(f"Could not load: {e}")

        with tab5:
            st.subheader("➕ Add New Equipment")
            st.caption("Use short names — not full Amazon descriptions.")

            name = st.text_input("Item name", placeholder="e.g. Sony A7 Camera")
            category = st.selectbox("Category", ["Camera", "Audio", "Laptop", "Cable", "Accessory", "Other"])
            notes = st.text_input("Notes", placeholder="e.g. Includes charger")

            if st.button("➕ Add Item", type="primary"):
                if not name:
                    st.warning("Please enter a name.")
                else:
                    try:
                        tag = generate_asset_tag()
                        supabase.table("equipment").insert({
                            "name": name, "category": category,
                            "status": "available", "notes": notes,
                            "asset_tag": tag,
                            "returned_at": datetime.now().isoformat()
                        }).execute()
                        st.success(f"✅ '{name}' added! Asset tag: `{tag}`")
                        st.divider()
                        st.markdown("**🏷️ Printable barcode for this item:**")
                        show_barcode(tag)
                    except Exception as e:
                        st.error(f"Error: {e}")

        with tab6:
            st.subheader("📂 Upload Equipment CSV")
            st.caption("Bulk import equipment. Asset tags are auto-generated. Long names are shortened automatically.")
            st.code("name,category,notes\nSony A7 Camera,Camera,Includes battery", language="csv")
            st.info("💡 Do NOT include an asset_tag column — tags are auto-assigned.")

            uploaded_file = st.file_uploader("Choose a CSV file", type="csv")
            if uploaded_file is not None:
                try:
                    content = uploaded_file.read().decode("utf-8")
                    reader = csv.DictReader(io.StringIO(content))
                    rows = list(reader)

                    assert len(rows) > 0, "CSV file is empty"
                    assert "name" in rows[0], "CSV must have a 'name' column"
                    assert "category" in rows[0], "CSV must have a 'category' column"

                    preview = []
                    for row in rows:
                        name = row.get("name", "").strip()
                        original = name
                        if len(name) > 40:
                            name = name[:40].rsplit(" ", 1)[0] + "..."
                        row["name"] = name
                        preview.append({
                            "Original": original,
                            "Shortened": name if name != original else "✅ No change",
                            "Category": row.get("category", "Other"),
                            "Notes": row.get("notes", "") or "—",
                            "Asset Tag": "⚙️ Auto-generated"
                        })

                    st.markdown(f"**Preview — {len(rows)} items:**")
                    st.dataframe(pd.DataFrame(preview), use_container_width=True, hide_index=True)

                    if st.button("⬆️ Import All", type="primary"):
                        ok, fail = 0, 0
                        generated_tags = []
                        for row in rows:
                            try:
                                tag = generate_asset_tag()
                                supabase.table("equipment").insert({
                                    "name": row["name"],
                                    "category": row.get("category", "Other"),
                                    "notes": row.get("notes", ""),
                                    "status": "available",
                                    "asset_tag": tag,
                                    "returned_at": datetime.now().isoformat()
                                }).execute()
                                ok += 1
                                generated_tags.append((row["name"], tag))
                            except Exception as e:
                                fail += 1
                                st.error(f"Failed to insert '{row.get('name')}': {e}")

                        if ok:
                            st.success(f"✅ Imported {ok} items!")
                            st.markdown("**🏷️ Generated barcodes — right-click each to save and print:**")
                            for item_name, tag in generated_tags:
                                st.caption(f"{item_name} — `{tag}`")
                                show_barcode(tag)
                        if fail:
                            st.error(f"❌ {fail} items failed to import.")

                except AssertionError as e:
                    st.error(f"CSV format error: {e}")
                except Exception as e:
                    st.error(f"Could not read file: {e}")

            st.divider()
            sample = "name,category,notes\nSony A7 Camera,Camera,Includes battery and charger\nRode Wireless Mic,Audio,Set of 2 transmitters\nMacBook Pro 14,Laptop,Charger included"
            st.download_button("⬇️ Download template", sample, "template.csv", "text/csv")

# ── ROUTER ────────────────────────────────────────────────────────────────────
if not st.session_state.logged_in:
    show_login()
else:
    show_app()