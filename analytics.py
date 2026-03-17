import logging

import pandas as pd
import plotly.express as px
import streamlit as st

from database import get_analytics


logger = logging.getLogger(__name__)


def render_analytics_page() -> None:
    st.subheader("Analytics Dashboard")

    try:
        data = get_analytics()
    except Exception as exc:
        logger.exception("Failed to load analytics: %s", exc)
        st.error("Unable to load analytics.")
        return

    total_users = data["total_users"]
    total_videos = data["total_videos"]
    total_feedback = data["total_feedback"]
    avg_length = data["avg_transcription_length"]
    uploads_per_day = data["uploads_per_day"]
    feedback_per_day = data["feedback_per_day"]
    user_activity = data["user_activity"]

    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Total Users", total_users)
    c2.metric("Total Videos", total_videos)
    c3.metric("Total Feedback", total_feedback)
    c4.metric("Avg. Transcription Length", f"{avg_length:.1f} chars")

    st.markdown("### Daily Uploads")
    if uploads_per_day:
        df_uploads = pd.DataFrame(
            [{"day": u.day, "count": u.count} for u in uploads_per_day]
        )
        fig_uploads = px.bar(df_uploads, x="day", y="count", title="Uploads per Day")
        st.plotly_chart(fig_uploads, use_container_width=True)
    else:
        st.info("No uploads yet.")

    st.markdown("### Feedback Activity")
    if feedback_per_day:
        df_feedback = pd.DataFrame(
            [{"day": f.day, "count": f.count} for f in feedback_per_day]
        )
        fig_feedback = px.line(
            df_feedback, x="day", y="count", title="Feedback Activity per Day"
        )
        st.plotly_chart(fig_feedback, use_container_width=True)
    else:
        st.info("No feedback submitted yet.")

    st.markdown("### User Activity")
    if user_activity:
        df_users = pd.DataFrame(
            [{"email": u.email, "count": u.count} for u in user_activity]
        )
        fig_users = px.bar(
            df_users, x="email", y="count", title="Feedback Count by User"
        )
        st.plotly_chart(fig_users, use_container_width=True)
    else:
        st.info("No user activity yet.")

