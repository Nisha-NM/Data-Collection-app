import os
import logging
from contextlib import contextmanager
from datetime import datetime
from typing import Optional, List, Dict, Any

from sqlalchemy import (
    create_engine,
    Column,
    Integer,
    String,
    DateTime,
    ForeignKey,
    Text,
)
from sqlalchemy.orm import declarative_base, relationship, sessionmaker, Session


logger = logging.getLogger(__name__)


DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///app.db")

engine = create_engine(
    DATABASE_URL,
    connect_args={"check_same_thread": False} if DATABASE_URL.startswith("sqlite") else {},
)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()


class User(Base):
    __tablename__ = "users"

    user_id = Column(Integer, primary_key=True, index=True)
    email = Column(String(255), unique=True, index=True, nullable=False)
    password_hash = Column(String(255), nullable=False)
    role = Column(String(50), default="user", nullable=False)
    created_time = Column(DateTime, default=datetime.utcnow, nullable=False)

    videos = relationship("Video", back_populates="user")
    feedback_items = relationship("Feedback", back_populates="user")


class Video(Base):
    __tablename__ = "videos"

    video_id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.user_id"), nullable=False)
    video_path = Column(String(512), nullable=False)
    upload_time = Column(DateTime, default=datetime.utcnow, nullable=False)

    user = relationship("User", back_populates="videos")
    feedback_items = relationship("Feedback", back_populates="video")


class Feedback(Base):
    __tablename__ = "feedback"

    feedback_id = Column(Integer, primary_key=True, index=True)
    video_id = Column(Integer, ForeignKey("videos.video_id"), nullable=False)
    user_id = Column(Integer, ForeignKey("users.user_id"), nullable=False)
    voice_file_path = Column(String(512), nullable=True)
    transcription_text = Column(Text, nullable=False)
    status = Column(String(50), default="PENDING", nullable=False)
    created_time = Column(DateTime, default=datetime.utcnow, nullable=False)

    video = relationship("Video", back_populates="feedback_items")
    user = relationship("User", back_populates="feedback_items")


def init_db() -> None:
    """Create database tables."""
    try:
        Base.metadata.create_all(bind=engine)
        logger.info("Database initialized successfully.")
    except Exception as exc:
        logger.exception("Error initializing database: %s", exc)
        raise


@contextmanager
def get_session() -> Session:
    session: Session = SessionLocal()
    try:
        yield session
        session.commit()
    except Exception as exc:
        session.rollback()
        logger.exception("Database session rollback due to error: %s", exc)
        raise
    finally:
        session.close()


def create_user(email: str, password_hash: str, role: str = "user") -> Optional[User]:
    with get_session() as session:
        if session.query(User).filter_by(email=email).first():
            return None
        user = User(email=email, password_hash=password_hash, role=role)
        session.add(user)
        session.flush()
        return user


def get_user_by_email(email: str) -> Optional[User]:
    with get_session() as session:
        return session.query(User).filter_by(email=email).first()


def get_user_by_id(user_id: int) -> Optional[User]:
    with get_session() as session:
        return session.query(User).filter_by(user_id=user_id).first()


def create_video(user_id: int, video_path: str) -> Video:
    with get_session() as session:
        video = Video(user_id=user_id, video_path=video_path)
        session.add(video)
        session.flush()
        return video


def get_videos_for_user(user_id: int) -> List[Video]:
    with get_session() as session:
        return (
            session.query(Video)
            .filter_by(user_id=user_id)
            .order_by(Video.upload_time.desc())
            .all()
        )


def get_all_videos() -> List[Video]:
    with get_session() as session:
        return session.query(Video).order_by(Video.upload_time.desc()).all()


def get_video_by_id(video_id: int) -> Optional[Video]:
    with get_session() as session:
        return session.query(Video).filter_by(video_id=video_id).first()


def create_feedback(
    video_id: int,
    user_id: int,
    voice_file_path: Optional[str],
    transcription_text: str,
) -> Feedback:
    with get_session() as session:
        fb = Feedback(
            video_id=video_id,
            user_id=user_id,
            voice_file_path=voice_file_path,
            transcription_text=transcription_text,
        )
        session.add(fb)
        session.flush()
        return fb


def get_feedback_for_user(user_id: int) -> List[Feedback]:
    with get_session() as session:
        return (
            session.query(Feedback)
            .filter_by(user_id=user_id)
            .order_by(Feedback.created_time.desc())
            .all()
        )


def get_all_feedback() -> List[Feedback]:
    with get_session() as session:
        return session.query(Feedback).order_by(Feedback.created_time.desc()).all()


def update_feedback_status(feedback_id: int, status: str) -> None:
    with get_session() as session:
        fb = session.query(Feedback).filter_by(feedback_id=feedback_id).first()
        if fb:
            fb.status = status


def get_all_users() -> List[User]:
    with get_session() as session:
        return session.query(User).order_by(User.created_time.desc()).all()


def get_analytics() -> Dict[str, Any]:
    """Return basic analytics metrics."""
    with get_session() as session:
        total_users = session.query(User).count()
        total_videos = session.query(Video).count()
        total_feedback = session.query(Feedback).count()

        from sqlalchemy import func

        avg_length = (
            session.query(func.avg(func.length(Feedback.transcription_text)))
            .scalar()
        )

        uploads_per_day = (
            session.query(
                func.date(Video.upload_time).label("day"),
                func.count(Video.video_id).label("count"),
            )
            .group_by(func.date(Video.upload_time))
            .order_by("day")
            .all()
        )

        feedback_per_day = (
            session.query(
                func.date(Feedback.created_time).label("day"),
                func.count(Feedback.feedback_id).label("count"),
            )
            .group_by(func.date(Feedback.created_time))
            .order_by("day")
            .all()
        )

        user_activity = (
            session.query(
                User.email,
                func.count(Feedback.feedback_id).label("count"),
            )
            .join(Feedback, Feedback.user_id == User.user_id)
            .group_by(User.user_id)
            .order_by(func.count(Feedback.feedback_id).desc())
            .all()
        )

        return {
            "total_users": total_users,
            "total_videos": total_videos,
            "total_feedback": total_feedback,
            "avg_transcription_length": avg_length or 0,
            "uploads_per_day": uploads_per_day,
            "feedback_per_day": feedback_per_day,
            "user_activity": user_activity,
        }

