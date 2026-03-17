import logging
from pathlib import Path
from typing import Optional
import uuid

import streamlit as st
from audiorecorder import audiorecorder

from database import (
    get_videos_for_user,
    get_video_by_id,
    create_feedback,
    get_feedback_for_user,
    Feedback,
    Video,
)


logger = logging.getLogger(__name__)


VOICE_DIR = Path("voice_feedback")
VOICE_DIR.mkdir(exist_ok=True)


def _save_voice_file(audio_bytes) -> Optional[str]:
    try:
        filename = f"{uuid.uuid4().hex}.wav"
        path = VOICE_DIR / filename
        with open(path, "wb") as f:
            f.write(audio_bytes)
        return str(path)
    except Exception as exc:
        logger.exception("Failed to save voice recording: %s", exc)
        return None


def render_video_review_page(current_user_id: int) -> None:
    st.subheader("Video Review")

    try:
        user_videos = get_videos_for_user(current_user_id)
    except Exception as exc:
        logger.exception("Failed to load videos for review: %s", exc)
        st.error("Unable to load your videos.")
        return

    if not user_videos:
        st.info("You have no videos to review yet. Please upload a video first.")
        return

    video_options = {f"ID {v.video_id} - {v.video_path}": v.video_id for v in user_videos}
    selected_label = st.selectbox("Select a video to review", list(video_options.keys()))
    selected_video_id = video_options[selected_label]

    video: Optional[Video] = get_video_by_id(selected_video_id)
    if not video:
        st.error("Selected video not found.")
        return

    st.video(video.video_path)

    st.markdown("### Voice Feedback")
    st.write("Use your microphone to record voice feedback.")

    audio = audiorecorder("Record", "Stop")

    audio_bytes = None
    if len(audio) > 0:
        audio_bytes = audio.tobytes()
        st.audio(audio_bytes, format="audio/wav")

    st.markdown("### Manual Transcription")

    transcription_text = st.text_area(
        "Write or edit your transcription here before saving.",
        height=250,
    )

    if st.button("Save Feedback"):
        if not transcription_text.strip():
            st.error("Transcription cannot be empty.")
            return
        try:
            voice_path = _save_voice_file(audio_bytes) if audio_bytes else None
            create_feedback(
                video_id=video.video_id,
                user_id=current_user_id,
                voice_file_path=voice_path,
                transcription_text=transcription_text.strip(),
            )
            st.success("Feedback saved successfully.")
        except Exception as exc:
            logger.exception("Failed to save feedback: %s", exc)
            st.error("Unable to save feedback. Please try again.")


def render_my_submissions_page(current_user_id: int) -> None:
    st.subheader("My Submissions")

    try:
        feedback_items = get_feedback_for_user(current_user_id)
    except Exception as exc:
        logger.exception("Failed to load submissions: %s", exc)
        st.error("Unable to load your submissions.")
        return

    if not feedback_items:
        st.info("You have not submitted any feedback yet.")
        return

    for fb in feedback_items:
        with st.container():
            st.write(f"Feedback ID: {fb.feedback_id}")
            st.write(f"Video ID: {fb.video_id}")
            st.write(f"Status: {fb.status}")
            st.caption(f"Submitted at: {fb.created_time}")
            if fb.voice_file_path:
                try:
                    with open(fb.voice_file_path, "rb") as f:
                        st.audio(f.read(), format="audio/wav")
                except FileNotFoundError:
                    st.warning("Voice recording file is missing.")
            with st.expander("View transcription"):
                st.write(fb.transcription_text)
            st.markdown("---")

