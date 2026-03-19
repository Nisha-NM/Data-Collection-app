import logging
import csv
import io

import streamlit as st

from database import (
    get_all_users,
    get_all_videos,
    get_all_feedback,
    update_feedback_status,
)
from git_storage import sync_db


logger = logging.getLogger(__name__)

ITEMS_PER_PAGE = 20


def _to_csv_bytes(rows: list[dict]) -> bytes:
    buffer = io.StringIO()
    if not rows:
        return b""
    writer = csv.DictWriter(buffer, fieldnames=list(rows[0].keys()))
    writer.writeheader()
    writer.writerows(rows)
    return buffer.getvalue().encode("utf-8")


def _paginate(items: list, page: int) -> list:
    start = page * ITEMS_PER_PAGE
    return items[start : start + ITEMS_PER_PAGE]


def render_admin_dashboard() -> None:
    st.subheader("Admin Dashboard")

    try:
        users = get_all_users()
        videos = get_all_videos()
        feedback_items = get_all_feedback()
    except Exception as exc:
        logger.exception("Failed to load admin data: %s", exc)
        st.error("Unable to load admin data.")
        return

    col1, col2, col3 = st.columns(3)
    with col1:
        st.metric("Total Users", len(users))
    with col2:
        st.metric("Total Videos", len(videos))
    with col3:
        st.metric("Total Feedback", len(feedback_items))

    # ── Users ──
    st.markdown("### Users")
    user_search = st.text_input("Search users by email", key="admin_user_search")
    filtered_users = users
    if user_search:
        filtered_users = [u for u in users if user_search.lower() in u.email.lower()]

    users_rows = [
        {
            "User ID": u.user_id,
            "Email": u.email,
            "Role": u.role,
            "Created": u.created_time,
        }
        for u in filtered_users
    ]

    total_user_pages = max(1, (len(users_rows) + ITEMS_PER_PAGE - 1) // ITEMS_PER_PAGE)
    user_page = st.number_input("Page", min_value=1, max_value=total_user_pages, value=1, key="user_page") - 1
    st.dataframe(_paginate(users_rows, user_page), use_container_width=True)
    st.caption(f"Showing page {user_page + 1} of {total_user_pages} ({len(filtered_users)} users)")
    st.download_button(
        "Export Users as CSV",
        _to_csv_bytes(users_rows),
        file_name="users.csv",
        mime="text/csv",
    )

    # ── Videos ──
    st.markdown("### Videos")
    videos_rows = [
        {
            "Video ID": v.video_id,
            "User ID": v.user_id,
            "Title": v.title,
            "Path": v.video_path,
            "Upload Time": v.upload_time,
        }
        for v in videos
    ]
    st.dataframe(videos_rows, use_container_width=True)
    st.download_button(
        "Export Videos as CSV",
        _to_csv_bytes(videos_rows),
        file_name="videos.csv",
        mime="text/csv",
    )

    # ── Feedback ──
    st.markdown("### Feedback Review")

    status_filter = st.selectbox("Filter by status", ["All", "PENDING", "APPROVED", "REJECTED"], key="admin_fb_filter")
    filtered_feedback = feedback_items
    if status_filter != "All":
        filtered_feedback = [f for f in feedback_items if f.status == status_filter]

    feedback_rows = [
        {
            "Feedback ID": f.feedback_id,
            "Video ID": f.video_id,
            "User ID": f.user_id,
            "Voice Path": f.voice_file_path,
            "Status": f.status,
            "Created": f.created_time,
            "Transcription": f.transcription_text[:100] + ("..." if len(f.transcription_text) > 100 else ""),
        }
        for f in filtered_feedback
    ]

    total_fb_pages = max(1, (len(feedback_rows) + ITEMS_PER_PAGE - 1) // ITEMS_PER_PAGE)
    fb_page = st.number_input("Page", min_value=1, max_value=total_fb_pages, value=1, key="fb_page") - 1
    st.dataframe(_paginate(feedback_rows, fb_page), use_container_width=True)
    st.caption(f"Showing page {fb_page + 1} of {total_fb_pages} ({len(filtered_feedback)} items)")

    # ── Approve / Reject via selectbox ──
    pending = [f for f in feedback_items if f.status == "PENDING"]
    if pending:
        st.markdown("#### Review Pending Feedback")
        fb_options = {
            f"#{f.feedback_id} — Video #{f.video_id} — {f.transcription_text[:50]}...": f.feedback_id
            for f in pending
        }
        selected_fb_label = st.selectbox("Select feedback to review", list(fb_options.keys()))
        selected_fb_id = fb_options[selected_fb_label]

        selected_fb = next(f for f in pending if f.feedback_id == selected_fb_id)
        with st.expander("Full transcription", expanded=True):
            st.write(selected_fb.transcription_text)

        col_a, col_b = st.columns(2)
        with col_a:
            if st.button("Approve", key="approve_btn", type="primary"):
                try:
                    update_feedback_status(selected_fb_id, "APPROVED")
                    sync_db()
                    st.success(f"Feedback #{selected_fb_id} approved.")
                    st.rerun()
                except Exception as exc:
                    logger.exception("Failed to approve: %s", exc)
                    st.error("Failed to update status.")
        with col_b:
            if st.button("Reject", key="reject_btn"):
                try:
                    update_feedback_status(selected_fb_id, "REJECTED")
                    sync_db()
                    st.success(f"Feedback #{selected_fb_id} rejected.")
                    st.rerun()
                except Exception as exc:
                    logger.exception("Failed to reject: %s", exc)
                    st.error("Failed to update status.")
    else:
        st.info("No pending feedback to review.")

    st.download_button(
        "Export Feedback as CSV",
        _to_csv_bytes([
            {
                "Feedback ID": f.feedback_id,
                "Video ID": f.video_id,
                "User ID": f.user_id,
                "Voice Path": f.voice_file_path,
                "Status": f.status,
                "Created": f.created_time,
                "Transcription": f.transcription_text,
            }
            for f in feedback_items
        ]),
        file_name="feedback.csv",
        mime="text/csv",
    )
