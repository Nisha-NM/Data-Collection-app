import logging
import os
import uuid
from pathlib import Path

import streamlit as st

from database import create_video, get_videos_for_user, Video


logger = logging.getLogger(__name__)


VIDEOS_DIR = Path("videos")
VIDEOS_DIR.mkdir(exist_ok=True)


ALLOWED_VIDEO_TYPES = ("video/mp4", "video/quicktime", "video/x-matroska", "video/webm")


def save_video_file(uploaded_file) -> str:
    ext = os.path.splitext(uploaded_file.name)[1]
    filename = f"{uuid.uuid4().hex}{ext}"
    file_path = VIDEOS_DIR / filename
    with open(file_path, "wb") as f:
        f.write(uploaded_file.getbuffer())
    return str(file_path)


def render_video_upload_page(current_user_id: int) -> None:
    st.subheader("Upload Video")
    st.write("Upload a video for which you want to record feedback.")

    uploaded_file = st.file_uploader(
        "Choose a video file",
        type=["mp4", "mov", "mkv", "webm"],
        accept_multiple_files=False,
    )

    if uploaded_file is not None:
        if uploaded_file.type not in ALLOWED_VIDEO_TYPES:
            st.error("Unsupported video format.")
            return

        if st.button("Upload"):
            try:
                video_path = save_video_file(uploaded_file)
                create_video(user_id=current_user_id, video_path=video_path)
                st.success("Video uploaded successfully.")
            except Exception as exc:
                logger.exception("Video upload failed: %s", exc)
                st.error("Failed to upload video. Please try again.")

    st.markdown("---")
    st.subheader("My Uploaded Videos")
    try:
        videos = get_videos_for_user(current_user_id)
    except Exception as exc:
        logger.exception("Failed to fetch videos for user: %s", exc)
        st.error("Unable to load videos.")
        return

    if not videos:
        st.info("You have not uploaded any videos yet.")
        return

    for video in videos:
        with st.container():
            st.write(f"Video ID: {video.video_id}")
            st.video(video.video_path)
            st.caption(f"Uploaded at: {video.upload_time}")
            st.markdown("---")

