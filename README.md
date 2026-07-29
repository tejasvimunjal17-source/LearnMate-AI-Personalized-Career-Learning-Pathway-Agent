# 🧭 LearnMate AI — Career Learning Platform

![Image Alt](https://github.com/tejasvimunjal17-source/LearnMate-AI-Personalized-Career-Learning-Pathway-Generator/blob/main/Learnmate%20AI%20Orchestrate%20Architecture%20Blueprint/LearnMate%20Al%20-%20Orchestrate%20Architecture%20Blueprint.png)

An agentic, AI-powered career learning **SaaS platform** built with
**Python + Streamlit**, using **IBM watsonx.ai** and **IBM Granite**
foundation models to generate fully personalized learning roadmaps,
skill-gap analyses, official course & certification recommendations, and
downloadable PDF/Word reports — wrapped in a premium, responsive,
glassmorphism UI with user accounts backed by **Supabase (PostgreSQL)**,
plus a full **Admin Panel** for platform management and analytics.

![status](https://img.shields.io/badge/status-production--ready-7C5CFF)
![python](https://img.shields.io/badge/python-3.10%2B-22D3B0)
![license](https://img.shields.io/badge/license-MIT-black)

It is built on IBM Cloud using IBM watsonx.ai (Granite models) for roadmap
generation, with Supabase as the application database.

<img src="https://user-images.githubusercontent.com/73097560/115834477-dbab4500-a447-11eb-908a-139a6edaec5c.gif" alt="" style="max-width: 100%; display: inline-block;" data-target="animated-image.originalImage">

Live At : https://learnmate-ai-personalized-career-learning-pathway-generator.streamlit.app/

<img src="https://user-images.githubusercontent.com/73097560/115834477-dbab4500-a447-11eb-908a-139a6edaec5c.gif" alt="" style="max-width: 100%; display: inline-block;" data-target="animated-image.originalImage">

---

## ✨ Features

### For every user
- **Premium Landing Page** — gradient hero, animated badges, feature grid,
  stats cards, footer, and a fixed top navigation bar (with a direct link
  into the Admin Panel).
- **User Registration & Sessions** — First Name, Last Name, Email (with
  empty-field, duplicate-email, and email-format validation), auto-login
  after registration, and a persistent session until logout.
- **Supabase Backend** — every user, resume, roadmap, AI chat exchange,
  resume review, feedback submission, and notification is stored in
  Supabase PostgreSQL, with a normalized relational schema (foreign keys,
  indexes, Row Level Security) instead of a flat spreadsheet. See
  **Database & Migrations** below.
- **My Profile Page** — First/Last Name, Email, Registration Date, Edit
  Profile, Logout — plus a full **History** section:
  - **Resume History** — every resume you've ever saved, with regenerate
    PDF/DOCX download buttons, search, and delete.
  - **Resume Downloads History** — a log of every time you downloaded a
    resume.
  - **AI Chat History** — every AI Mentor conversation, searchable and
    filterable by model, exportable per exchange.
  - **Roadmap History** — every AI-generated roadmap you've received,
    exportable as JSON.
  - All four history views support search, pagination, and a two-step
    confirm-before-delete flow.
- **AI Roadmap Generator** — weekly milestones with key skills,
  mini-projects, practice tasks, and recommended courses, powered by IBM
  Granite models on watsonx.ai (with a deterministic offline fallback).
  Every generated roadmap is persisted to Supabase automatically.
- **Skill-Gap Analysis** — current vs. required skill levels, prioritized,
  with an interactive readiness gauge and gap chart.
- **Course & Certification Recommendations** — curated, hand-picked cards
  with direct official links (IBM SkillsBuild, IBM Training, Coursera, edX,
  Cisco Skills for All, Google Cloud Skills Boost, Microsoft Learn, Kaggle
  Learn, freeCodeCamp, Harvard CS50, DeepLearning.AI, Hugging Face,
  DataCamp, Codecademy), each showing Provider, Duration, Difficulty, and
  Free/Paid status — with "mark completed / earned" tracking that feeds the
  Dashboard.
- **Job Search** — live job listings merged and deduped from RemoteOK,
  Remotive, and Arbeitnow (all free, public, no API key required), with
  fuzzy role/domain matching. Falls back to a small curated sample dataset
  if all three sources are unreachable, so the page never breaks.
- **Free Courses** — a curated directory of free learning resources.
- **Resume Builder** — a full resume creation studio:
  - Multiple visual **templates** with a live preview and an **accent
    color** picker.
  - An **AI Toolkit** (OpenRouter-powered) to generate a professional
    summary, improve individual bullet points, polish grammar, and
    generate a cover letter, LinkedIn "About" section, portfolio blurb, HR
    outreach email, and likely interview questions — all grounded in your
    own resume data.
  - **Resume Settings**: target role, experience level, one-page toggle,
    and an optional profile photo.
  - **ATS Score checker** built in (keyword coverage, completeness,
    duplicate-skill detection) via the same engine as the standalone
    Resume Review page.
  - Every save creates a new version in **Resume History** (nothing is
    ever silently overwritten) and generates downloadable PDF (ReportLab)
    and Word/.docx (python-docx) files on demand.
- **Resume Review** — upload an existing PDF/DOCX resume for an instant
  ATS score, missing-keyword detection, and section-completeness
  feedback.
- **Interactive Dashboard** — Roadmap Progress, Skill Readiness, Study
  Hours, Weekly Progress, Completion %, Certifications Earned, Courses
  Completed, plus Progress Donut / Skill Gap Bar / Weekly Timeline /
  Readiness Gauge charts, **and** a "Your Activity" panel with real,
  Supabase-sourced totals (roadmaps generated, resumes saved, AI
  requests, weekly study hours) and trend charts — clearly separated from
  the session-only progress-tracker charts.
- **Feedback** — rate the platform (1–5 stars), and submit general
  feedback, bug reports, or feature requests, each tracked through a
  Pending → Reviewed → Resolved workflow (with admin replies visible in
  the Admin Panel).
- **Notification Center** — a bell icon with an unread badge; admins can
  broadcast a message to every user or send one to a specific user, and
  you can mark items read individually or all at once.
- **Floating AI Mentor Chatbot** — minimize/maximize, welcome message,
  suggested questions, and persistent chat history. Replies are generated
  via the **OpenRouter** Chat Completions API (model configurable, default
  a free Llama 3.3 model) and fall back to a roadmap-grounded rule-based
  mentor if OpenRouter isn't configured or is unreachable. Every exchange
  is logged to Supabase (prompt, response, model, response time) and
  surfaced in your AI Chat History. Never overlaps the main UI.
- **Downloadable Reports** — full PDF (ReportLab) and Word/.docx
  (python-docx) exports covering Student Profile, Skill Gap, Roadmap,
  Courses, Certifications, and Progress Summary.
- **Premium, Fully Responsive UI** — glassmorphism cards, gradient
  accents, smooth animations, dark/light mode toggle; a custom
  Gmail/Drive-style collapsible sidebar drawer (desktop margin-shift,
  mobile overlay-with-backdrop) shared between the main app and the Admin
  Panel, each with fully independent open/closed state.

### 🛡️ Admin Panel
A complete, separately-authenticated (bcrypt, its own `admin_users`
table — never the same session as a regular user) back office, reachable
from the landing page's top-right "🛠️ Admin Panel" link or the
authenticated sidebar:

- **Dashboard** — live KPI cards (users, resumes, reviews, roadmaps, AI
  responses, feedback) and Plotly charts, all real Supabase counts —
  honest empty states instead of fabricated numbers wherever a table has
  no rows yet.
- **Database Explorer** — one tab per table (Users, Resume Details,
  Resume Reviews, Roadmap Requests, Generated Roadmaps, AI Responses,
  Feedback, Login Logs, User Activity, Announcements, Notifications),
  each with search, column filtering, sorting, pagination, a live row
  count, a manual refresh control, and CSV/Excel export.
- **User Management** — search, view profile, enable/disable an account
  (no hard delete), and inspect a user's resume/roadmap/AI-request
  history.
- **Feedback Management** — search and filter by status/category, move
  items through Pending → Reviewed → Resolved, and reply with a full,
  threaded reply history per item.
- **Announcements** — create/edit/archive/publish banners shown to users
  after login.
- **Notifications** — send broadcast or user-specific notifications, with
  full send history and the ability to retract one.
- **Advanced Analytics** — Daily/Weekly/Monthly Active Users, registration
  and login trend charts, per-feature usage (resumes, reviews, roadmaps,
  AI chat), feedback statistics, notification statistics, most-active
  users, recent activity, and an **Admin Audit Log** (every admin action —
  enabling/disabling a user, replying to feedback, sending a broadcast,
  etc. — is itself logged and summarized here).
- **Export Center** — one-click CSV/Excel export for Users, Resume
  Details, Resume Reviews, AI Responses, Feedback, Notifications,
  Activity Logs, and a flattened Analytics summary, each with a live
  record count.

### Platform-wide
- **User Activity Logging** — login, logout, registration, resume
  generation/download, resume review, AI roadmap generation, AI chatbot
  usage, profile updates, and feedback submissions are all logged to
  Supabase (`user_activity_logs`, `login_logs`), powering both the History
  pages and the Admin Analytics dashboard. Best-effort by design: a
  logging failure never blocks the action it's attached to.
- **Offline Fallback Where It Matters** — watsonx.ai unreachable → a
  deterministic offline roadmap generator; OpenRouter unreachable → a
  rule-based chat fallback; all three free job-board APIs unreachable → a
  small curated sample dataset. The app stays demonstrable even with
  zero external services configured.
- **Secure by Design** — all credentials loaded from environment
  variables / Streamlit secrets, never hard-coded, never logged. The
  Supabase **service role key** is used only by `backend/` modules on the
  server side and is never exposed to the browser. Admin passwords are
  bcrypt-hashed; regular user accounts remain intentionally passwordless
  (email-based), by original product design.

---

## 🏗️ Architecture

```
learnmate-ai/
├── app.py                       # Streamlit entrypoint, session & page router
├── config.py                    # Secure env/secrets loader (watsonx.ai, Supabase, OpenRouter, ...)
├── agent_instructions.py        # 🔧 Customize agent persona/tone/rules here
├── requirements.txt
├── .env.example                 # Template for local credentials
├── database/
│   └── migrations/               # Numbered, idempotent Supabase SQL migrations (001, 002, ...)
├── backend/
│   ├── watsonx_client.py        # IBM watsonx.ai REST client (IAM auth, retries)
│   ├── roadmap_engine.py        # Prompt building, JSON parsing, offline fallback
│   ├── roadmap_store.py         # Persists every generated roadmap to Supabase
│   ├── skill_gap.py             # Skill-gap normalization & scoring
│   ├── recommendations.py       # Curated courses & certifications (official links)
│   ├── free_courses.py          # Free course directory
│   ├── job_search.py            # RemoteOK / Remotive / Arbeitnow job search + fuzzy matching
│   ├── openrouter_client.py     # OpenRouter Chat Completions client (AI Mentor)
│   ├── supabase_client.py       # Core Supabase connection + legacy Sheets-shaped adapter
│   ├── auth.py                  # User registration, login, profile-update logic
│   ├── admin_auth.py            # Admin login (bcrypt), separate session from regular users
│   ├── admin_data.py            # Admin Panel data layer (dashboard, users, feedback, announcements)
│   ├── analytics_data.py        # Advanced Analytics Dashboard queries (DAU/WAU/MAU, trends, ...)
│   ├── export_data.py           # Admin Export Center data layer
│   ├── notification_store.py    # Broadcast/direct notifications, read/unread tracking
│   ├── activity_logger.py       # User + admin activity/login logging
│   ├── feedback_store.py        # User-submitted feedback/ratings/bug reports/feature requests
│   ├── resume_store.py          # Resume domain model + validation
│   ├── resume_details.py        # Direct Supabase access for resume_details
│   ├── resume_generator.py      # PDF/DOCX resume generation (ReportLab / python-docx)
│   ├── resume_templates.py      # Resume template gallery + accent colors
│   ├── resume_ai.py             # AI Toolkit: summaries, bullet polish, cover letters, etc.
│   ├── resume_ats.py            # ATS score, keyword coverage, completeness checks
│   ├── resume_review.py         # Standalone Resume Review (upload → score) engine
│   ├── ai_response_store.py     # AI Mentor chat history persistence
│   ├── responses_store.py       # Persists roadmap-form submissions
│   ├── pdf_report.py            # Full roadmap PDF report generation (ReportLab)
│   ├── docx_report.py           # Full roadmap Word (.docx) report generation (python-docx)
│   ├── sheets_client.py         # ⚠️ Deprecated/unused — kept for reference only (see below)
│   └── logger_setup.py          # Centralized logging
├── frontend/
│   ├── styles.py                # Design system / custom CSS (dark & light, landing, chatbot, sidebar)
│   ├── custom_sidebar.py        # Shared collapsible-drawer sidebar (used by both app & Admin Panel)
│   ├── landing.py               # Landing page + fixed top nav (incl. Admin Panel entry link)
│   ├── auth_page.py             # Registration / login screens
│   ├── profile_page.py          # "My Profile" page + Resume/AI/Roadmap/Downloads History tabs
│   ├── resume_builder.py        # Resume Builder studio (templates, AI Toolkit, live preview)
│   ├── resume_review_page.py    # Standalone Resume Review page
│   ├── job_search_page.py       # Job Search page
│   ├── free_courses_page.py     # Free Courses page
│   ├── feedback_page.py         # User feedback/rating submission page
│   ├── notification_center.py   # Bell icon + unread badge + notification panel
│   ├── chatbot.py               # Floating AI Mentor widget
│   ├── components.py            # Reusable UI components (incl. course/cert cards)
│   ├── charts.py                # Themed Plotly chart builders
│   ├── admin_panel.py           # Admin Panel router + its own sidebar
│   ├── admin_login_page.py      # Admin Login screen
│   ├── admin_dashboard_page.py  # Admin Dashboard (KPIs + charts)
│   ├── admin_database_page.py   # Database Explorer
│   ├── admin_users_page.py      # User Management
│   ├── admin_feedback_page.py   # Feedback Management (with reply threads)
│   ├── admin_notifications_page.py  # Announcement Manager
│   ├── admin_broadcast_page.py  # Notification sender + history
│   ├── admin_analytics_page.py  # Advanced Analytics Dashboard
│   └── admin_export_page.py     # Export Center
├── utils/
│   └── validators.py            # Form input validation
└── data/                        # Legacy local fallback storage (git-ignored) — see note below
```

**Design principles:** modular separation of concerns (backend vs.
frontend vs. config), reusable components, typed dataclasses for the
domain model, defensive error handling at every network boundary, and a
graceful offline fallback at the AI/job-search boundaries so the app is
always demonstrable — while the core application data store (users,
resumes, roadmaps, feedback, activity) is now a single source of truth in
Supabase, with no silent on-disk fallback for that data.

---

## 🚀 Quick Start (Local)

### 1. Clone & install

```bash
git clone https://github.com/<your-username>/learnmate-ai.git
cd learnmate-ai
python -m venv .venv
source .venv/bin/activate   # Windows: .venv\Scripts\activate
pip install -r requirements.txt
```

### 2. Configure your credentials

```bash
cp .env.example .env
```

Edit `.env` and fill in your IBM watsonx.ai details:

```dotenv
WATSONX_API_KEY=your_ibm_cloud_api_key_here
WATSONX_PROJECT_ID=your_watsonx_project_id_here
WATSONX_URL=https://us-south.ml.cloud.ibm.com
WATSONX_MODEL_ID=ibm/granite-3-8b-instruct
WATSONX_API_VERSION=2024-05-01
APP_ENV=development
```

> Where to find these:
> - **API Key**: [IBM Cloud → Manage → Access (IAM) → API Keys](https://cloud.ibm.com/iam/apikeys)
> - **Project ID**: watsonx.ai → your Project → *Manage* tab
> - **Region URL**: matches the region your watsonx.ai project lives in
> - **Model ID**: any Granite (or other) foundation model available in your project

Then configure **Supabase** (required — see below) and, optionally, the
**AI Mentor chatbot** (OpenRouter — see below).

### 3. Run the app

```bash
streamlit run app.py
```

Visit `http://localhost:8501`.

> **AI credentials not configured yet?** The app still runs end-to-end —
> roadmap generation falls back to an offline demo generator, and the AI
> Mentor chatbot falls back to a rule-based mentor grounded in your own
> roadmap data. Supabase, however, is required for accounts, resumes,
> roadmaps, and every other piece of persisted data — see below.

---

## 🗄️ Supabase Setup (Database)

LearnMate AI's application data — users, resumes, roadmaps, resume
reviews, AI chat history, feedback, notifications, activity logs, and the
Admin Panel's own tables — lives entirely in a Supabase PostgreSQL
project. There is no local/offline fallback for this data (unlike the AI
and job-search integrations), so this step is required, not optional.

1. Create a project at [supabase.com](https://supabase.com).
2. In your Supabase project → **SQL Editor**, run every file in
   `database/migrations/`, **in numeric order** (`001_...sql`,
   `002_...sql`, and so on). Each migration is idempotent (`if not
   exists` / `drop constraint if exists` throughout), so re-running one
   by accident is safe.
3. In your Supabase project → **Settings → API**, copy the **Project
   URL** and the **service_role** key (not the `anon` key — the backend
   needs full read/write access and bypasses Row Level Security by
   design, since it never runs in the browser).
4. Add them to `.env`:
   ```dotenv
   SUPABASE_URL=https://your-project-ref.supabase.co
   SUPABASE_SERVICE_ROLE_KEY=your_supabase_service_role_key_here
   ```
5. Create your first Admin Panel login. There is currently no sign-up UI
   for admins by design — run this once from a local Python shell with
   the two env vars above set:
   ```python
   from backend.admin_auth import create_admin_user
   create_admin_user("you@example.com", "a-strong-password", "Jane", "Doe", is_super_admin=True)
   ```

> **Legacy note — Google Sheets:** earlier versions of this project used
> Google Sheets (`backend/sheets_client.py`) as the primary datastore,
> with a local-CSV fallback. That module is fully deprecated and
> **unused at runtime** as of the Supabase migration — it's kept in the
> repository only for historical reference and is not imported anywhere.
> The `GOOGLE_*` variables in `.env.example` are likewise vestigial and
> safe to leave blank.

---

## 💬 AI Mentor Chatbot (OpenRouter)

The floating "AI Mentor" widget is powered by the **OpenRouter** Chat
Completions API — an OpenAI-compatible gateway to many hosted models,
including free-tier options. Configure it in `.env`:

```dotenv
OPENROUTER_API_KEY=your_openrouter_api_key
OPENROUTER_MODEL=meta-llama/llama-3.3-70b-instruct:free
```

Get a key at [openrouter.ai](https://openrouter.ai/keys). Until this is
configured, the widget automatically falls back to a lightweight
rule-based mentor grounded in the logged-in student's own roadmap data
(weekly focus, top skill gaps, certifications, timeline), so it's fully
functional out of the box either way. Every exchange (with or without
OpenRouter configured) is logged to Supabase and shown in the user's own
AI Chat History.

---

## 🔧 Customizing the AI Agent

Open **`agent_instructions.py`**. Every aspect of the agent's behavior is a
plain Python string/dict you can edit directly:

| Section | Purpose |
|---|---|
| `PERSONA` | Who the agent is |
| `TEACHING_STYLE` | How it explains concepts |
| `TONE` | Emotional register of its writing |
| `ROADMAP_STYLE` | Structure/format of generated roadmaps |
| `DOMAIN_SPECIALIZATION` | Per-domain emphasis (add new domains here) |
| `SAFETY_RULES` | Hard constraints the agent must always follow |
| `BEGINNER_GUIDANCE` | Extra scaffolding for beginner students |
| `OUTPUT_SCHEMA_HINT` | The JSON contract the model must return |

To add courses/certifications for a new domain, add an entry to
`backend/recommendations.py`'s `COURSES` / `CERTIFICATIONS` dicts, keyed by
the same domain name used in `DOMAIN_SPECIALIZATION`.

No other file needs to change to retune the roadmap-generation agent's
behavior. (The AI Mentor chatbot and the Resume Builder's AI Toolkit are
separate integrations — see `backend/openrouter_client.py` and
`backend/resume_ai.py` respectively.)

---

## 🔐 Security Notes

- Secrets are **only** read from environment variables / `.env` (local) or
  Streamlit `secrets.toml` (cloud) — never hard-coded, never logged.
- `.env` is git-ignored by default; only `.env.example` (with placeholders)
  is committed.
- The Supabase **service role key** bypasses Row Level Security and is
  used exclusively by `backend/` modules running on the server — it is
  never sent to, or reachable from, the browser/frontend.
- Admin accounts use bcrypt-hashed passwords in a dedicated `admin_users`
  table, with a session (`st.session_state["admin_user"]`) kept
  completely separate from a regular user's session
  (`st.session_state["auth_user"]`) — logging into one never affects the
  other. Regular user accounts remain intentionally passwordless
  (email-based), per the original product design.
- IAM tokens for watsonx.ai are cached in-memory and refreshed
  automatically before expiry.
- All external API calls (watsonx.ai, OpenRouter, Supabase, job boards)
  are wrapped in typed exceptions and retried with exponential backoff on
  transient errors where appropriate.
- Sessions are held only in Streamlit's server-side `session_state` —
  no client-side cookies or local storage are used for auth.

---

## ☁️ Deployment

### Deploy to Streamlit Community Cloud

1. Push this repository to GitHub (see below).
2. Go to [share.streamlit.io](https://share.streamlit.io) → **New app**.
3. Select your repo, branch, and set **Main file path** to `app.py`.
4. Under **Advanced settings → Secrets**, paste:
   ```toml
   WATSONX_API_KEY = "your_ibm_cloud_api_key_here"
   WATSONX_PROJECT_ID = "your_watsonx_project_id_here"
   WATSONX_URL = "https://us-south.ml.cloud.ibm.com"
   WATSONX_MODEL_ID = "ibm/granite-3-8b-instruct"
   WATSONX_API_VERSION = "2024-05-01"
   APP_ENV = "production"

   SUPABASE_URL = "https://your-project-ref.supabase.co"
   SUPABASE_SERVICE_ROLE_KEY = "your_supabase_service_role_key_here"

   OPENROUTER_API_KEY = "your_openrouter_api_key"
   OPENROUTER_MODEL = "meta-llama/llama-3.3-70b-instruct:free"
   ```
5. Click **Deploy**. Streamlit Cloud installs `requirements.txt`
   automatically. Make sure you've already run every SQL migration in
   `database/migrations/` against your Supabase project (see **Supabase
   Setup** above) and created at least one admin account before relying
   on the Admin Panel in production.

### Push to GitHub

```bash
git init
git add .
git commit -m "LearnMate AI: premium AI career learning platform"
git branch -M main
git remote add origin https://github.com/<your-username>/learnmate-ai.git
git push -u origin main
```

> `.env` is git-ignored — double-check it never gets committed. Only
> `.env.example` should be in version control. If you ever run a
> one-off SQL script containing a real plaintext password (e.g. to
> bootstrap an admin account), don't commit that file either — prefer
> creating admin accounts via `backend/admin_auth.create_admin_user(...)`
> from a local shell instead.

### Alternative: IBM Cloud Code Engine / Docker

```dockerfile
FROM python:3.11-slim
WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY . .
EXPOSE 8501
CMD ["streamlit", "run", "app.py", "--server.port=8501", "--server.address=0.0.0.0"]
```

```bash
docker build -t learnmate-ai .
docker run -p 8501:8501 --env-file .env learnmate-ai
```

---

## ⚡ Performance Notes

- The Supabase client is cached per-process (not reconnected on every
  query).
- Roadmap/report generation runs only on explicit form submission, not on
  every rerun.
- Charts are rendered lazily, only on the page that needs them.
- `st.session_state` holds all user/session data — no redundant
  recomputation across reruns.
- User and admin activity logging (`backend/activity_logger.py`) is
  best-effort and non-blocking — a logging failure never delays or breaks
  the action it's attached to.

---

## 🧪 Tech Stack

- **Frontend/App**: Streamlit, streamlit-option-menu, streamlit-extras,
  streamlit-lottie, custom CSS design system (glassmorphism, gradients,
  responsive, collapsible sidebar drawer)
- **AI — Roadmap Generation**: IBM watsonx.ai REST API, IBM Granite
  foundation models
- **AI — Chat & Resume Toolkit**: OpenRouter Chat Completions API
  (model-agnostic; default is a free Llama 3.3 model)
- **Database**: Supabase (PostgreSQL), via the official `supabase-py`
  client
- **Auth**: bcrypt (admin accounts); passwordless, email-based sessions
  for regular users
- **Job Search**: RemoteOK, Remotive, and Arbeitnow public APIs (free, no
  key required)
- **Charts**: Plotly
- **Report Generation**: ReportLab (PDF), python-docx (Word), pypdf
  (PDF text extraction for Resume Review)
- **Data handling**: pandas, openpyxl (Excel export in the Admin Panel)
- **Validation/Config**: python-dotenv, dataclasses
- **Resilience**: tenacity (retries), structured logging

---

## 📄 License

MIT — free to use, modify, and deploy for personal or commercial projects.
