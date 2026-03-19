import base64
import logging
import os
from pathlib import Path

import requests

logger = logging.getLogger(__name__)

GITHUB_TOKEN = os.getenv("GITHUB_TOKEN")
GITHUB_REPO = os.getenv("GITHUB_REPO")  # "owner/repo"
GITHUB_BRANCH = os.getenv("GITHUB_BRANCH", "main")
API_BASE = "https://api.github.com"

BASE_DIR = Path(os.path.dirname(os.path.abspath(__file__)))

MAX_FILE_SIZE_MB = 75  # GitHub Contents API limit (~100MB base64 → ~75MB raw)


def is_enabled() -> bool:
    return bool(GITHUB_TOKEN and GITHUB_REPO)


def _headers() -> dict:
    return {
        "Authorization": f"token {GITHUB_TOKEN}",
        "Accept": "application/vnd.github.v3+json",
    }


def _repo_path(local_path: str) -> str:
    """Convert absolute local path to repo-relative path."""
    return str(Path(local_path).relative_to(BASE_DIR)).replace("\\", "/")


def _get_file_sha(repo_path: str):
    """Get SHA of existing file in the repo (needed for updates)."""
    url = f"{API_BASE}/repos/{GITHUB_REPO}/contents/{repo_path}"
    resp = requests.get(url, headers=_headers(), params={"ref": GITHUB_BRANCH})
    if resp.status_code == 200:
        return resp.json().get("sha")
    return None


def push_file(local_path: str, message: str = "Update file") -> bool:
    """Push a local file to the GitHub repo."""
    if not is_enabled():
        return False

    try:
        file_size = os.path.getsize(local_path)
        if file_size > MAX_FILE_SIZE_MB * 1024 * 1024:
            logger.error("File too large for GitHub API: %s (%.1f MB)", local_path, file_size / 1024 / 1024)
            return False

        with open(local_path, "rb") as f:
            content = base64.b64encode(f.read()).decode("utf-8")

        repo_path = _repo_path(local_path)
        url = f"{API_BASE}/repos/{GITHUB_REPO}/contents/{repo_path}"

        data = {
            "message": message,
            "content": content,
            "branch": GITHUB_BRANCH,
        }

        sha = _get_file_sha(repo_path)
        if sha:
            data["sha"] = sha

        resp = requests.put(url, headers=_headers(), json=data)
        if resp.status_code in (200, 201):
            logger.info("Pushed %s to git", repo_path)
            return True
        else:
            logger.error("Failed to push %s: %s %s", repo_path, resp.status_code, resp.text[:200])
            return False
    except Exception as exc:
        logger.exception("Git push failed for %s: %s", local_path, exc)
        return False


def delete_file(local_path: str, message: str = "Delete file") -> bool:
    """Delete a file from the GitHub repo."""
    if not is_enabled():
        return False

    try:
        repo_path = _repo_path(local_path)
        sha = _get_file_sha(repo_path)
        if not sha:
            return True  # already gone

        url = f"{API_BASE}/repos/{GITHUB_REPO}/contents/{repo_path}"
        data = {
            "message": message,
            "sha": sha,
            "branch": GITHUB_BRANCH,
        }
        resp = requests.delete(url, headers=_headers(), json=data)
        if resp.status_code == 200:
            logger.info("Deleted %s from git", repo_path)
            return True
        else:
            logger.error("Failed to delete %s: %s", repo_path, resp.text[:200])
            return False
    except Exception as exc:
        logger.exception("Git delete failed for %s: %s", local_path, exc)
        return False


def sync_db() -> bool:
    """Push the SQLite database to git."""
    from database import DB_PATH
    if os.path.exists(DB_PATH):
        return push_file(DB_PATH, message="Sync database")
    return False
