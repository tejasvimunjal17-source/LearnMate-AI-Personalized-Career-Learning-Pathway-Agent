# 🧭 LearnMate AI — Career Learning Platform

An agentic, AI-powered career learning **SaaS platform** built with
**Python + Streamlit**, using **IBM watsonx.ai** and **IBM Granite**
foundation models to generate fully personalized learning roadmaps,
skill-gap analyses, official course & certification recommendations, and
downloadable PDF/Word reports — wrapped in a premium, responsive,
glassmorphism UI with user accounts backed by **Google Sheets**.

![status](https://img.shields.io/badge/status-production--ready-7C5CFF)
![python](https://img.shields.io/badge/python-3.10%2B-22D3B0)
![license](https://img.shields.io/badge/license-MIT-black)

---

## ✨ Features

- **Premium Landing Page** — gradient hero, animated badges, feature grid,
  stats cards, footer, and a fixed top navigation bar.
- **User Registration & Sessions** — First Name, Last Name, Email (with
  empty-field, duplicate-email, and email-format validation), auto-login
  after registration, and a persistent session until logout.
- **Google Sheets Backend** — registrations saved to **"LearnMate AI Users
  Data"** and every roadmap-form submission saved to **"LearnMate AI Users
  Responses"**, with automatic local-CSV fallback so the app always runs
  end-to-end even before Google credentials are configured.
- **My Profile Page** — view First/Last Name, Email, Registration Date;
  Edit Profile and Logout.
- **AI Roadmap Generator** — weekly milestones with key skills,
  mini-projects, practice tasks, and recommended courses, powered by IBM
  Granite models on watsonx.ai (with a deterministic offline fallback).
- **Skill-Gap Analysis** — current vs. required skill levels, prioritized,
  with an interactive readiness gauge and gap chart.
- **Course & Certification Recommendations** — curated, hand-picked cards
  with direct official links (IBM SkillsBuild, IBM Training, Coursera, edX,
  Cisco Skills for All, Google Cloud Skills Boost, Microsoft Learn, Kaggle
  Learn, freeCodeCamp, Harvard CS50, DeepLearning.AI, Hugging Face,
  DataCamp, Codecademy), each showing Provider, Duration, Difficulty, and
  Free/Paid status — with "mark completed / earned" tracking that feeds the
  Dashboard.
- **Interactive Dashboard** — Roadmap Progress, Skill Readiness, Study
  Hours, Weekly Progress, Completion %, Certifications Earned, Courses
  Completed, plus Progress Donut / Skill Gap Bar / Weekly Timeline /
  Readiness Gauge charts.
- **Floating AI Mentor Chatbot** — minimize/maximize, welcome message,
  suggested questions, chat history; reserves a real integration point for
  **IBM watsonx Orchestrate** (embeds the live agent once configured) and
  falls back to a roadmap-grounded rule-based mentor otherwise. Never
  overlaps the main UI.
- **Downloadable Reports** — full PDF (ReportLab) and Word/.docx
  (python-docx) exports covering Student Profile, Skill Gap, Roadmap,
  Courses, Certifications, and Progress Summary.
- **Premium, Fully Responsive UI** — glassmorphism cards, gradient accents,
  smooth animations, dark/light mode toggle; the sidebar nav collapses into
  Streamlit's native hamburger drawer on mobile/tablet.
- **Offline Fallback Everywhere** — watsonx.ai unreachable → deterministic
  offline roadmap; Google Sheets unreachable → local CSV storage. The app
  is always demonstrable.
- **Secure by Design** — all credentials loaded from environment variables
  / Streamlit secrets, never hard-coded, never logged; PII only ever
  touches Google Sheets or local `./data/` (git-ignored).

---

## 🏗️ Architecture

```
learnmate-ai/
├── app.py                       # Streamlit entrypoint, session & page router
├── config.py                    # Secure env/secrets loader (watsonx.ai, Sheets, Orchestrate)
├── agent_instructions.py        # 🔧 Customize agent persona/tone/rules here
├── requirements.txt
├── .env.example                 # Template for local credentials
├── .streamlit/
│   └── config.toml              # Streamlit theme
├── backend/
│   ├── watsonx_client.py        # IBM watsonx.ai REST client (IAM auth, retries)
│   ├── roadmap_engine.py        # Prompt building, JSON parsing, offline fallback
│   ├── skill_gap.py             # Skill-gap normalization & scoring
│   ├── recommendations.py       # Curated courses & certifications (official links)
│   ├── sheets_client.py         # Google Sheets read/write, local CSV fallback
│   ├── auth.py                  # Registration, login, profile-update logic
│   ├── responses_store.py       # Persists roadmap-form submissions
│   ├── pdf_report.py            # PDF report generation (ReportLab)
│   ├── docx_report.py           # Word (.docx) report generation (python-docx)
│   └── logger_setup.py          # Centralized logging
├── frontend/
│   ├── styles.py                # Design system / custom CSS (dark & light, landing, chatbot)
│   ├── landing.py                # Landing page + fixed top nav
│   ├── auth_page.py             # Registration / login screens
│   ├── profile_page.py          # "My Profile" account page
│   ├── chatbot.py               # Floating AI Mentor widget
│   ├── components.py            # Reusable UI components (incl. course/cert cards)
│   └── charts.py                # Themed Plotly chart builders
├── utils/
│   └── validators.py            # Form input validation
└── data/                        # Local Google Sheets fallback (auto-created, git-ignored)
```

**Design principles:** modular separation of concerns (backend vs.
frontend vs. config), reusable components, typed dataclasses for the
domain model, defensive error handling at every network boundary, and a
graceful offline fallback at *every* external dependency (AI, storage, and
chat) so the app is always demonstrable.

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

(Optional) Configure Google Sheets — see **Google Sheets Setup** below.
(Optional) Configure IBM watsonx Orchestrate — see **AI Mentor Chatbot** below.

### 3. Run the app

```bash
streamlit run app.py
```

Visit `http://localhost:8501`.

> **No credentials configured yet?** The app still runs end-to-end —
> roadmap generation falls back to an offline demo generator, and
> registrations/responses fall back to local CSV storage under `./data/`.

---

## 📊 Google Sheets Setup

1. In [Google Cloud Console](https://console.cloud.google.com/), create a
   project and enable the **Google Sheets API** and **Google Drive API**.
2. Create a **Service Account** → **Keys** → **Add Key** → JSON. Download
   the key file.
3. Share your target spreadsheet(s) with the service account's `client_email`
   as **Editor** (or let the app auto-create them under that account).
4. In `.env`, either:
   ```dotenv
   GOOGLE_SERVICE_ACCOUNT_FILE=/path/to/service-account.json
   ```
   or (recommended for Streamlit Cloud, which can't upload files) paste the
   raw JSON as a single value:
   ```dotenv
   GOOGLE_SERVICE_ACCOUNT_JSON={"type": "service_account", ...}
   ```
5. Sheet names default to `LearnMate AI Users Data` and
   `LearnMate AI Users Responses` — override with `GOOGLE_USERS_SHEET_NAME`
   / `GOOGLE_RESPONSES_SHEET_NAME` if needed.

Without this configured, the app transparently uses local CSV files in
`./data/` instead — identical behavior, zero setup required for a demo.

---

## 💬 AI Mentor Chatbot (IBM watsonx Orchestrate)

The floating "AI Mentor" widget reserves a real integration point for IBM
watsonx Orchestrate. Once you've built and published an Orchestrate agent
with a public/embeddable chat URL, set:

```dotenv
WATSONX_ORCHESTRATE_EMBED_URL=https://your-orchestrate-instance/chat/<agent-id>
WATSONX_ORCHESTRATE_AGENT_ID=your_agent_id
```

Until then, the widget automatically falls back to a lightweight
rule-based mentor grounded in the logged-in student's own roadmap data
(weekly focus, top skill gaps, certifications, timeline), so it's fully
functional out of the box.

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

No other file needs to change to retune the mentor's behavior.

---

## 🔐 Security Notes

- Secrets are **only** read from environment variables / `.env` (local) or
  Streamlit `secrets.toml` (cloud) — never hard-coded, never logged.
- `.env` is git-ignored by default; only `.env.example` (with placeholders)
  is committed. `./data/` (local Sheets fallback, contains PII) is also
  git-ignored.
- IAM tokens are cached in-memory and refreshed automatically before expiry.
- All external API calls (watsonx.ai, Google Sheets) are wrapped in typed
  exceptions and retried with exponential backoff on transient errors.
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

   GOOGLE_SERVICE_ACCOUNT_JSON = '{"type": "service_account", ...}'
   GOOGLE_USERS_SHEET_NAME = "LearnMate AI Users Data"
   GOOGLE_RESPONSES_SHEET_NAME = "LearnMate AI Users Responses"

   WATSONX_ORCHESTRATE_EMBED_URL = ""
   WATSONX_ORCHESTRATE_AGENT_ID = ""
   ```
5. Click **Deploy**. Streamlit Cloud installs `requirements.txt`
   automatically. The app is optimized for the free tier: cached API calls,
   minimal reruns, and lazy chart rendering.

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
> `.env.example` should be in version control.

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

- Google Sheets client and worksheet lookups are cached per-process (not
  re-authorized on every write).
- Roadmap/report generation runs only on explicit form submission, not on
  every rerun.
- Charts are rendered lazily, only on the page that needs them.
- `st.session_state` holds all user/session data — no redundant recomputation
  across reruns.

---

## 🧪 Tech Stack

- **Frontend/App**: Streamlit, streamlit-option-menu, custom CSS design
  system (glassmorphism, gradients, responsive)
- **AI**: IBM watsonx.ai REST API, IBM Granite foundation models, IBM
  watsonx Orchestrate (chatbot)
- **Backend Database**: Google Sheets (gspread + google-auth), local CSV
  fallback
- **Charts**: Plotly
- **Report Generation**: ReportLab (PDF), python-docx (Word)
- **Validation/Config**: python-dotenv, dataclasses
- **Resilience**: tenacity (retries), structured logging

---

## 📄 License

MIT — free to use, modify, and deploy for personal or commercial projects.
