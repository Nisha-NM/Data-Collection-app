import logging
import os

import streamlit as st

from auth import authenticate_user, register_user
from database import init_db, get_user_by_id
from video_upload import render_video_upload_page
from video_review import render_video_review_page, render_my_submissions_page
from admin_panel import render_admin_dashboard
from analytics import render_analytics_page


logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s - %(message)s",
)
logger = logging.getLogger(__name__)


def ensure_admin_exists() -> None:
    """Create a default admin user if none exists.

    For production, you should manage admin creation separately or via env vars.
    """
    from database import get_user_by_email

    admin_email = os.getenv("ADMIN_EMAIL", "admin@example.com")
    admin_password = os.getenv("ADMIN_PASSWORD", "admin123")

    existing_admin = get_user_by_email(admin_email)
    if existing_admin is None:
        user = register_user(admin_email, admin_password, role="admin")
        if user:
            logger.info("Default admin ensured: %s", admin_email)
        else:
            logger.warning(
                "Could not create default admin user. Email may already exist with different role."
            )


def init_app():
    init_db()
    ensure_admin_exists()


def show_login():
    st.title("Video Feedback Portal")
    st.markdown(
        "A professional platform to upload videos, record voice feedback, and manage manual transcriptions."
    )

    tab_login, tab_register = st.tabs(["Login", "Register"])

    with tab_login:
        with st.form("login_form"):
            email = st.text_input("Email")
            password = st.text_input("Password", type="password")
            submitted = st.form_submit_button("Login")

        if submitted:
            user = authenticate_user(email, password)
            if user:
                st.session_state["user_id"] = user.user_id
                st.session_state["role"] = user.role
                st.experimental_rerun()
            else:
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
            if reg_password != reg_confirm:
                st.error("Passwords do not match.")
            elif not reg_email or not reg_password:
                st.error("Email and password are required.")
            else:
                user = register_user(reg_email, reg_password, role="user")
                if user:
                    st.success("Account created. Please log in.")
                else:
                    st.error("Email already registered or registration failed.")


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
        ),
    )

    if st.sidebar.button("Logout"):
        st.session_state.clear()
        st.experimental_rerun()

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
        render_analytics_page()


def show_admin_dashboard():
    st.sidebar.title("Admin Navigation")
    page = st.sidebar.radio(
        "Go to",
        (
            "Admin Dashboard",
            "Analytics",
        ),
    )

    if st.sidebar.button("Logout"):
        st.session_state.clear()
        st.experimental_rerun()

    if page == "Admin Dashboard":
        render_admin_dashboard()
    elif page == "Analytics":
        render_analytics_page()


def main():
    st.set_page_config(
        page_title="Video Feedback Portal",
        layout="wide",
        initial_sidebar_state="expanded",
    )

    init_app()

    user_id = st.session_state.get("user_id")
    role = st.session_state.get("role")

    if not user_id:
        show_login()
        return

    user = get_user_by_id(user_id)
    if not user:
        st.session_state.clear()
        st.experimental_rerun()
        return

    if role == "admin":
        show_admin_dashboard()
    else:
        show_user_dashboard()


if __name__ == "__main__":
    main()

