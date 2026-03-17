import io
import logging

import pandas as pd
import streamlit as st

from database import (
    get_all_users,
    get_all_videos,
    get_all_feedback,
    update_feedback_status,
)


logger = logging.getLogger(__name__)


def _to_csv_bytes(df: pd.DataFrame) -> bytes:
    buffer = io.StringIO()
    df.to_csv(buffer, index=False)
    return buffer.getvalue().encode("utf-8")


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

    st.markdown("### Users")
    users_df = pd.DataFrame(
        [
            {
                "User ID": u.user_id,
                "Email": u.email,
                "Role": u.role,
                "Created": u.created_time,
            }
            for u in users
        ]
    )
    st.dataframe(users_df, use_container_width=True)
    st.download_button(
        "Export Users as CSV",
        _to_csv_bytes(users_df),
        file_name="users.csv",
        mime="text/csv",
    )

    st.markdown("### Videos")
    videos_df = pd.DataFrame(
        [
            {
                "Video ID": v.video_id,
                "User ID": v.user_id,
                "Path": v.video_path,
                "Upload Time": v.upload_time,
            }
            for v in videos
        ]
    )
    st.dataframe(videos_df, use_container_width=True)
    st.download_button(
        "Export Videos as CSV",
        _to_csv_bytes(videos_df),
        file_name="videos.csv",
        mime="text/csv",
    )

    st.markdown("### Feedback")
    feedback_df = pd.DataFrame(
        [
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
        ]
    )
    st.dataframe(feedback_df, use_container_width=True)

    col_a, col_b = st.columns(2)
    with col_a:
        selected_feedback_id = st.number_input(
            "Feedback ID to approve/reject", min_value=0, step=1
        )
    with col_b:
        action = st.selectbox("Action", ["Approve", "Reject"])

    if st.button("Submit Review"):
        if selected_feedback_id <= 0:
            st.error("Please enter a valid Feedback ID.")
        else:
            status = "APPROVED" if action == "Approve" else "REJECTED"
            try:
                update_feedback_status(int(selected_feedback_id), status)
                st.success(f"Feedback {selected_feedback_id} marked as {status}.")
            except Exception as exc:
                logger.exception("Failed to update feedback status: %s", exc)
                st.error("Unable to update feedback status.")

    st.download_button(
        "Export Feedback as CSV",
        _to_csv_bytes(feedback_df),
        file_name="feedback.csv",
        mime="text/csv",
    )

