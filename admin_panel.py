import logging
import csv
import io
import os

import streamlit as st

from database import (
    get_all_users,
    get_all_videos,
    get_all_feedback,
    get_video_by_id,
    get_user_by_id,
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

    tab_users, tab_videos, tab_feedback = st.tabs(["Users", "Videos", "Feedback Review"])

    # ── Users Tab ──
    with tab_users:
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
        st.caption(f"Page {user_page + 1} of {total_user_pages} ({len(filtered_users)} users)")
        st.download_button(
            "Export Users as CSV",
            _to_csv_bytes(users_rows),
            file_name="users.csv",
            mime="text/csv",
        )

    # ── Videos Tab ──
    with tab_videos:
        for v in videos:
            with st.container():
                vid_col, info_col = st.columns([2, 1])
                with vid_col:
                    if os.path.exists(v.video_path):
                        st.video(v.video_path)
                    else:
                        st.warning(f"Video file missing: {v.video_path}")
                with info_col:
                    user = get_user_by_id(v.user_id)
                    st.write(f"**{v.title}**")
                    st.write(f"Uploaded by: {user.email if user else 'Unknown'}")
                    st.write(f"Video ID: {v.video_id}")
                    st.caption(f"Uploaded: {v.upload_time}")
                st.markdown("---")

        videos_rows = [
            {
                "Video ID": v.video_id,
                "User ID": v.user_id,
                "Title": v.title,
                "Upload Time": v.upload_time,
            }
            for v in videos
        ]
        st.download_button(
            "Export Videos as CSV",
            _to_csv_bytes(videos_rows),
            file_name="videos.csv",
            mime="text/csv",
        )

    # ── Feedback Review Tab ──
    with tab_feedback:
        status_filter = st.selectbox(
            "Filter by status", ["All", "PENDING", "APPROVED", "REJECTED"], key="admin_fb_filter"
        )
        filtered_feedback = feedback_items
        if status_filter != "All":
            filtered_feedback = [f for f in feedback_items if f.status == status_filter]

        if not filtered_feedback:
            st.info("No feedback found for this filter.")
        else:
            total_fb_pages = max(1, (len(filtered_feedback) + ITEMS_PER_PAGE - 1) // ITEMS_PER_PAGE)
            fb_page = st.number_input("Page", min_value=1, max_value=total_fb_pages, value=1, key="fb_page") - 1
            page_items = _paginate(filtered_feedback, fb_page)
            st.caption(f"Page {fb_page + 1} of {total_fb_pages} ({len(filtered_feedback)} items)")

            for fb in page_items:
                with st.container():
                    # Header row with status
                    status_colors = {"PENDING": "🟡", "APPROVED": "🟢", "REJECTED": "🔴"}
                    user = get_user_by_id(fb.user_id)
                    user_email = user.email if user else "Unknown"

                    st.markdown(
                        f"**Feedback #{fb.feedback_id}** — "
                        f"by **{user_email}** — "
                        f"{status_colors.get(fb.status, '')} {fb.status}"
                    )
                    st.caption(f"Submitted: {fb.created_time}")

                    # Video + Audio + Transcription side by side
                    video_col, detail_col = st.columns([1, 1], gap="large")

                    with video_col:
                        video = get_video_by_id(fb.video_id)
                        if video and os.path.exists(video.video_path):
                            st.video(video.video_path)
                            st.caption(f"Video: {video.title}")
                        else:
                            st.warning("Video file not available.")

                    with detail_col:
                        # Audio playback
                        if fb.voice_file_path:
                            if os.path.exists(fb.voice_file_path):
                                with open(fb.voice_file_path, "rb") as af:
                                    st.audio(af.read(), format="audio/wav")
                            else:
                                st.warning("Audio file missing.")
                        else:
                            st.info("No audio feedback submitted.")

                        # Transcription
                        with st.expander("Transcription", expanded=True):
                            if fb.transcription_text:
                                st.write(fb.transcription_text)
                            else:
                                st.write("_(no text feedback)_")

                    # Approve / Reject buttons for pending items
                    if fb.status == "PENDING":
                        btn_col1, btn_col2, _ = st.columns([1, 1, 3])
                        with btn_col1:
                            if st.button("Approve", key=f"approve_{fb.feedback_id}", type="primary"):
                                try:
                                    update_feedback_status(fb.feedback_id, "APPROVED")
                                    sync_db()
                                    st.success(f"Feedback #{fb.feedback_id} approved.")
                                    st.rerun()
                                except Exception as exc:
                                    logger.exception("Failed to approve: %s", exc)
                                    st.error("Failed to update.")
                        with btn_col2:
                            if st.button("Reject", key=f"reject_{fb.feedback_id}"):
                                try:
                                    update_feedback_status(fb.feedback_id, "REJECTED")
                                    sync_db()
                                    st.success(f"Feedback #{fb.feedback_id} rejected.")
                                    st.rerun()
                                except Exception as exc:
                                    logger.exception("Failed to reject: %s", exc)
                                    st.error("Failed to update.")

                    st.markdown("---")

        st.download_button(
            "Export Feedback as CSV",
            _to_csv_bytes([
                {
                    "Feedback ID": f.feedback_id,
                    "Video ID": f.video_id,
                    "User ID": f.user_id,
                    "Status": f.status,
                    "Created": f.created_time,
                    "Transcription": f.transcription_text,
                }
                for f in feedback_items
            ]),
            file_name="feedback.csv",
            mime="text/csv",
        )
