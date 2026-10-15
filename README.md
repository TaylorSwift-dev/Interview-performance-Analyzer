# AI Interview Performance Analyzer
### Full-Stack AI Interview Preparation Platform

> **Prepare Smarter. Interview Better.**  
> A modern, full-stack AI interview preparation and evaluation platform designed for students, job candidates, and campus interviewers. Built with Flask, SQLite / Supabase PostgreSQL, Chart.js, and Google Gemini AI.

---

## 🌟 Key Platform Features

### 1. 🧮 Aptitude Practice Room
- **4 Core Aptitude Domains:** Quantitative Aptitude, Logical Reasoning, Verbal Ability, and Data Interpretation.
- **Multiple Test Presets:** Quick 5-Question Sprint, Standard 10-Question Test, or Comprehensive Mock Assessment.
- **Interactive Exam Studio:** Real-time countdown timer, dynamic question palette with status indicators (Unanswered, Answered, Current), instant grading, and step-by-step mathematical/logical explanations for every question.
- **Persistent Attempt History:** Track test scores over time to monitor foundational problem-solving readiness.

### 2. 🎙️ AI Mock Interview Room ("Ava — AI Interviewer")
- **Dual-Participant Experience:** Professional side-by-side room layout pairing the candidate with **Ava — AI Interviewer**, complete with live status dots ("Listening", "Candidate Ready") and realistic avatar representations.
- **Voice Dictation & Text-to-Speech:** Integrated Web Speech API enables spoken voice answers and automatic audio question vocalization.
- **Adaptive Follow-Up Questions:** Questions adapt to candidate responses based on technical depth, length, and resume background.
- **Multi-Role Scenarios:** Practice technical, behavioral, and HR questions across Software Engineering, Data Science, Product Management, and Cloud roles.

### 3. 👥 Interviewer Workspace & Candidate Evaluation Portal
- **Role-Based Authorization:** Separate portals for **Students** and **Interviewers** with an administrator approval gate (`is_approved`) for verified evaluators.
- **Interviewer Workspace (`/interviewer/dashboard`):** Schedule sessions, assign candidates from the roster, and curate questions from the question bank.
- **Live Candidate Dossier & Evaluation Room (`/interviewer/session/<id>`):** Live review pane showing the candidate's academic background, parsed resume skills/projects, question rubrics, and a real-time scoring form (Technical 0-100, Communication 0-100, Overall 0-100, and meeting notes).
- **Candidate Feedback Portal (`/my-interviews`):** Students can review assigned sessions, interviewer feedback, and evaluation scores to prepare for real campus interviews.

### 4. 📄 Persistent Resume Intelligence
- **Multi-Resume Storage:** Upload and manage multiple PDF resumes with permanent persistence in the database and filesystem.
- **Automated Resume Parsing:** Extracts skills, projects, education, and target roles using `pypdf` and regex intelligence.
- **Windows File-Locking Prevention:** Built-in memory buffering (`BytesIO`) ensures resumes can be viewed, downloaded, or deleted without file locking issues.
- **Session Personalization:** Extracted resume skills and projects automatically seed candidate questions during mock interviews.

### 5. 📊 5-Metric Performance Analytics & Practice Drills
- **5 Evaluation Dimensions:** Relevance, Clarity, Communication, Fluency, and Technical Knowledge.
- **Visual Analytics:** Interactive Chart.js radar charts and detailed score rationales ("Explain My Score").
- **STAR Practice Drills:** Real-time evaluation of practice responses against Situation, Task, Action, and Result frameworks.
- **Longitudinal Progress Tracking:** Compare Attempt 1 vs. Attempt 2 with exact score deltas and trajectory curves.

---

## 🎨 Modern EdTech Visual Identity

The platform features a modern, accessible EdTech design:
- **Palette:** Sky-blue background (`#f0f9ff`), vibrant cyan/blue primary accents (`#0284c7`, `#06b6d4`), and high-contrast navy typography (`#0f172a`).
- **Layout:** Generous spacing, soft rounded cards (`14px` border-radius), floating accent badges, pill buttons, and responsive grid layouts.
- **Clarity First:** Free of academic clutter, theoretical essays, and confusing disclaimers — every screen focuses on actionable practice and clear results.

---

## 📂 Project Structure

