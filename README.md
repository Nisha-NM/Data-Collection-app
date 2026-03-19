## Video Feedback Web Application

Professional video feedback platform built with **Python** and **Streamlit**.  
Users can upload videos, record voice feedback, and write manual transcriptions.  
Admins can review all submissions, approve/reject them, and export data as CSV.

### Features

- **Authentication**
  - Email/password login with **hashed passwords** (bcrypt)
  - Two roles: `user` and `admin`
- **User capabilities**
  - Upload videos (stored in `videos/`)
  - See only their own videos
  - Record voice feedback (stored in `voice_feedback/`)
  - Write and edit manual transcription before saving
  - View all their submissions and approval status
- **Admin capabilities**
  - Admin dashboard with all users, videos, and feedback
  - Approve / reject feedback submissions
  - Export users, videos, and feedback as CSV
- **Analytics**
  - Total users, videos, feedback
  - Average transcription length
  - Uploads per day
  - Feedback activity per day
  - User activity (feedback count per user)
  - Interactive charts using **Plotly** and **Pandas**
- **UI**
  - Professional multi-page layout
  - Clean dashboards using cards, tables, and charts
  - Responsive Streamlit layout

### Project Structure

- `app.py` – Main Streamlit app, routing, and layout
- `auth.py` – Authentication and password hashing
- `database.py` – SQLAlchemy models and data access helpers
- `video_upload.py` – Video upload page
- `video_review.py` – Video review & "My Submissions" pages
- `admin_panel.py` – Admin dashboard and CSV export
- `analytics.py` – Analytics dashboard and charts
- `requirements.txt` – Python dependencies

### Database

- Default: **SQLite** file `app.db` in the project root.
- Optional: **PostgreSQL** via `DATABASE_URL` (SQLAlchemy URL), e.g.:
  - `postgresql+psycopg2://user:password@host:5432/dbname`

Tables:

- `users` – `user_id`, `email`, `password_hash`, `role`, `created_time`
- `videos` – `video_id`, `user_id`, `video_path`, `upload_time`
- `feedback` – `feedback_id`, `video_id`, `user_id`, `voice_file_path`, `transcription_text`, `status`, `created_time`

### Local Development

1. Create and activate a virtual environment (optional but recommended).
2. Install dependencies:

```bash
pip install -r requirements.txt
```

3. Run the Streamlit app:

```bash
streamlit run app.py
```

4. Open the URL shown in the terminal (usually `http://localhost:8501`).

On first startup:

- The database schema is created automatically.
- A default admin account is created if there are no users:
  - Email: `admin@example.com`
  - Password: `admin123`
  - You can override these with environment variables `ADMIN_EMAIL` and `ADMIN_PASSWORD`.

### Deployment on Streamlit Community Cloud

1. Push this project to a **GitHub** repository.
2. Ensure `requirements.txt` is committed.
3. On Streamlit Community Cloud, create a new app:
   - Point to `app.py` as the entrypoint.
4. (Optional) Add environment variables:
   - `DATABASE_URL` – to use PostgreSQL instead of SQLite.
   - `ADMIN_EMAIL` / `ADMIN_PASSWORD` – to control the initial admin.
5. Deploy the app; Streamlit Cloud installs from `requirements.txt` automatically.

### Security Notes

- Passwords are never stored in plain text; they are hashed with **bcrypt**.
- Users can only see and operate on **their own videos and feedback**.
- Admins have full visibility and control over all records.

