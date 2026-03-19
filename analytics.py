import logging
from typing import Optional

import plotly.express as px
import streamlit as st

from database import get_analytics


logger = logging.getLogger(__name__)


def render_analytics_page(user_id: Optional[int] = None) -> None:
    st.subheader("Analytics Dashboard")

    try:
        data = get_analytics(user_id=user_id)
    except Exception as exc:
        logger.exception("Failed to load analytics: %s", exc)
        st.error("Unable to load analytics.")
        return

    total_videos = data["total_videos"]
    total_feedback = data["total_feedback"]
    avg_length = data["avg_transcription_length"]
    uploads_per_day = data["uploads_per_day"]
    feedback_per_day = data["feedback_per_day"]
    user_activity = data["user_activity"]

    if data["total_users"] is not None:
        c1, c2, c3, c4 = st.columns(4)
        c1.metric("Total Users", data["total_users"])
        c2.metric("Total Videos", total_videos)
        c3.metric("Total Feedback", total_feedback)
        c4.metric("Avg. Transcription Length", f"{avg_length:.1f} chars")
    else:
        c1, c2, c3 = st.columns(3)
        c1.metric("My Videos", total_videos)
        c2.metric("My Feedback", total_feedback)
        c3.metric("Avg. Transcription Length", f"{avg_length:.1f} chars")

    st.markdown("### Daily Uploads")
    if uploads_per_day:
        uploads_days = [str(u.day) for u in uploads_per_day]
        uploads_counts = [int(u.count) for u in uploads_per_day]
        fig_uploads = px.bar(
            x=uploads_days,
            y=uploads_counts,
            labels={"x": "day", "y": "count"},
            title="Uploads per Day",
        )
        st.plotly_chart(fig_uploads, use_container_width=True)
    else:
        st.info("No uploads yet.")

    st.markdown("### Feedback Activity")
    if feedback_per_day:
        feedback_days = [str(f.day) for f in feedback_per_day]
        feedback_counts = [int(f.count) for f in feedback_per_day]
        fig_feedback = px.line(
            x=feedback_days,
            y=feedback_counts,
            labels={"x": "day", "y": "count"},
            title="Feedback Activity per Day",
        )
        st.plotly_chart(fig_feedback, use_container_width=True)
    else:
        st.info("No feedback submitted yet.")

    if user_activity:
        st.markdown("### User Activity")
        user_emails = [u.email for u in user_activity]
        user_counts = [int(u.count) for u in user_activity]
        fig_users = px.bar(
            x=user_emails,
            y=user_counts,
            labels={"x": "email", "y": "count"},
            title="Feedback Count by User",
        )
        st.plotly_chart(fig_users, use_container_width=True)
