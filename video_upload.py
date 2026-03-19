import logging
import os
import uuid
from pathlib import Path

import streamlit as st

from database import create_video, get_videos_for_user, delete_video
from git_storage import push_file, delete_file, sync_db


logger = logging.getLogger(__name__)

BASE_DIR = Path(os.path.dirname(os.path.abspath(__file__)))
VIDEOS_DIR = BASE_DIR / "data" / "videos"
VIDEOS_DIR.mkdir(parents=True, exist_ok=True)

ALLOWED_VIDEO_TYPES = ("video/mp4", "video/quicktime", "video/x-matroska", "video/webm")
MAX_FILE_SIZE_MB = 75  # GitHub API limit


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

    title = st.text_input("Video Title", value="", placeholder="Give your video a name")

    if uploaded_file is not None:
        if uploaded_file.type not in ALLOWED_VIDEO_TYPES:
            st.error("Unsupported video format.")
            return

        file_size_mb = uploaded_file.size / (1024 * 1024)
        if file_size_mb > MAX_FILE_SIZE_MB:
            st.error(f"File too large. Maximum size is {MAX_FILE_SIZE_MB} MB (GitHub API limit).")
            return

        st.caption(f"File size: {file_size_mb:.1f} MB")

        if st.button("Upload"):
            try:
                video_path = save_video_file(uploaded_file)
                video_title = title.strip() if title.strip() else uploaded_file.name
                create_video(user_id=current_user_id, video_path=video_path, title=video_title)
                push_file(video_path, f"Upload video: {video_title}")
                sync_db()
                st.success("Video uploaded successfully.")
            except Exception as exc:
                logger.exception("Video upload failed: %s", exc)
                st.error("Failed to upload video. Please try again.")

    st.markdown("---")
    st.subheader("My Uploaded Videos")

    search = st.text_input("Search videos", placeholder="Filter by title...", key="video_search")

    try:
        videos = get_videos_for_user(current_user_id)
    except Exception as exc:
        logger.exception("Failed to fetch videos for user: %s", exc)
        st.error("Unable to load videos.")
        return

    if not videos:
        st.info("You have not uploaded any videos yet.")
        return

    if search:
        videos = [v for v in videos if search.lower() in v.title.lower()]

    for video in videos:
        with st.container():
            col1, col2 = st.columns([4, 1])
            with col1:
                st.write(f"**{video.title}** (ID: {video.video_id})")
                st.video(video.video_path)
                st.caption(f"Uploaded: {video.upload_time}")
            with col2:
                if st.button("Delete", key=f"del_video_{video.video_id}"):
                    try:
                        delete_file(video.video_path, f"Delete video: {video.title}")
                        if os.path.exists(video.video_path):
                            os.remove(video.video_path)
                        delete_video(video.video_id)
                        sync_db()
                        st.success("Video deleted.")
                        st.rerun()
                    except Exception as exc:
                        logger.exception("Failed to delete video: %s", exc)
                        st.error("Failed to delete video.")
            st.markdown("---")
