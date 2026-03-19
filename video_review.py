import io
import logging
import os
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
    update_feedback_text,
    Feedback,
    Video,
)
from git_storage import push_file, sync_db


logger = logging.getLogger(__name__)

BASE_DIR = Path(os.path.dirname(os.path.abspath(__file__)))
VOICE_DIR = BASE_DIR / "data" / "voice_feedback"
VOICE_DIR.mkdir(parents=True, exist_ok=True)


def _save_voice_file(audio_segment) -> Optional[str]:
    """Export an AudioSegment to a WAV file and return the path."""
    try:
        filename = f"{uuid.uuid4().hex}.wav"
        path = VOICE_DIR / filename
        audio_segment.export(str(path), format="wav")
        return str(path)
    except Exception as exc:
        logger.exception("Failed to save voice recording: %s", exc)
        return None


def _audio_segment_to_bytes(audio_segment) -> bytes:
    """Convert an AudioSegment to WAV bytes for st.audio playback."""
    buf = io.BytesIO()
    audio_segment.export(buf, format="wav")
    return buf.getvalue()


def render_video_review_page(current_user_id: int) -> None:
    st.subheader("Video Review & Feedback")

    try:
        user_videos = get_videos_for_user(current_user_id)
    except Exception as exc:
        logger.exception("Failed to load videos for review: %s", exc)
        st.error("Unable to load your videos.")
        return

    if not user_videos:
        st.info("You have no videos to review yet. Please upload a video first.")
        return

    video_options = {
        f"{v.title} (uploaded {v.upload_time:%Y-%m-%d %H:%M})": v.video_id
        for v in user_videos
    }
    selected_label = st.selectbox("Select a video to review", list(video_options.keys()))
    selected_video_id = video_options[selected_label]

    video: Optional[Video] = get_video_by_id(selected_video_id)
    if not video:
        st.error("Selected video not found.")
        return

    # ── Side-by-side: video on left, feedback form on right ──
    video_col, feedback_col = st.columns([1, 1], gap="large")

    with video_col:
        st.markdown("#### Video")
        st.video(video.video_path)
        st.caption(f"{video.title} — uploaded {video.upload_time}")

    with feedback_col:
        st.markdown("#### Record Audio Feedback")
        audio = audiorecorder(
            start_prompt="Click to record",
            stop_prompt="Click to stop recording",
            pause_prompt="",
        )

        has_audio = len(audio) > 0
        if has_audio:
            wav_bytes = _audio_segment_to_bytes(audio)
            st.audio(wav_bytes, format="audio/wav")
            st.success("Audio recorded. You can re-record by clicking again.")

        st.markdown("#### Text Feedback")
        transcription_text = st.text_area(
            "Write your feedback / transcription here.",
            height=200,
            placeholder="Type your feedback about the video...",
        )

        st.markdown("---")

        if st.button("Save Feedback", type="primary", use_container_width=True):
            if not transcription_text.strip() and not has_audio:
                st.error("Please provide audio feedback, text feedback, or both.")
                return
            try:
                voice_path = None
                if has_audio:
                    voice_path = _save_voice_file(audio)
                    if voice_path:
                        push_file(voice_path, "Upload voice feedback")

                create_feedback(
                    video_id=video.video_id,
                    user_id=current_user_id,
                    voice_file_path=voice_path,
                    transcription_text=transcription_text.strip() if transcription_text.strip() else "",
                )
                sync_db()
                st.success("Feedback saved successfully!")
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

    status_filter = st.selectbox("Filter by status", ["All", "PENDING", "APPROVED", "REJECTED"])
    if status_filter != "All":
        feedback_items = [fb for fb in feedback_items if fb.status == status_filter]

    for fb in feedback_items:
        with st.container():
            col1, col2 = st.columns([3, 1])
            with col1:
                st.write(f"**Feedback #{fb.feedback_id}** — Video #{fb.video_id}")
                status_colors = {"PENDING": "🟡", "APPROVED": "🟢", "REJECTED": "🔴"}
                st.write(f"Status: {status_colors.get(fb.status, '')} {fb.status}")
                st.caption(f"Submitted: {fb.created_time}")
            with col2:
                if fb.voice_file_path:
                    try:
                        with open(fb.voice_file_path, "rb") as f:
                            st.audio(f.read(), format="audio/wav")
                    except FileNotFoundError:
                        st.warning("Voice file missing.")

            with st.expander("View / Edit transcription"):
                if fb.status == "PENDING":
                    new_text = st.text_area(
                        "Transcription",
                        value=fb.transcription_text,
                        key=f"edit_fb_{fb.feedback_id}",
                        height=150,
                    )
                    if st.button("Save Changes", key=f"save_fb_{fb.feedback_id}"):
                        if new_text.strip():
                            if update_feedback_text(fb.feedback_id, new_text.strip()):
                                sync_db()
                                st.success("Transcription updated.")
                                st.rerun()
                            else:
                                st.error("Could not update. Feedback may no longer be pending.")
                        else:
                            st.error("Transcription cannot be empty.")
                else:
                    st.write(fb.transcription_text)
            st.markdown("---")