```
AI-Interview-performance-Analyzer/
├── app.py                      # Flask backend controller & RESTful API routes
├── requirements.txt            # Python dependencies (Flask, pypdf, google-generativeai, pytest)
├── .env.example                # Environment variable configuration template
├── seed_demo.py                # Database seeder for demo accounts & Attempt 1 data
├── test_app.py                 # Route status sanity test
├── test_comprehensive.py       # Full pytest suite (10 end-to-end test cases)
├── interview_analyzer.db       # Relational SQLite database
│
├── database/
│   └── db.py                   # DB connection, schema migrations, and 23 seed aptitude questions
│
├── migrations/
│   └── 01_supabase_schema.sql  # Supabase PostgreSQL schema with RLS policies
│
├── services/
│   ├── ai_service.py           # Gemini AI & rule-based question generator & 5-metric evaluator
│   ├── resume_service.py       # PDF parser & technical skill/project extractor
│   └── analysis_service.py     # Practice drill generator & attempt comparison engine
│
├── static/
│   └── css/
│       └── style.css           # Modern EdTech design system (cyan accents & navy typography)
│
└── templates/
    ├── base.html               # Role-aware responsive navigation & footer
    ├── index.html              # Modern landing page ("Prepare Smarter. Interview Better.")
    ├── login.html              # Sign-in portal with 1-click demo logins
    ├── register.html           # Student & Interviewer registration
    ├── dashboard.html          # Student dashboard & readiness metrics
    ├── aptitude_setup.html     # Aptitude practice room setup
    ├── aptitude_test.html      # Timed aptitude test room with question palette
    ├── aptitude_result.html    # Aptitude results & step-by-step explanations
    ├── interview_setup.html    # AI Mock Interview configuration wizard
    ├── interview.html          # Dual-participant room (Ava & Candidate + Audio/Video)
    ├── result.html             # AI Performance Analysis & Radar Chart
    ├── preparation.html        # Practice Recommendations & STAR drill sandbox
    ├── resume.html             # My Resumes upload & preview gallery
    ├── question_bank.html      # Question Bank catalog & CSV import
    ├── progress.html           # Longitudinal attempt comparison & analytics
    ├── interviewer_dashboard.html # Interviewer workspace & session creator
    ├── interviewer_room.html   # Live interviewer evaluation room
    └── student_interviews.html # Student portal for interviewer evaluations
```

---

## 🚀 Getting Started

### 1. Prerequisites
- Python 3.10 or higher installed.

### 2. Installation
Clone the repository and enter the directory:
```powershell
git clone https://github.com/Prathameshkoli707/AI-Interview-performance-Analyzer.git
cd AI-Interview-performance-Analyzer
```

Install the dependencies:
```powershell
pip install -r requirements.txt
```

### 3. Environment Configuration
Create a `.env` file from the provided `.env.example`:
```powershell
cp .env.example .env
```

Configure your environment variables as needed:
```ini
FLASK_SECRET_KEY=dev-secret-key-replace-in-production-2026
DB_MODE=sqlite
GEMINI_API_KEY=your-gemini-api-key-here
```
*(Note: If `GEMINI_API_KEY` is not provided, the platform automatically activates its built-in rule-based evaluation engine and curated question bank.)*

### 4. Database Setup & Seeding
The database tables and seed questions are initialized automatically when the app runs. To seed the demo candidate and interviewer history:
```powershell
python seed_demo.py
```

### 5. Running the Application
Start the Flask development server:
```powershell
python app.py
```

Access the application in your browser at:
```
http://127.0.0.1:5000
```

---

## 🔑 Default Demo Accounts

For instant evaluation, you can use the pre-configured credentials or the 1-click buttons on the login screen:

| Role | Email | Password | Access Level |
|---|---|---|---|
| **Student** | `student@example.com` | `password123` | Dashboard, Resumes, Aptitude, AI Mock Interviews, Feedback |
| **Interviewer** | `interviewer@example.com` | `interviewer123` | Interviewer Workspace, Candidate Roster, Live Scoring Room |

---

## 🧪 Automated Testing

Run the full end-to-end test suite:

```powershell
# Run the 10-point comprehensive pytest test suite
python -m pytest test_comprehensive.py -v

# Run the lightweight route verification
python test_app.py
```

### Test Coverage:
1. `test_routes_status_200`: All public and authenticated routes render HTTP 200.
2. `test_user_registration_and_login`: Student onboarding, password hashing, and session authentication.
3. `test_complete_resume_lifecycle`: Upload, disk storage, database persistence, view/download, re-analysis, multi-resume management, user isolation, and deletion.
4. `test_question_bank_add_and_filter`: Personal questions, category filtering, and rubrics.
5. `test_csv_import_question_bank`: Bulk CSV importing with duplicate detection.
6. `test_interview_lifecycle`: Adaptive question generation, answer submissions, composite scoring, and preparation recommendations.
7. `test_practice_drill_evaluation`: Real-time STAR methodology evaluation.
8. `test_aptitude_module_full_lifecycle`: Category selection, timed test room, answer submission, score calculation, and review.
9. `test_interviewer_auth_and_dashboard`: Role protection and administrator verification gate.
10. `test_interviewer_session_and_student_feedback`: Session creation, live evaluation submission, and student feedback viewing.

---

## 📜 License
This project is open-source under the MIT License.
