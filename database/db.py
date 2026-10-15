import os
import sqlite3
import json
from werkzeug.security import generate_password_hash

DB_PATH = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "interview_analyzer.db")

def get_db_connection():
    conn = sqlite3.connect(DB_PATH, timeout=30.0)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON;")
    conn.execute("PRAGMA journal_mode = WAL;")
    return conn

def init_db():
    conn = get_db_connection()
    cursor = conn.cursor()

    # 1. users / profiles table (supports full profile metadata)
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS users (
        user_id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT NOT NULL,
        email TEXT UNIQUE NOT NULL,
        password TEXT NOT NULL,
        education TEXT,
        college_name TEXT,
        experience_level TEXT DEFAULT 'Fresher',
        target_industry TEXT DEFAULT 'IT & Software',
        target_role TEXT DEFAULT 'Software Developer',
        technical_skills TEXT, -- JSON array of skills
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    );
    """)

    # 2. resumes table
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS resumes (
        resume_id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER NOT NULL,
        file_path TEXT NOT NULL,
        original_filename TEXT,
        extracted_text TEXT,
        skills TEXT, -- JSON list
        projects TEXT, -- JSON list
        education TEXT,
        experience TEXT,
        uploaded_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (user_id) REFERENCES users(user_id) ON DELETE CASCADE
    );
    """)

    # 3. question_bank table (Student-owned & Public catalog)
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS question_bank (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        owner_user_id INTEGER, -- NULL = public system question
        question_text TEXT NOT NULL,
        category TEXT NOT NULL,
        topic TEXT NOT NULL,
        job_role TEXT NOT NULL,
        difficulty TEXT NOT NULL DEFAULT 'Medium',
        expected_answer_or_rubric TEXT,
        is_public INTEGER DEFAULT 0, -- 1 for public, 0 for private
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (owner_user_id) REFERENCES users(user_id) ON DELETE CASCADE
    );
    """)

    # 4. interviews table
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS interviews (
        interview_id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER NOT NULL,
        title TEXT DEFAULT 'Mock Interview Session',
        industry TEXT NOT NULL,
        job_role TEXT NOT NULL,
        interview_type TEXT NOT NULL,
        difficulty TEXT NOT NULL,
        num_questions INTEGER DEFAULT 4,
        overall_score REAL DEFAULT 0.0,
        status TEXT DEFAULT 'in_progress', -- 'in_progress', 'completed'
        date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        completed_at TIMESTAMP,
        FOREIGN KEY (user_id) REFERENCES users(user_id) ON DELETE CASCADE
    );
    """)

    # 5. questions table (interview_questions)
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS questions (
        question_id INTEGER PRIMARY KEY AUTOINCREMENT,
        interview_id INTEGER NOT NULL,
        question_bank_id INTEGER,
        question_text TEXT NOT NULL,
        question_type TEXT,
        difficulty TEXT,
        question_order INTEGER,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (interview_id) REFERENCES interviews(interview_id) ON DELETE CASCADE,
        FOREIGN KEY (question_bank_id) REFERENCES question_bank(id) ON DELETE SET NULL
    );
    """)

    # 6. answers table
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS answers (
        answer_id INTEGER PRIMARY KEY AUTOINCREMENT,
        question_id INTEGER NOT NULL,
        user_id INTEGER NOT NULL,
        answer_text TEXT,
        answer_duration_seconds INTEGER DEFAULT 0,
        audio_path TEXT,
        video_path TEXT,
        submitted_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (question_id) REFERENCES questions(question_id) ON DELETE CASCADE,
        FOREIGN KEY (user_id) REFERENCES users(user_id) ON DELETE CASCADE
    );
    """)

    # 7. analysis table (evaluations)
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS analysis (
        analysis_id INTEGER PRIMARY KEY AUTOINCREMENT,
        interview_id INTEGER NOT NULL,
        answer_id INTEGER NOT NULL UNIQUE,
        relevance_score REAL DEFAULT 0.0,
        clarity_score REAL DEFAULT 0.0,
        communication_score REAL DEFAULT 0.0,
        fluency_score REAL DEFAULT 0.0,
        technical_score REAL DEFAULT 0.0,
        strengths TEXT, -- JSON list
        weaknesses TEXT, -- JSON list
        feedback TEXT,
        improvement_suggestion TEXT,
        explain_json TEXT, -- JSON breakdown
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (interview_id) REFERENCES interviews(interview_id) ON DELETE CASCADE,
        FOREIGN KEY (answer_id) REFERENCES answers(answer_id) ON DELETE CASCADE
    );
    """)

    # 8. practice_plan table (practice_plans)
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS practice_plan (
        plan_id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER NOT NULL,
        interview_id INTEGER,
        weak_area TEXT NOT NULL,
        recommendation TEXT NOT NULL,
        practice_questions TEXT NOT NULL, -- JSON list
        ai_focus TEXT,
        priority TEXT DEFAULT 'Medium',
        status TEXT DEFAULT 'pending', -- 'pending', 'in_progress', 'completed'
        due_date TEXT,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        completed_at TIMESTAMP,
        FOREIGN KEY (user_id) REFERENCES users(user_id) ON DELETE CASCADE,
        FOREIGN KEY (interview_id) REFERENCES interviews(interview_id) ON DELETE SET NULL
    );
    """)

    # 9. aptitude_questions table
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS aptitude_questions (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        category TEXT NOT NULL, -- 'Quantitative Aptitude', 'Logical Reasoning', 'Verbal Ability', 'Data Interpretation'
        topic TEXT NOT NULL,
        difficulty TEXT NOT NULL DEFAULT 'Medium', -- 'Easy', 'Medium', 'Hard'
        question_text TEXT NOT NULL,
        options TEXT NOT NULL, -- JSON list of 4 options
        correct_option INTEGER NOT NULL, -- 0-indexed integer
        explanation TEXT,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    );
    """)

    # 10. aptitude_attempts table
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS aptitude_attempts (
        attempt_id TEXT PRIMARY KEY,
        user_id INTEGER NOT NULL,
        category TEXT NOT NULL,
        difficulty TEXT NOT NULL,
        mode TEXT NOT NULL DEFAULT 'timed', -- 'practice' or 'timed'
        total_questions INTEGER NOT NULL,
        correct_count INTEGER NOT NULL DEFAULT 0,
        incorrect_count INTEGER NOT NULL DEFAULT 0,
        unanswered_count INTEGER NOT NULL DEFAULT 0,
        score_percent REAL NOT NULL DEFAULT 0.0,
        time_taken_seconds INTEGER DEFAULT 0,
        user_answers TEXT, -- JSON mapping question_id -> selected_option
        question_ids TEXT, -- JSON list of question_ids in this test
        submitted_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (user_id) REFERENCES users(user_id) ON DELETE CASCADE
    );
    """)

    # 11. interviewer_sessions table (for interviewer-led mock interviews)
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS interviewer_sessions (
        session_id INTEGER PRIMARY KEY AUTOINCREMENT,
        interviewer_id INTEGER NOT NULL,
        candidate_id INTEGER, -- Assigned student user_id, nullable until assigned/claimed
        title TEXT NOT NULL,
        job_role TEXT NOT NULL,
        interview_type TEXT NOT NULL DEFAULT 'Technical',
        difficulty TEXT NOT NULL DEFAULT 'Medium',
        scheduled_time TEXT,
        status TEXT NOT NULL DEFAULT 'scheduled', -- 'scheduled', 'in_progress', 'completed', 'cancelled'
        meeting_notes TEXT,
        interviewer_feedback TEXT,
        technical_score REAL DEFAULT 0.0,
        communication_score REAL DEFAULT 0.0,
        overall_score REAL DEFAULT 0.0,
        selected_question_ids TEXT, -- JSON list of question_bank ids
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        completed_at TIMESTAMP,
        FOREIGN KEY (interviewer_id) REFERENCES users(user_id) ON DELETE CASCADE,
        FOREIGN KEY (candidate_id) REFERENCES users(user_id) ON DELETE SET NULL
    );
    """)

    # Ensure schema migrations for existing database columns (idempotent alterations)
    def ensure_column(table, column, col_type):
        try:
            cursor.execute(f"ALTER TABLE {table} ADD COLUMN {column} {col_type};")
        except sqlite3.OperationalError:
            pass

    ensure_column("users", "role", "TEXT DEFAULT 'student'")
    ensure_column("users", "is_approved", "INTEGER DEFAULT 1")
    ensure_column("users", "college_name", "TEXT")
    ensure_column("users", "technical_skills", "TEXT")
    ensure_column("users", "updated_at", "TIMESTAMP")
    ensure_column("resumes", "original_filename", "TEXT")
    ensure_column("interviews", "title", "TEXT DEFAULT 'Mock Interview Session'")
    ensure_column("interviews", "completed_at", "TIMESTAMP")
    ensure_column("questions", "question_bank_id", "INTEGER")
    ensure_column("questions", "created_at", "TIMESTAMP")
    ensure_column("answers", "answer_duration_seconds", "INTEGER DEFAULT 0")
    ensure_column("analysis", "improvement_suggestion", "TEXT")
    ensure_column("analysis", "created_at", "TIMESTAMP")
    ensure_column("practice_plan", "priority", "TEXT DEFAULT 'Medium'")
    ensure_column("practice_plan", "due_date", "TEXT")
    ensure_column("practice_plan", "completed_at", "TIMESTAMP")

    # Seed public questions into question_bank if empty
    cursor.execute("SELECT COUNT(*) FROM question_bank")
    if cursor.fetchone()[0] == 0:
        seed_public_questions(cursor)

    # Seed verified questions into aptitude_questions if empty
    cursor.execute("SELECT COUNT(*) FROM aptitude_questions")
    if cursor.fetchone()[0] == 0:
        seed_aptitude_questions(cursor)

    # Seed default verified student & interviewer accounts if missing
    seed_default_accounts(cursor)

    conn.commit()
    conn.close()

def seed_default_accounts(cursor):
    """Seed trusted default student and interviewer accounts with proper hashed passwords."""
    from werkzeug.security import generate_password_hash
    # 1. Student Account
    cursor.execute("SELECT user_id FROM users WHERE LOWER(email) = 'student@example.com'")
    if not cursor.fetchone():
        cursor.execute("""
        INSERT INTO users (name, email, password, education, college_name, experience_level, target_industry, target_role, technical_skills, role, is_approved)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, 'student', 1)
        """, (
            "Alex Johnson",
            "student@example.com",
            generate_password_hash("password123"),
            "B.Tech Computer Science (Final Year)",
            "Apex Institute of Technology",
            "Internship",
            "IT & Software",
            "Software Developer",
            "Python, SQL, React, Flask, Data Structures"
        ))

    # 2. Interviewer Account
    cursor.execute("SELECT user_id FROM users WHERE LOWER(email) = 'interviewer@example.com'")
    if not cursor.fetchone():
        cursor.execute("""
        INSERT INTO users (name, email, password, education, college_name, experience_level, target_industry, target_role, technical_skills, role, is_approved)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, 'interviewer', 1)
        """, (
            "Dr. Marcus Vance",
            "interviewer@example.com",
            generate_password_hash("interviewer123"),
            "M.S. Software Engineering",
            "Senior Technical Interviewer",
            "8+ Years",
            "IT & Software",
            "Engineering Hiring Lead",
            "System Design, Algorithms, Python, Cloud Architecture"
        ))

def seed_aptitude_questions(cursor):
    """Seed comprehensive verified aptitude questions across all 4 categories."""
    from database.aptitude_seeds import APTITUDE_QUESTIONS
    for q in APTITUDE_QUESTIONS:
        cursor.execute("""
        INSERT INTO aptitude_questions (category, topic, difficulty, question_text, options, correct_option, explanation)
        VALUES (?, ?, ?, ?, ?, ?, ?)
        """, (
            q["category"],
            q["topic"],
            q["difficulty"],
            q["question"],
            json.dumps(q["options"]),
            q["correct_option"],
            q["explanation"]
        ))

def seed_public_questions(cursor):
    """Seed comprehensive initial question bank across various technical & behavioral categories."""
    public_questions = [
        # Software Development
        ("Can you explain how indexing works in relational databases and what trade-offs it introduces?",
         "Software Development", "Database Systems", "Software Developer", "Medium",
         "Indexing creates B-Tree or Hash data structures that speed up SELECT queries from O(N) to O(log N), but slows down write operations (INSERT, UPDATE, DELETE) and consumes extra disk space.", 1),
        ("What is the difference between synchronous and asynchronous execution in web backends?",
         "Software Development", "Concurrency & Web Architecture", "Software Developer", "Medium",
         "Synchronous code blocks thread execution until an operation finishes. Asynchronous non-blocking code delegates long I/O operations to an event loop or worker thread, allowing the server to handle concurrent requests.", 1),
        ("How do you identify and resolve memory leaks or high CPU usage in an application?",
         "Software Development", "Performance & Debugging", "Software Developer", "Hard",
         "Use profilers (e.g. cProfile, memory_profiler), inspect heap snapshots, analyze garbage collection logs, check unclosed connections, and examine thread dumps.", 1),
        ("Describe a challenging technical bug you encountered and how you used the STAR method to debug it.",
         "Software Development", "Problem Solving", "Software Developer", "Medium",
         "Candidate should describe Situation, Task, Action (systematic reproduction, log tracing, hypothesis testing), and Result (fix deployed, unit test added, system stabilized).", 1),
        
        # Web Development
        ("Explain the Virtual DOM in modern UI frameworks and how it minimizes browser reflows.",
         "Web Development", "Frontend Architecture", "Web Developer", "Medium",
         "The Virtual DOM is an in-memory lightweight representation of the real DOM. When state changes, a diffing algorithm determines minimal changes, batching updates to prevent expensive browser layout recalculations.", 1),
        ("What are CORS headers and how do you resolve Cross-Origin Resource Sharing issues securely?",
         "Web Development", "Web Security", "Web Developer", "Easy",
         "CORS is a browser security mechanism that restricts cross-origin HTTP requests. It is configured on the backend using Access-Control-Allow-Origin, Allow-Methods, and Allow-Headers with specific whitelisted domains.", 1),
        ("What are the key security best practices to protect a web application against XSS and CSRF?",
         "Web Development", "Application Security", "Web Developer", "Hard",
         "Sanitize and encode user inputs, use Content Security Policy (CSP), store authentication tokens in httpOnly SameSite cookies, and validate CSRF tokens for state-changing requests.", 1),

        # Data Analytics & AI/ML
        ("What is the difference between supervised, unsupervised, and reinforcement learning?",
         "Artificial Intelligence", "Machine Learning Fundamentals", "AI/ML Engineer", "Easy",
         "Supervised learning uses labeled input-target pairs; Unsupervised finds hidden patterns/clusters in unlabeled data; Reinforcement learns optimal policies via reward and penalty feedback in an environment.", 1),
        ("How do you handle missing values and outliers in a tabular dataset?",
         "Data Analytics", "Data Preprocessing", "Data Analyst", "Medium",
         "Check missingness mechanism (MCAR, MAR, MNAR); use median/mode imputation, iterative regression, or domain-specific drop rules. For outliers, use IQR clipping, z-score thresholds, or robust estimators.", 1),
        ("Explain the bias-variance tradeoff and how regularization helps prevent overfitting.",
         "Artificial Intelligence", "Model Evaluation", "AI/ML Engineer", "Medium",
         "High bias causes underfitting; high variance causes overfitting. L1 (Lasso) and L2 (Ridge) regularization add penalty terms to the loss function to constrain parameter weights and improve generalization.", 1),

        # Human Resources / Behavioral
        ("Tell me about a time you had a conflict with a teammate or stakeholder. How was it resolved?",
         "Human Resources", "Conflict Resolution", "All Roles", "Easy",
         "Demonstrate empathy, active listening, separation of personal emotions from project goals, collaborative compromise, and measurable project delivery.", 1),
        ("Where do you see yourself professionally in the next 3 to 5 years?",
         "Human Resources", "Career Goals & Motivation", "All Roles", "Easy",
         "Express realistic enthusiasm for technical growth, team mentorship, deepening architectural knowledge, and driving tangible product impact.", 1),
        ("Describe a situation where a project deadline was suddenly moved forward. How did you adapt?",
         "Human Resources", "Time Management & Agility", "All Roles", "Medium",
         "Focus on scope triage, communicating risks proactively to stakeholders, prioritizing high-impact MVP features, and maintaining code quality under constraints.", 1),

        # Cybersecurity
        ("What is the difference between symmetric and asymmetric encryption, and where is each used in TLS?",
         "Cybersecurity", "Cryptography & Protocols", "Cybersecurity Analyst", "Medium",
         "Asymmetric encryption (RSA, ECC) uses public/private keys to securely negotiate and exchange session keys during the TLS handshake. Symmetric encryption (AES) is then used for fast data transmission.", 1),
        ("How would you respond to a suspected credential stuffing attack against your authentication service?",
         "Cybersecurity", "Incident Response", "Cybersecurity Analyst", "Hard",
         "Rate-limit login endpoints by IP and user ID, mandate CAPTCHA on failed attempts, enforce multi-factor authentication (MFA), block known malicious IP ranges, and alert affected users to reset credentials.", 1)
    ]

    cursor.executemany("""
    INSERT INTO question_bank (question_text, category, topic, job_role, difficulty, expected_answer_or_rubric, is_public)
    VALUES (?, ?, ?, ?, ?, ?, ?)
    """, public_questions)
