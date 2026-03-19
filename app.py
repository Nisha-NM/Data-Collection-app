import logging
import os
from datetime import datetime, timezone

import streamlit as st
from dotenv import load_dotenv

load_dotenv()

from auth import authenticate_user, register_user, validate_email, validate_password, change_password
from database import init_db, get_user_by_id
from video_upload import render_video_upload_page
from video_review import render_video_review_page, render_my_submissions_page
from admin_panel import render_admin_dashboard
from analytics import render_analytics_page
from git_storage import is_enabled as git_enabled, sync_db


logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s - %(message)s",
)
logger = logging.getLogger(__name__)

MAX_LOGIN_ATTEMPTS = 5
LOCKOUT_SECONDS = 300


@st.cache_resource
def _init_once():
    init_db()
    _ensure_admin_exists()
    if git_enabled():
        logger.info("Git storage enabled (repo: %s)", os.getenv("GITHUB_REPO"))
    else:
        logger.info("Git storage disabled — running in local-only mode")
    return True


def _ensure_admin_exists() -> None:
    from database import get_user_by_email

    admin_email = os.getenv("ADMIN_EMAIL", "admin@example.com")
    admin_password = os.getenv("ADMIN_PASSWORD", "admin123")

    if admin_email == "admin@example.com":
        logger.warning(
            "Using default admin credentials. Set ADMIN_EMAIL and ADMIN_PASSWORD env vars for production."
        )

    existing_admin = get_user_by_email(admin_email)
    if existing_admin is None:
        user = register_user(admin_email, admin_password, role="admin")
        if user:
            logger.info("Default admin ensured: %s", admin_email)
            sync_db()


def _check_rate_limit() -> bool:
    attempts = st.session_state.get("login_attempts", [])
    now = datetime.now(timezone.utc)
    recent = [t for t in attempts if (now - t).total_seconds() < LOCKOUT_SECONDS]
    st.session_state["login_attempts"] = recent
    return len(recent) < MAX_LOGIN_ATTEMPTS


def _record_failed_attempt():
    if "login_attempts" not in st.session_state:
        st.session_state["login_attempts"] = []
    st.session_state["login_attempts"].append(datetime.now(timezone.utc))


def show_login():
    st.title("Video Feedback Portal")
    st.markdown(
        "A professional platform to upload videos, record voice feedback, and manage manual transcriptions."
    )

    tab_login, tab_register = st.tabs(["Login", "Register"])

    with tab_login:
        if not _check_rate_limit():
            st.error(f"Too many failed attempts. Please wait {LOCKOUT_SECONDS // 60} minutes.")
            return

        with st.form("login_form"):
            email = st.text_input("Email")
            password = st.text_input("Password", type="password")
            submitted = st.form_submit_button("Login")

        if submitted:
            user = authenticate_user(email, password)
            if user:
                st.session_state["user_id"] = user.user_id
                st.session_state["role"] = user.role
                st.session_state["login_attempts"] = []
                st.rerun()
            else:
                _record_failed_attempt()
                st.error("Invalid credentials.")

    with tab_register:
        with st.form("register_form"):
            reg_email = st.text_input("Email", key="reg_email")
            reg_password = st.text_input("Password", type="password", key="reg_pwd")
            reg_confirm = st.text_input(
                "Confirm Password", type="password", key="reg_confirm"
            )
            reg_submitted = st.form_submit_button("Create Account")

        if reg_submitted:
            email_err = validate_email(reg_email)
            if email_err:
                st.error(email_err)
            elif reg_password != reg_confirm:
                st.error("Passwords do not match.")
            else:
                pwd_err = validate_password(reg_password)
                if pwd_err:
                    st.error(pwd_err)
                else:
                    user = register_user(reg_email, reg_password, role="user")
                    if user:
                        sync_db()
                        st.success("Account created. Please log in.")
                    else:
                        st.error("Email already registered or registration failed.")


def show_profile_page():
    st.subheader("My Profile")
    user = get_user_by_id(st.session_state["user_id"])
    if not user:
        st.error("User not found.")
        return

    st.write(f"**Email:** {user.email}")
    st.write(f"**Role:** {user.role}")
    st.write(f"**Joined:** {user.created_time}")

    st.markdown("### Change Password")
    with st.form("change_password_form"):
        old_pwd = st.text_input("Current Password", type="password")
        new_pwd = st.text_input("New Password", type="password")
        confirm_pwd = st.text_input("Confirm New Password", type="password")
        submitted = st.form_submit_button("Update Password")

    if submitted:
        if new_pwd != confirm_pwd:
            st.error("New passwords do not match.")
        else:
            error = change_password(st.session_state["user_id"], old_pwd, new_pwd)
            if error:
                st.error(error)
            else:
                sync_db()
                st.success("Password updated successfully.")


def show_user_dashboard():
    st.sidebar.title("Navigation")
    page = st.sidebar.radio(
        "Go to",
        (
            "Dashboard",
            "Upload Video",
            "Video Review",
            "My Submissions",
            "Analytics",
            "Profile",
        ),
    )

    if st.sidebar.button("Logout"):
        st.session_state.clear()
        st.rerun()

    if page == "Dashboard":
        st.title("User Dashboard")
        st.write("Welcome to your video feedback workspace.")
        st.markdown(
            """
        - Upload new videos for review.
        - Record voice feedback and write manual transcriptions.
        - Track your submissions and their approval status.
        """
        )
    elif page == "Upload Video":
        render_video_upload_page(st.session_state["user_id"])
    elif page == "Video Review":
        render_video_review_page(st.session_state["user_id"])
    elif page == "My Submissions":
        render_my_submissions_page(st.session_state["user_id"])
    elif page == "Analytics":
        render_analytics_page(user_id=st.session_state["user_id"])
    elif page == "Profile":
        show_profile_page()


def show_admin_dashboard():
    st.sidebar.title("Admin Navigation")
    page = st.sidebar.radio(
        "Go to",
        (
            "Admin Dashboard",
            "Analytics",
            "Profile",
        ),
    )

    if st.sidebar.button("Logout"):
        st.session_state.clear()
        st.rerun()

    if page == "Admin Dashboard":
        render_admin_dashboard()
    elif page == "Analytics":
        render_analytics_page()
    elif page == "Profile":
        show_profile_page()


def main():
    st.set_page_config(
        page_title="Video Feedback Portal",
        layout="wide",
        initial_sidebar_state="expanded",
    )

    _init_once()

    user_id = st.session_state.get("user_id")
    role = st.session_state.get("role")

    if not user_id:
        show_login()
        return

    user = get_user_by_id(user_id)
    if not user:
        st.session_state.clear()
        st.rerun()
        return

    if role == "admin":
        show_admin_dashboard()
    else:
        show_user_dashboard()


if __name__ == "__main__":
    main()
