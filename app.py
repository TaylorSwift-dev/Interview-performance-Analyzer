import os
import json
import csv
import io
import uuid
from datetime import datetime
import sqlite3
from flask import (
    Flask, render_template, request, jsonify, redirect, url_for, session, flash, Response, send_file
)
from werkzeug.utils import secure_filename
from werkzeug.security import generate_password_hash, check_password_hash

from database.db import get_db_connection, init_db
from services.resume_service import extract_text_from_pdf, analyze_resume_text
from services.ai_service import generate_question, evaluate_answer
from services.analysis_service import generate_personalized_plan, compare_interview_attempts

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
UPLOAD_FOLDER = os.path.join(BASE_DIR, "uploads")
os.makedirs(UPLOAD_FOLDER, exist_ok=True)

app = Flask(__name__)
app.secret_key = os.environ.get("FLASK_SECRET_KEY", "fep-ai-interview-analyzer-secret-key-2026")
app.config["UPLOAD_FOLDER"] = UPLOAD_FOLDER
app.config["MAX_CONTENT_LENGTH"] = int(os.environ.get("MAX_CONTENT_LENGTH", 16 * 1024 * 1024))  # 16 MB max

# Initialize database schema on startup
with app.app_context():
    init_db()

def get_current_user_id():
    """Returns authenticated user id or None."""
    return session.get("user_id")

def is_authenticated():
    return "user_id" in session

# ----------------- Navigation & Auth Routes -----------------

@app.route("/")
def index():
    return render_template("index.html")

@app.route("/login", methods=["GET", "POST"])
def login():
    """Student Login Route."""
    if request.method == "POST":
        email = request.form.get("email", "").strip().lower()
        password = request.form.get("password", "")

        if not email or not password:
            flash("Please enter both email and password.", "warning")
            return render_template("login.html")

        conn = get_db_connection()
        user = conn.execute("SELECT * FROM users WHERE LOWER(email) = ?", (email,)).fetchone()
        conn.close()

        if user:
            valid = False
            if user["password"].startswith(("pbkdf2:", "scrypt:")):
                valid = check_password_hash(user["password"], password)
            else:
                valid = (user["password"] == password)

            if valid:
                if user["role"] == "interviewer":
                    flash("This account is an Interviewer account. Please log in via the Interviewer Login portal.", "warning")
                    return redirect(url_for("interviewer_login"))

                session["user_id"] = user["user_id"]
                session["user_name"] = user["name"]
                session["user_role"] = "student"

                flash(f"Welcome back, {user['name']}!", "success")
                return redirect(url_for("dashboard"))

        flash("Invalid email or password. Please verify your credentials.", "danger")

    return render_template("login.html")

@app.route("/register", methods=["GET", "POST"])
def register():
    """Student Registration Route."""
    if request.method == "POST":
        name = request.form.get("name", "").strip()
        email = request.form.get("email", "").strip().lower()
        password = request.form.get("password", "")
        confirm_password = request.form.get("confirm_password", "").strip()
        college_name = request.form.get("college_name", "").strip()
        education = request.form.get("education", "").strip()
        experience_level = request.form.get("experience_level", "Fresher")
        target_industry = request.form.get("target_industry", "IT & Software")
        target_role = request.form.get("target_role", "Software Developer")
        technical_skills = request.form.get("technical_skills", "").strip()

        if not name or not email or not password:
            flash("Please fill in all required fields (Name, Email, Password).", "warning")
            return render_template("register.html", name=name, email=email)

        if confirm_password and password != confirm_password:
            flash("Passwords do not match. Please verify your password.", "warning")
            return render_template("register.html", name=name, email=email)

        if len(password) < 6:
            flash("Password must be at least 6 characters long.", "warning")
            return render_template("register.html", name=name, email=email)

        conn = get_db_connection()
        existing = conn.execute("SELECT user_id FROM users WHERE LOWER(email) = ?", (email,)).fetchone()
        if existing:
            conn.close()
            flash("An account with this email already exists. Please log in.", "warning")
            return redirect(url_for("login"))

        hashed_pw = generate_password_hash(password)
        cursor = conn.cursor()
        cursor.execute("""
        INSERT INTO users (name, email, password, education, college_name, experience_level, target_industry, target_role, technical_skills, role, is_approved)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, 'student', 1)
        """, (name, email, hashed_pw, education, college_name, experience_level, target_industry, target_role, technical_skills))
        user_id = cursor.lastrowid
        conn.commit()
        conn.close()

        session["user_id"] = user_id
        session["user_name"] = name
        session["user_role"] = "student"
        flash("Registration successful! Welcome to InterviewPrep AI.", "success")
        return redirect(url_for("dashboard"))

    return render_template("register.html")

@app.route("/interviewer/login", methods=["GET", "POST"])
def interviewer_login():
    """Interviewer Login Route."""
    if request.method == "POST":
        email = request.form.get("email", "").strip().lower()
        password = request.form.get("password", "")

        if not email or not password:
            flash("Please enter both email and password.", "warning")
            return render_template("interviewer_login.html")

        conn = get_db_connection()
        user = conn.execute("SELECT * FROM users WHERE LOWER(email) = ?", (email,)).fetchone()
        conn.close()

        if user:
            valid = False
            if user["password"].startswith(("pbkdf2:", "scrypt:")):
                valid = check_password_hash(user["password"], password)
            else:
                valid = (user["password"] == password)

            if valid:
                if user["role"] != "interviewer":
                    flash("This account is registered as a student. Please use the Student Login portal.", "warning")
                    return render_template("interviewer_login.html")

                if user["is_approved"] == 0:
                    flash("Your interviewer account is currently pending administrator approval.", "warning")
                    return render_template("interviewer_login.html")

                session["user_id"] = user["user_id"]
                session["user_name"] = user["name"]
                session["user_role"] = "interviewer"

                flash(f"Welcome back, {user['name']}!", "success")
                return redirect(url_for("interviewer_dashboard"))

        flash("Invalid email or password. Please verify your credentials.", "danger")

    return render_template("interviewer_login.html")

@app.route("/interviewer/register", methods=["GET", "POST"])
def interviewer_register():
    """Interviewer Registration / Access Request Route."""
    if request.method == "POST":
        name = request.form.get("name", "").strip()
        email = request.form.get("email", "").strip().lower()
        password = request.form.get("password", "")
        confirm_password = request.form.get("confirm_password", "").strip()
        organization = request.form.get("organization", "").strip() or request.form.get("college_name", "").strip()
        technical_skills = request.form.get("technical_skills", "").strip()

        if not name or not email or not password:
            flash("Please fill in all required fields.", "warning")
            return render_template("interviewer_register.html", name=name, email=email)

        if confirm_password and password != confirm_password:
            flash("Passwords do not match. Please verify your password.", "warning")
            return render_template("interviewer_register.html", name=name, email=email)

        if len(password) < 6:
            flash("Password must be at least 6 characters long.", "warning")
            return render_template("interviewer_register.html", name=name, email=email)

        conn = get_db_connection()
        existing = conn.execute("SELECT user_id FROM users WHERE LOWER(email) = ?", (email,)).fetchone()
        if existing:
            conn.close()
            flash("An account with this email already exists. Please log in.", "warning")
            return redirect(url_for("interviewer_login"))

        hashed_pw = generate_password_hash(password)
        cursor = conn.cursor()
        cursor.execute("""
        INSERT INTO users (name, email, password, college_name, technical_skills, role, is_approved)
        VALUES (?, ?, ?, ?, ?, 'interviewer', 0)
        """, (name, email, hashed_pw, organization, technical_skills))
        conn.commit()
        conn.close()

        flash("Interviewer registration received! Your account is pending administrator approval. Please log in once approved.", "info")
        return redirect(url_for("interviewer_login"))

    return render_template("interviewer_register.html")

@app.route("/forgot-password", methods=["GET", "POST"])
def forgot_password():
    if request.method == "POST":
        email = request.form.get("email", "").strip().lower()
        new_password = request.form.get("new_password", "")
        confirm_password = request.form.get("confirm_password", "")

        if not email:
            flash("Please enter your account email.", "warning")
            return render_template("forgot_password.html")

        conn = get_db_connection()
        user = conn.execute("SELECT user_id, name FROM users WHERE LOWER(email) = ?", (email,)).fetchone()
        
        if not user:
            conn.close()
            flash("No account found with that email address.", "danger")
            return render_template("forgot_password.html")

        if new_password:
            if new_password != confirm_password:
                conn.close()
                flash("Passwords do not match. Please try again.", "warning")
                return render_template("forgot_password.html", email=email)

            hashed_pw = generate_password_hash(new_password)
            conn.execute("UPDATE users SET password = ? WHERE user_id = ?", (hashed_pw, user["user_id"]))
            conn.commit()
            conn.close()
            flash("Your password has been reset successfully! You can now log in.", "success")
            return redirect(url_for("login"))

        conn.close()
        return render_template("forgot_password.html", email=email, step="reset")

    return render_template("forgot_password.html", step="identify")

@app.route("/reset-password", methods=["GET", "POST"])
def reset_password():
    return redirect(url_for("forgot_password"))

@app.route("/profile", methods=["GET", "POST"])
def profile_view():
    user_id = get_current_user_id()
    conn = get_db_connection()

    if request.method == "POST":
        name = request.form.get("name", "").strip()
        college_name = request.form.get("college_name", "").strip()
        education = request.form.get("education", "").strip()
        experience_level = request.form.get("experience_level", "Fresher")
        target_industry = request.form.get("target_industry", "IT & Software")
        target_role = request.form.get("target_role", "Software Developer")
        technical_skills = request.form.get("technical_skills", "").strip()

        conn.execute("""
        UPDATE users SET
            name = ?,
            college_name = ?,
            education = ?,
            experience_level = ?,
            target_industry = ?,
            target_role = ?,
            technical_skills = ?,
            updated_at = CURRENT_TIMESTAMP
        WHERE user_id = ?
        """, (name, college_name, education, experience_level, target_industry, target_role, technical_skills, user_id))
        conn.commit()
        session["user_name"] = name
        flash("Profile updated successfully!", "success")

    user = conn.execute("SELECT * FROM users WHERE user_id = ?", (user_id,)).fetchone()
    conn.close()
    return render_template("profile.html", user=user)

@app.route("/logout")
def logout():
    session.clear()
    flash("Signed out successfully.", "info")
    return redirect(url_for("index"))

# ----------------- Candidate Dashboard -----------------

@app.route("/student/dashboard", endpoint="student_dashboard")
@app.route("/dashboard", endpoint="dashboard")
def student_dashboard():
    user_id = session.get("user_id")
    if not user_id:
        flash("Please log in to access the student dashboard.", "warning")
        return redirect(url_for("login"))

    if session.get("user_role") == "interviewer":
        return redirect(url_for("interviewer_dashboard"))

    conn = get_db_connection()
    user = conn.execute("SELECT * FROM users WHERE user_id = ?", (user_id,)).fetchone()
    if not user:
        conn.close()
        session.clear()
        flash("User profile not found. Please log in again.", "warning")
        return redirect(url_for("login"))
    resume = conn.execute("SELECT * FROM resumes WHERE user_id = ? ORDER BY uploaded_at DESC LIMIT 1", (user_id,)).fetchone()

    interviews = conn.execute(
        "SELECT * FROM interviews WHERE user_id = ? ORDER BY date DESC",
        (user_id,)
    ).fetchall()

    best_score_row = conn.execute(
        "SELECT MAX(overall_score) as best_score, AVG(overall_score) as avg_score, COUNT(*) as total FROM interviews WHERE user_id = ? AND overall_score > 0",
        (user_id,)
    ).fetchone()

    plans = conn.execute(
        "SELECT * FROM practice_plan WHERE user_id = ? ORDER BY created_at DESC LIMIT 3",
        (user_id,)
    ).fetchall()

    aptitude_attempts = conn.execute(
        "SELECT * FROM aptitude_attempts WHERE user_id = ? ORDER BY submitted_at DESC",
        (user_id,)
    ).fetchall()

    apt_stats_row = conn.execute(
        "SELECT COUNT(*) as total_tests, AVG(score_percent) as avg_score, MAX(score_percent) as best_score FROM aptitude_attempts WHERE user_id = ?",
        (user_id,)
    ).fetchone()

    aptitude_stats = {
        "total_tests": apt_stats_row["total_tests"] if apt_stats_row else 0,
        "avg_score": round(apt_stats_row["avg_score"] or 0, 1) if apt_stats_row else 0,
        "best_score": round(apt_stats_row["best_score"] or 0, 1) if apt_stats_row else 0
    }

    conn.close()

    # Completed interviews for real metrics
    completed_interviews = [i for i in interviews if i["status"] == "completed" and (i["overall_score"] or 0) > 0]
    total_completed = len(completed_interviews)
    
    latest_score = 0
    improvement_delta = 0
    if total_completed >= 1:
        latest_score = round(completed_interviews[0]["overall_score"], 1)
    if total_completed >= 2:
        # previous is index 1 since ordered by date DESC
        prev_score = round(completed_interviews[1]["overall_score"], 1)
        improvement_delta = round(latest_score - prev_score, 1)

    # Primary recommended practice activity
    recommended_plan = plans[0] if plans else None

    resume_skills = json.loads(resume["skills"]) if resume and resume["skills"] else []
    resume_projects = json.loads(resume["projects"]) if resume and resume["projects"] else []

    return render_template(
        "dashboard.html",
        user=user,
        resume=resume,
        resume_skills=resume_skills,
        resume_projects=resume_projects,
        interviews=interviews,
        total_completed=total_completed,
        latest_score=latest_score,
        improvement_delta=improvement_delta,
        recommended_plan=recommended_plan,
        best_score=round(best_score_row["best_score"] or 0, 1),
        avg_score=round(best_score_row["avg_score"] or 0, 1),
        plans=plans,
        aptitude_attempts=aptitude_attempts,
        aptitude_stats=aptitude_stats
    )

dashboard = student_dashboard

# ----------------- Resume Module (My Resumes) -----------------

@app.route("/resume", methods=["GET", "POST"])
def resume_view():
    user_id = session.get("user_id")
    if not user_id:
        flash("Please log in to manage your resumes.", "warning")
        return redirect(url_for("login"))

    conn = get_db_connection()

    if request.method == "POST":
        if "resume_file" not in request.files:
            flash("Please choose a PDF file to upload.", "danger")
            return redirect(request.url)

        file = request.files["resume_file"]
        if file.filename == "":
            flash("Please choose a PDF file to upload.", "danger")
            return redirect(request.url)

        if file and file.filename.lower().endswith(".pdf"):
            orig_filename = secure_filename(file.filename)
            filename = f"user_{user_id}_{orig_filename}"
            save_path = os.path.join(app.config["UPLOAD_FOLDER"], filename)
            file.save(save_path)

            # Extract text & analyze with PyPDF & pattern extraction
            raw_text = extract_text_from_pdf(save_path)
            analysis = analyze_resume_text(raw_text)

            conn.execute("""
            INSERT INTO resumes (user_id, file_path, original_filename, extracted_text, skills, projects, education, experience)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                user_id,
                save_path,
                orig_filename,
                raw_text[:4000],
                json.dumps(analysis["skills"]),
                json.dumps(analysis["projects"]),
                analysis["education"],
                analysis["experience"]
            ))
            conn.commit()
            flash(f"Resume '{orig_filename}' uploaded and analyzed successfully!", "success")
            conn.close()
            return redirect(url_for("resume_view"))
        else:
            flash("Invalid file format. Please upload a PDF document (.pdf).", "warning")

    # Fetch all resumes for the authenticated user
    resumes_rows = conn.execute(
        "SELECT * FROM resumes WHERE user_id = ? ORDER BY uploaded_at DESC",
        (user_id,)
    ).fetchall()
    conn.close()

    resumes_list = []
    for r in resumes_rows:
        skills = json.loads(r["skills"]) if r["skills"] else []
        projects = json.loads(r["projects"]) if r["projects"] else []
        has_file = os.path.exists(r["file_path"]) if r["file_path"] else False
        resumes_list.append({
            "resume_id": r["resume_id"],
            "original_filename": r["original_filename"] or os.path.basename(r["file_path"] or "resume.pdf"),
            "file_path": r["file_path"],
            "has_file": has_file,
            "uploaded_at": r["uploaded_at"],
            "education": r["education"] or "Not detected",
            "experience": r["experience"] or "Fresher / Student",
            "skills": skills,
            "projects": projects,
            "extracted_length": len(r["extracted_text"] or "")
        })

    active_resume = resumes_list[0] if resumes_list else None

    return render_template(
        "resume.html",
        resumes=resumes_list,
        active_resume=active_resume
    )

@app.route("/resume/download/<int:resume_id>")
def download_resume(resume_id):
    user_id = get_current_user_id()
    conn = get_db_connection()
    resume = conn.execute("SELECT * FROM resumes WHERE resume_id = ? AND user_id = ?", (resume_id, user_id)).fetchone()
    conn.close()

    if not resume:
        flash("Resume not found or unauthorized.", "danger")
        return redirect(url_for("resume_view"))

    file_path = resume["file_path"]
    if not file_path or not os.path.exists(file_path):
        flash("The physical PDF file could not be found on storage.", "danger")
        return redirect(url_for("resume_view"))

    with open(file_path, "rb") as f:
        file_bytes = io.BytesIO(f.read())
    download_name = resume["original_filename"] or os.path.basename(file_path)
    return send_file(file_bytes, as_attachment=True, download_name=download_name, mimetype="application/pdf")

@app.route("/resume/view/<int:resume_id>")
def view_resume_file(resume_id):
    user_id = get_current_user_id()
    conn = get_db_connection()
    resume = conn.execute("SELECT * FROM resumes WHERE resume_id = ? AND user_id = ?", (resume_id, user_id)).fetchone()
    conn.close()

    if not resume:
        flash("Resume not found or unauthorized.", "danger")
        return redirect(url_for("resume_view"))

    file_path = resume["file_path"]
    if not file_path or not os.path.exists(file_path):
        flash("The PDF file does not exist on storage.", "danger")
        return redirect(url_for("resume_view"))

    with open(file_path, "rb") as f:
        file_bytes = io.BytesIO(f.read())
    return send_file(file_bytes, mimetype="application/pdf")

@app.route("/resume/analyze/<int:resume_id>", methods=["POST"])
def analyze_resume_action(resume_id):
    user_id = get_current_user_id()
    conn = get_db_connection()
    resume = conn.execute("SELECT * FROM resumes WHERE resume_id = ? AND user_id = ?", (resume_id, user_id)).fetchone()

    if not resume:
        conn.close()
        flash("Resume not found or unauthorized.", "danger")
        return redirect(url_for("resume_view"))

    file_path = resume["file_path"]
    if not file_path or not os.path.exists(file_path):
        conn.close()
        flash("Resume file is not available on disk for re-analysis.", "danger")
        return redirect(url_for("resume_view"))

    raw_text = extract_text_from_pdf(file_path)
    analysis = analyze_resume_text(raw_text)

    conn.execute("""
    UPDATE resumes SET
        extracted_text = ?,
        skills = ?,
        projects = ?,
        education = ?,
        experience = ?
    WHERE resume_id = ?
    """, (
        raw_text[:4000],
        json.dumps(analysis["skills"]),
        json.dumps(analysis["projects"]),
        analysis["education"],
        analysis["experience"],
        resume_id
    ))
    conn.commit()
    conn.close()

    flash("Resume re-analyzed successfully! Skills and projects updated.", "success")
    return redirect(url_for("resume_view"))

@app.route("/resume/delete/<int:resume_id>", methods=["POST"])
def delete_resume_action(resume_id):
    import gc
    user_id = get_current_user_id()
    conn = get_db_connection()
    resume = conn.execute("SELECT * FROM resumes WHERE resume_id = ? AND user_id = ?", (resume_id, user_id)).fetchone()

    if not resume:
        conn.close()
        flash("Resume not found or unauthorized.", "danger")
        return redirect(url_for("resume_view"))

    # Safely remove file from disk if it exists
    file_path = resume["file_path"]
    if file_path and os.path.exists(file_path):
        gc.collect()
        try:
            os.remove(file_path)
        except Exception as e:
            print(f"Notice: Failed to delete physical file {file_path}: {e}")

    conn.execute("DELETE FROM resumes WHERE resume_id = ?", (resume_id,))
    conn.commit()
    conn.close()

    flash("Resume deleted successfully.", "info")
    return redirect(url_for("resume_view"))

# ----------------- Student-Owned Question Bank -----------------

@app.route("/question-bank")
def question_bank_view():
    user_id = get_current_user_id()
    query = request.args.get("q", "").strip()
    category = request.args.get("category", "").strip()
    difficulty = request.args.get("difficulty", "").strip()
    scope = request.args.get("scope", "").strip() # 'mine', 'public', or ''

    conn = get_db_connection()

    sql = "SELECT * FROM question_bank WHERE (is_public = 1 OR owner_user_id = ?)"
    params = [user_id]

    if scope == "mine":
        sql += " AND owner_user_id = ?"
        params.append(user_id)
    elif scope == "public":
        sql += " AND is_public = 1"

    if category:
        sql += " AND category = ?"
        params.append(category)

    if difficulty:
        sql += " AND difficulty = ?"
        params.append(difficulty)

    if query:
        sql += " AND (question_text LIKE ? OR topic LIKE ? OR expected_answer_or_rubric LIKE ?)"
        q_wild = f"%{query}%"
        params.extend([q_wild, q_wild, q_wild])

    sql += " ORDER BY created_at DESC"
    questions = conn.execute(sql, params).fetchall()

    categories_rows = conn.execute("SELECT DISTINCT category FROM question_bank").fetchall()
    categories = [r["category"] for r in categories_rows if r["category"]]

    conn.close()

    return render_template(
        "question_bank.html",
        questions=questions,
        categories=categories,
        query=query,
        selected_category=category,
        selected_difficulty=difficulty,
        selected_scope=scope,
        current_user_id=user_id
    )

@app.route("/question-bank/add", methods=["POST"])
def add_question():
    user_id = get_current_user_id()
    question_text = request.form.get("question_text", "").strip()
    category = request.form.get("category", "Software Development").strip()
    topic = request.form.get("topic", "General").strip()
    job_role = request.form.get("job_role", "Software Developer").strip()
    difficulty = request.form.get("difficulty", "Medium").strip()
    expected_answer = request.form.get("expected_answer", "").strip()
    is_public = 1 if request.form.get("is_public") == "1" else 0

    if not question_text:
        flash("Question text is required.", "warning")
        return redirect(url_for("question_bank_view"))

    conn = get_db_connection()
    conn.execute("""
    INSERT INTO question_bank (owner_user_id, question_text, category, topic, job_role, difficulty, expected_answer_or_rubric, is_public)
    VALUES (?, ?, ?, ?, ?, ?, ?, ?)
    """, (user_id, question_text, category, topic, job_role, difficulty, expected_answer, is_public))
    conn.commit()
    conn.close()

    flash("Question added successfully to your question bank!", "success")
    return redirect(url_for("question_bank_view"))

@app.route("/question-bank/delete/<int:q_id>", methods=["POST"])
def delete_question(q_id):
    user_id = get_current_user_id()
    conn = get_db_connection()
    # Check ownership
    q = conn.execute("SELECT * FROM question_bank WHERE id = ?", (q_id,)).fetchone()
    if q and q["owner_user_id"] == user_id:
        conn.execute("DELETE FROM question_bank WHERE id = ?", (q_id,))
        conn.commit()
        flash("Question deleted successfully.", "info")
    else:
        flash("Unauthorized or question not found.", "danger")
    conn.close()
    return redirect(url_for("question_bank_view"))

@app.route("/question-bank/import-csv", methods=["POST"])
def import_questions_csv():
    user_id = get_current_user_id()
    if "csv_file" not in request.files:
        flash("No file selected.", "danger")
        return redirect(url_for("question_bank_view"))

    file = request.files["csv_file"]
    if not file.filename.lower().endswith(".csv"):
        flash("Please upload a valid .csv file.", "warning")
        return redirect(url_for("question_bank_view"))

    try:
        stream = io.StringIO(file.stream.read().decode("utf-8-sig"), newline=None)
        reader = csv.DictReader(stream)

        imported_count = 0
        conn = get_db_connection()

        for row in reader:
            q_text = row.get("question_text", "").strip()
            if not q_text:
                continue

            category = row.get("category", "Software Development").strip()
            topic = row.get("topic", "General").strip()
            job_role = row.get("job_role", "Software Developer").strip()
            difficulty = row.get("difficulty", "Medium").strip()
            expected_ans = row.get("expected_answer", row.get("expected_answer_or_rubric", "")).strip()

            # Prevent duplicate import for same user
            existing = conn.execute(
                "SELECT id FROM question_bank WHERE owner_user_id = ? AND question_text = ?",
                (user_id, q_text)
            ).fetchone()
            if not existing:
                conn.execute("""
                INSERT INTO question_bank (owner_user_id, question_text, category, topic, job_role, difficulty, expected_answer_or_rubric, is_public)
                VALUES (?, ?, ?, ?, ?, ?, ?, 0)
                """, (user_id, q_text, category, topic, job_role, difficulty, expected_ans))
                imported_count += 1

        conn.commit()
        conn.close()
        flash(f"Successfully imported {imported_count} questions from CSV!", "success")
    except Exception as e:
        flash(f"Error parsing CSV file: {e}", "danger")

    return redirect(url_for("question_bank_view"))

# ----------------- Interview Setup & Studio -----------------

@app.route("/interview-setup")
def interview_setup():
    user_id = session.get("user_id")
    if not user_id:
        flash("Please log in to set up a mock interview.", "warning")
        return redirect(url_for("login"))

    conn = get_db_connection()
    user = conn.execute("SELECT * FROM users WHERE user_id = ?", (user_id,)).fetchone()
    resume = conn.execute("SELECT * FROM resumes WHERE user_id = ? ORDER BY uploaded_at DESC LIMIT 1", (user_id,)).fetchone()
    conn.close()
    return render_template("interview_setup.html", user=user, resume=resume)

@app.route("/start-interview", methods=["POST"])
def start_interview():
    user_id = get_current_user_id()
    data = request.get_json() or {}

    industry = data.get("industry", "IT & Software")
    role = data.get("role", "Software Developer")
    interview_type = data.get("interview_type", "Technical")
    difficulty = data.get("difficulty", "Medium")
    num_questions = int(data.get("num_questions", 4))
    question_source = data.get("question_source", "adaptive")

    conn = get_db_connection()
    # Fetch candidate resume context
    resume = conn.execute("SELECT * FROM resumes WHERE user_id = ? ORDER BY uploaded_at DESC LIMIT 1", (user_id,)).fetchone()
    resume_context = {}
    if resume:
        resume_context = {
            "skills": json.loads(resume["skills"]) if resume["skills"] else [],
            "projects": json.loads(resume["projects"]) if resume["projects"] else [],
            "education": resume["education"] or ""
        }

    # Create interview session
    cursor = conn.cursor()
    cursor.execute("""
    INSERT INTO interviews (user_id, industry, job_role, interview_type, difficulty, num_questions, status)
    VALUES (?, ?, ?, ?, ?, ?, 'in_progress')
    """, (user_id, industry, role, interview_type, difficulty, num_questions))
    interview_id = cursor.lastrowid

    # Select Question 1 based on source
    q1_text = ""
    q_bank_id = None

    if question_source == "question_bank":
        # Look for relevant question in question_bank
        qb_row = conn.execute("""
        SELECT * FROM question_bank
        WHERE (job_role LIKE ? OR category LIKE ?) AND (is_public = 1 OR owner_user_id = ?)
        ORDER BY RANDOM() LIMIT 1
        """, (f"%{role}%", f"%{industry}%", user_id)).fetchone()

        if qb_row:
            q1_text = qb_row["question_text"]
            q_bank_id = qb_row["id"]

    if not q1_text:
        q1_text = generate_question(industry, role, interview_type, difficulty, resume_context, [])

    cursor.execute("""
    INSERT INTO questions (interview_id, question_bank_id, question_text, question_type, difficulty, question_order)
    VALUES (?, ?, ?, ?, ?, 1)
    """, (interview_id, q_bank_id, q1_text, interview_type, difficulty))

    conn.commit()
    conn.close()

    return jsonify({
        "status": "success",
        "interview_id": interview_id,
        "redirect_url": url_for("interview_room", interview_id=interview_id)
    })

@app.route("/interview/<int:interview_id>")
def interview_room(interview_id):
    user_id = get_current_user_id()
    conn = get_db_connection()
    interview = conn.execute("SELECT * FROM interviews WHERE interview_id = ? AND user_id = ?", (interview_id, user_id)).fetchone()
    if not interview:
        conn.close()
        flash("Interview session not found.", "danger")
        return redirect(url_for("dashboard"))

    questions = conn.execute(
        "SELECT * FROM questions WHERE interview_id = ? ORDER BY question_order ASC",
        (interview_id,)
    ).fetchall()

    answers = conn.execute(
        "SELECT * FROM answers WHERE user_id = ? AND question_id IN (SELECT question_id FROM questions WHERE interview_id = ?)",
        (user_id, interview_id)
    ).fetchall()

    current_order = len(answers) + 1
    total_q = interview["num_questions"]

    if current_order > total_q:
        conn.close()
        return redirect(url_for("interview_result", interview_id=interview_id))

    current_q = None
    for q in questions:
        if q["question_order"] == current_order:
            current_q = q
            break

    user = conn.execute("SELECT * FROM users WHERE user_id = ?", (user_id,)).fetchone()
    conn.close()
    return render_template(
        "interview.html",
        interview=interview,
        current_question=current_q,
        current_step=current_order,
        total_questions=total_q,
        user=user
    )

@app.route("/api/submit-answer", methods=["POST"])
def submit_answer():
    user_id = get_current_user_id()
    data = request.get_json() or {}

    interview_id = data.get("interview_id")
    question_id = data.get("question_id")
    answer_text = data.get("answer_text", "").strip()

    conn = get_db_connection()
    interview = conn.execute("SELECT * FROM interviews WHERE interview_id = ?", (interview_id,)).fetchone()
    question = conn.execute("SELECT * FROM questions WHERE question_id = ?", (question_id,)).fetchone()
    resume = conn.execute("SELECT * FROM resumes WHERE user_id = ? ORDER BY uploaded_at DESC LIMIT 1", (user_id,)).fetchone()

    resume_context = {}
    if resume:
        resume_context = {
            "skills": json.loads(resume["skills"]) if resume["skills"] else [],
            "projects": json.loads(resume["projects"]) if resume["projects"] else []
        }

    # Evaluate the individual answer across 5 dimensions
    eval_res = evaluate_answer(
        question=question["question_text"],
        answer=answer_text,
        role=interview["job_role"],
        interview_type=interview["interview_type"],
        resume_context=resume_context
    )

    # Insert answer
    cursor = conn.cursor()
    cursor.execute("""
    INSERT INTO answers (question_id, user_id, answer_text)
    VALUES (?, ?, ?)
    """, (question_id, user_id, answer_text))
    answer_id = cursor.lastrowid

    # Insert individual answer analysis
    cursor.execute("""
    INSERT INTO analysis (interview_id, answer_id, relevance_score, clarity_score, communication_score, fluency_score, technical_score, strengths, weaknesses, feedback, improvement_suggestion, explain_json)
    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, (
        interview_id,
        answer_id,
        eval_res["relevance_score"],
        eval_res["clarity_score"],
        eval_res["communication_score"],
        eval_res["fluency_score"],
        eval_res["technical_score"],
        json.dumps(eval_res["strengths"]),
        json.dumps(eval_res["weaknesses"]),
        eval_res["feedback"],
        eval_res.get("improvement_suggestion", ""),
        json.dumps(eval_res["explain"])
    ))

    # Check answered count
    answered_count = conn.execute("""
        SELECT COUNT(*) as count FROM answers
        WHERE question_id IN (SELECT question_id FROM questions WHERE interview_id = ?)
    """, (interview_id,)).fetchone()["count"]

    is_completed = answered_count >= interview["num_questions"]

    if is_completed:
        # Calculate overall interview composite average score
        scores = conn.execute("""
            SELECT AVG(relevance_score) as avg_rel,
                   AVG(clarity_score) as avg_cla,
                   AVG(communication_score) as avg_com,
                   AVG(fluency_score) as avg_flu,
                   AVG(technical_score) as avg_tec
            FROM analysis WHERE interview_id = ?
        """, (interview_id,)).fetchone()

        overall = round((scores["avg_rel"] + scores["avg_cla"] + scores["avg_com"] + scores["avg_flu"] + scores["avg_tec"]) / 5.0, 1)

        cursor.execute("UPDATE interviews SET overall_score = ?, status = 'completed', completed_at = CURRENT_TIMESTAMP WHERE interview_id = ?", (overall, interview_id))
        conn.commit()
        conn.close()

        return jsonify({
            "status": "completed",
            "message": "Interview completed successfully!",
            "redirect_url": url_for("interview_result", interview_id=interview_id)
        })

    # Generate next adaptive question
    past_qa = []
    past_rows = conn.execute("""
        SELECT q.question_text, a.answer_text FROM questions q
        JOIN answers a ON q.question_id = a.question_id
        WHERE q.interview_id = ?
        ORDER BY q.question_order ASC
    """, (interview_id,)).fetchall()

    for r in past_rows:
        past_qa.append({"question": r["question_text"], "answer": r["answer_text"]})

    next_order = answered_count + 1
    next_question_text = generate_question(
        industry=interview["industry"],
        role=interview["job_role"],
        interview_type=interview["interview_type"],
        difficulty=interview["difficulty"],
        resume_context=resume_context,
        previous_qa=past_qa
    )

    cursor.execute("""
    INSERT INTO questions (interview_id, question_text, question_type, difficulty, question_order)
    VALUES (?, ?, ?, ?, ?)
    """, (interview_id, next_question_text, interview["interview_type"], interview["difficulty"], next_order))
    next_q_id = cursor.lastrowid

    conn.commit()
    conn.close()

    return jsonify({
        "status": "continue",
        "next_step": next_order,
        "total_steps": interview["num_questions"],
        "question_id": next_q_id,
        "next_question": next_question_text
    })

# ----------------- Performance Analysis & Results -----------------

@app.route("/result/<int:interview_id>")
def interview_result(interview_id):
    user_id = get_current_user_id()
    conn = get_db_connection()

    interview = conn.execute("SELECT * FROM interviews WHERE interview_id = ? AND user_id = ?", (interview_id, user_id)).fetchone()
    if not interview:
        conn.close()
        flash("Interview not found.", "danger")
        return redirect(url_for("dashboard"))

    # Fetch aggregate scores
    avg_scores = conn.execute("""
        SELECT AVG(communication_score) as com,
               AVG(relevance_score) as rel,
               AVG(clarity_score) as cla,
               AVG(fluency_score) as flu,
               AVG(technical_score) as tec
        FROM analysis WHERE interview_id = ?
    """, (interview_id,)).fetchone()

    rows = conn.execute("""
        SELECT q.question_order, q.question_text, a.answer_text,
               an.communication_score, an.relevance_score, an.clarity_score,
               an.fluency_score, an.technical_score, an.strengths, an.weaknesses,
               an.feedback, an.explain_json
        FROM questions q
        JOIN answers a ON q.question_id = a.question_id
        JOIN analysis an ON a.answer_id = an.answer_id
        WHERE q.interview_id = ?
        ORDER BY q.question_order ASC
    """, (interview_id,)).fetchall()

    all_strengths = []
    all_weaknesses = []
    detailed_turns = []

    for r in rows:
        st = json.loads(r["strengths"]) if r["strengths"] else []
        wk = json.loads(r["weaknesses"]) if r["weaknesses"] else []
        exp = json.loads(r["explain_json"]) if r["explain_json"] else {}
        all_strengths.extend(st)
        all_weaknesses.extend(wk)
        detailed_turns.append({
            "order": r["question_order"],
            "question": r["question_text"],
            "answer": r["answer_text"],
            "communication": round(r["communication_score"]),
            "relevance": round(r["relevance_score"]),
            "clarity": round(r["clarity_score"]),
            "fluency": round(r["fluency_score"]),
            "technical": round(r["technical_score"]),
            "strengths": st,
            "weaknesses": wk,
            "feedback": r["feedback"],
            "explain": exp
        })

    unique_strengths = list(dict.fromkeys(all_strengths))[:4]
    unique_weaknesses = list(dict.fromkeys(all_weaknesses))[:4]

    scores_dict = {
        "communication": round(avg_scores["com"] or 70),
        "relevance": round(avg_scores["rel"] or 75),
        "clarity": round(avg_scores["cla"] or 72),
        "fluency": round(avg_scores["flu"] or 74),
        "technical": round(avg_scores["tec"] or 70),
        "overall": round(interview["overall_score"] or 72)
    }

    conn.close()

    return render_template(
        "result.html",
        interview=interview,
        scores=scores_dict,
        strengths=unique_strengths,
        weaknesses=unique_weaknesses,
        detailed_turns=detailed_turns
    )

# ----------------- Personalized Preparation Plan & Practice -----------------

@app.route("/prepare/<int:interview_id>")
def prepare_next(interview_id):
    user_id = get_current_user_id()
    conn = get_db_connection()

    interview = conn.execute("SELECT * FROM interviews WHERE interview_id = ? AND user_id = ?", (interview_id, user_id)).fetchone()
    if not interview:
        conn.close()
        flash("Interview session not found.", "warning")
        return redirect(url_for("dashboard"))

    # Compute metric averages
    avg_scores = conn.execute("""
        SELECT AVG(communication_score) as communication_score,
               AVG(relevance_score) as relevance_score,
               AVG(clarity_score) as clarity_score,
               AVG(fluency_score) as fluency_score,
               AVG(technical_score) as technical_score
        FROM analysis WHERE interview_id = ?
    """, (interview_id,)).fetchone()

    scores_dict = {k: avg_scores[k] or 70 for k in avg_scores.keys()}
    plans = generate_personalized_plan(scores_dict, interview["job_role"])

    # Persist plans in database if not already stored
    for p in plans:
        existing = conn.execute("SELECT * FROM practice_plan WHERE interview_id = ? AND weak_area = ?", (interview_id, p["weak_area"])).fetchone()
        if not existing:
            conn.execute("""
            INSERT INTO practice_plan (user_id, interview_id, weak_area, recommendation, practice_questions, ai_focus, priority)
            VALUES (?, ?, ?, ?, ?, ?, ?)
            """, (user_id, interview_id, p["weak_area"], p["recommendation"], json.dumps(p["practice_questions"]), p["ai_focus"], p.get("priority", "Medium")))

    conn.commit()
    saved_plans = conn.execute("SELECT * FROM practice_plan WHERE interview_id = ?", (interview_id,)).fetchall()
    conn.close()

    parsed_plans = []
    for sp in saved_plans:
        parsed_plans.append({
            "plan_id": sp["plan_id"],
            "weak_area": sp["weak_area"],
            "recommendation": sp["recommendation"],
            "ai_focus": sp["ai_focus"],
            "practice_questions": json.loads(sp["practice_questions"]),
            "status": sp["status"]
        })

    return render_template("preparation.html", interview=interview, plans=parsed_plans)

@app.route("/api/submit-practice", methods=["POST"])
def submit_practice():
    data = request.get_json() or {}
    plan_id = data.get("plan_id")
    answer = data.get("answer", "")
    question = data.get("question", "")

    # Lightweight feedback on practice
    words = len(answer.split())
    star_words = [w for w in ["situation", "task", "action", "result", "outcome", "because", "impact"] if w in answer.lower()]

    if words < 25:
        feedback = "Good attempt! For your next interview, expand on the specific actions YOU took and the quantifiable result."
        passed = False
    elif len(star_words) >= 2:
        feedback = "Excellent! Strong STAR structure detected. You effectively highlighted concrete actions and results."
        passed = True
    else:
        feedback = "Solid detail. Try to clearly separate the problem (Situation & Task) from your specific technical response (Action & Result)."
        passed = True

    if plan_id:
        conn = get_db_connection()
        conn.execute("UPDATE practice_plan SET status = 'completed', completed_at = CURRENT_TIMESTAMP WHERE plan_id = ?", (plan_id,))
        conn.commit()
        conn.close()

    return jsonify({
        "status": "success",
        "feedback": feedback,
        "star_elements_found": star_words,
        "is_ready_for_next": passed
    })

# ----------------- Longitudinal Progress & Interview Comparison -----------------

@app.route("/progress")
def progress_view():
    user_id = session.get("user_id")
    if not user_id:
        flash("Please log in to view your progress analytics.", "warning")
        return redirect(url_for("login"))

    conn = get_db_connection()

    interviews = conn.execute("""
        SELECT i.interview_id, i.job_role, i.interview_type, i.difficulty, i.overall_score, i.date,
               AVG(a.communication_score) as communication_score,
               AVG(a.clarity_score) as clarity_score,
               AVG(a.relevance_score) as relevance_score,
               AVG(a.fluency_score) as fluency_score,
               AVG(a.technical_score) as technical_score
        FROM interviews i
        LEFT JOIN analysis a ON i.interview_id = a.interview_id
        WHERE i.user_id = ? AND i.status = 'completed'
        GROUP BY i.interview_id
        ORDER BY i.date ASC
    """, (user_id,)).fetchall()

    plans = conn.execute(
        "SELECT * FROM practice_plan WHERE user_id = ? ORDER BY created_at DESC LIMIT 3",
        (user_id,)
    ).fetchall()

    aptitude_attempts = conn.execute(
        "SELECT * FROM aptitude_attempts WHERE user_id = ? ORDER BY submitted_at DESC",
        (user_id,)
    ).fetchall()
    conn.close()

    comparison_data = None
    if len(interviews) >= 2:
        attempt_1 = dict(interviews[0])
        attempt_2 = dict(interviews[-1])
        comparison_data = compare_interview_attempts(attempt_1, attempt_2)

    return render_template(
        "progress.html",
        interviews=interviews,
        comparison=comparison_data,
        plans=plans,
        has_multiple_attempts=len(interviews) >= 2,
        aptitude_attempts=aptitude_attempts
    )

# ----------------- Aptitude Practice Module -----------------

@app.route("/aptitude")
def aptitude_setup_view():
    user_id = get_current_user_id()
    conn = get_db_connection()

    # Get available categories and question counts
    categories_summary = conn.execute("""
        SELECT category, COUNT(*) as count 
        FROM aptitude_questions 
        GROUP BY category
    """).fetchall()

    recent_attempts = conn.execute("""
        SELECT * FROM aptitude_attempts 
        WHERE user_id = ? 
        ORDER BY submitted_at DESC 
        LIMIT 5
    """, (user_id,)).fetchall()

    conn.close()
    return render_template(
        "aptitude_setup.html",
        categories=categories_summary,
        recent_attempts=recent_attempts
    )

@app.route("/aptitude/start", methods=["POST"])
def aptitude_start():
    user_id = get_current_user_id()
    data = request.get_json() if request.is_json else request.form

    category = data.get("category", "All Categories")
    difficulty = data.get("difficulty", "Mixed")
    mode = data.get("mode", "standard") # quick (5), standard (10), full (20)

    count_map = {"quick": 5, "standard": 10, "full": 20}
    num_questions = count_map.get(mode, 10)

    conn = get_db_connection()
    query = "SELECT id FROM aptitude_questions WHERE 1=1"
    params = []

    if category != "All Categories":
        query += " AND category = ?"
        params.append(category)

    if difficulty != "Mixed":
        query += " AND difficulty = ?"
        params.append(difficulty)

    query += " ORDER BY RANDOM() LIMIT ?"
    params.append(num_questions)

    question_rows = conn.execute(query, params).fetchall()

    # Fallback to any questions if specific filter yielded none
    if not question_rows:
        question_rows = conn.execute("SELECT id FROM aptitude_questions ORDER BY RANDOM() LIMIT ?", (num_questions,)).fetchall()

    selected_ids = [q["id"] for q in question_rows]
    conn.close()

    if not selected_ids:
        flash("No aptitude questions available in bank.", "warning")
        return redirect(url_for("aptitude_setup_view"))

    # Generate an attempt token in session or temporary attempt record
    attempt_id = f"apt_{uuid.uuid4().hex[:10]}"
    session[f"aptitude_{attempt_id}"] = {
        "attempt_id": attempt_id,
        "category": category,
        "difficulty": difficulty,
        "mode": mode,
        "question_ids": selected_ids,
        "start_time": datetime.utcnow().isoformat()
    }

    if request.is_json:
        return jsonify({
            "status": "success",
            "attempt_id": attempt_id,
            "redirect_url": url_for("aptitude_test_view", attempt_id=attempt_id)
        })
    return redirect(url_for("aptitude_test_view", attempt_id=attempt_id))

@app.route("/aptitude/test/<attempt_id>")
def aptitude_test_view(attempt_id):
    sess_key = f"aptitude_{attempt_id}"
    attempt_session = session.get(sess_key)
    if not attempt_session:
        # Check if already completed and in DB
        conn = get_db_connection()
        record = conn.execute("SELECT attempt_id FROM aptitude_attempts WHERE attempt_id = ?", (attempt_id,)).fetchone()
        conn.close()
        if record:
            return redirect(url_for("aptitude_result_view", attempt_id=attempt_id))
        flash("Aptitude practice session expired or invalid.", "info")
        return redirect(url_for("aptitude_setup_view"))

    q_ids = attempt_session.get("question_ids", [])
    conn = get_db_connection()
    placeholders = ",".join(["?"] * len(q_ids))
    questions_raw = conn.execute(
        f"SELECT id, category, topic, difficulty, question_text, options FROM aptitude_questions WHERE id IN ({placeholders})",
        q_ids
    ).fetchall()
    conn.close()

    # Preserve order
    q_dict = {q["id"]: q for q in questions_raw}
    ordered_questions = []
    for qid in q_ids:
        if qid in q_dict:
            q = dict(q_dict[qid])
            q["options"] = json.loads(q["options"]) if isinstance(q["options"], str) else q["options"]
            ordered_questions.append(q)

    # Time budget per question: ~60-90s
    total_seconds = len(ordered_questions) * 90

    return render_template(
        "aptitude_test.html",
        attempt_id=attempt_id,
        category=attempt_session.get("category"),
        difficulty=attempt_session.get("difficulty"),
        mode=attempt_session.get("mode"),
        questions=ordered_questions,
        total_seconds=total_seconds
    )

@app.route("/api/aptitude/submit", methods=["POST"])
def aptitude_submit():
    user_id = get_current_user_id() or 1
    data = request.get_json() or {}

    attempt_id = data.get("attempt_id")
    user_answers = data.get("answers", {}) # {qid_str: selected_opt_char}
    time_taken = int(data.get("time_taken_seconds", 0))

    sess_key = f"aptitude_{attempt_id}"
    attempt_session = session.get(sess_key)

    q_ids = []
    category = "General Aptitude"
    difficulty = "Medium"
    mode = "standard"

    if attempt_session:
        q_ids = attempt_session.get("question_ids", [])
        category = attempt_session.get("category", category)
        difficulty = attempt_session.get("difficulty", difficulty)
        mode = attempt_session.get("mode", mode)
    else:
        q_ids = [int(k) for k in user_answers.keys() if k.isdigit()]

    if not q_ids:
        return jsonify({"status": "error", "message": "No questions identified for evaluation."}), 400

    conn = get_db_connection()
    placeholders = ",".join(["?"] * len(q_ids))
    db_questions = conn.execute(
        f"SELECT id, correct_option FROM aptitude_questions WHERE id IN ({placeholders})",
        q_ids
    ).fetchall()

    correct_map = {str(q["id"]): str(q["correct_option"]).strip().upper() for q in db_questions}

    correct_count = 0
    incorrect_count = 0
    unanswered_count = 0

    for qid in q_ids:
        qid_str = str(qid)
        ans = user_answers.get(qid_str)
        if not ans:
            unanswered_count += 1
        elif str(ans).strip().upper() == correct_map.get(qid_str):
            correct_count += 1
        else:
            incorrect_count += 1

    total_q = len(q_ids)
    score_pct = round((correct_count / total_q * 100), 1) if total_q > 0 else 0

    # Store persistently in DB
    conn.execute("""
        INSERT INTO aptitude_attempts 
        (attempt_id, user_id, category, difficulty, mode, total_questions, correct_count, incorrect_count, unanswered_count, score_percent, time_taken_seconds, user_answers, question_ids)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, (
        attempt_id,
        user_id,
        category,
        difficulty,
        mode,
        total_q,
        correct_count,
        incorrect_count,
        unanswered_count,
        score_pct,
        time_taken,
        json.dumps(user_answers),
        json.dumps(q_ids)
    ))
    conn.commit()
    conn.close()

    # Clear active session token
    if sess_key in session:
        session.pop(sess_key, None)

    return jsonify({
        "status": "success",
        "attempt_id": attempt_id,
        "score_percent": score_pct,
        "redirect_url": url_for("aptitude_result_view", attempt_id=attempt_id)
    })

@app.route("/aptitude/result/<attempt_id>")
def aptitude_result_view(attempt_id):
    user_id = get_current_user_id()
    conn = get_db_connection()

    attempt = conn.execute("""
        SELECT * FROM aptitude_attempts 
        WHERE attempt_id = ? AND user_id = ?
    """, (attempt_id, user_id)).fetchone()

    if not attempt:
        conn.close()
        flash("Aptitude test result not found.", "warning")
        return redirect(url_for("aptitude_setup_view"))

    q_ids = json.loads(attempt["question_ids"]) if attempt["question_ids"] else []
    user_answers = json.loads(attempt["user_answers"]) if attempt["user_answers"] else {}

    placeholders = ",".join(["?"] * len(q_ids))
    questions_raw = conn.execute(
        f"SELECT * FROM aptitude_questions WHERE id IN ({placeholders})",
        q_ids
    ).fetchall()
    conn.close()

    q_dict = {q["id"]: q for q in questions_raw}
    detailed_questions = []

    for qid in q_ids:
        if qid in q_dict:
            q = dict(q_dict[qid])
            q["options"] = json.loads(q["options"]) if isinstance(q["options"], str) else q["options"]
            user_choice = user_answers.get(str(qid))
            q["user_choice"] = user_choice
            q["is_correct"] = (user_choice is not None and str(user_choice).strip().upper() == str(q["correct_option"]).strip().upper())
            q["is_unanswered"] = (user_choice is None or str(user_choice).strip() == "")
            detailed_questions.append(q)

    return render_template(
        "aptitude_result.html",
        attempt=attempt,
        questions=detailed_questions
    )

# ----------------- Interviewer Module (Interviewer-Led Sessions) -----------------

def require_interviewer():
    """Verify authenticated user has approved interviewer role."""
    user_id = session.get("user_id")
    if not user_id:
        return None
    conn = get_db_connection()
    user = conn.execute("SELECT * FROM users WHERE user_id = ?", (user_id,)).fetchone()
    conn.close()
    if user and user["role"] == "interviewer" and user["is_approved"] == 1:
        return user
    return None

@app.route("/interviewer/dashboard")
def interviewer_dashboard():
    interviewer = require_interviewer()
    if not interviewer:
        flash("Unauthorized. Interviewer access required.", "danger")
        return redirect(url_for("login"))

    conn = get_db_connection()
    # Fetch interviewer's sessions with candidate metadata
    sessions = conn.execute("""
        SELECT s.*, u.name as candidate_name, u.email as candidate_email, u.target_role as candidate_role
        FROM interviewer_sessions s
        LEFT JOIN users u ON s.candidate_id = u.user_id
        WHERE s.interviewer_id = ?
        ORDER BY s.created_at DESC
    """, (interviewer["user_id"],)).fetchall()

    # Available students for assignment
    students = conn.execute("""
        SELECT user_id, name, email, target_role, experience_level 
        FROM users 
        WHERE role = 'student' 
        ORDER BY name ASC
    """).fetchall()

    # Public and saved questions for session creation
    available_questions = conn.execute("""
        SELECT id, question_text, category, difficulty 
        FROM question_bank 
        ORDER BY id DESC LIMIT 50
    """).fetchall()

    conn.close()
    return render_template(
        "interviewer_dashboard.html",
        interviewer=interviewer,
        sessions=sessions,
        students=students,
        questions=available_questions
    )

@app.route("/interviewer/session/create", methods=["POST"])
def interviewer_create_session():
    interviewer = require_interviewer()
    if not interviewer:
        flash("Unauthorized. Interviewer access required.", "danger")
        return redirect(url_for("login"))

    title = request.form.get("title", "").strip() or "Technical Interview Session"
    job_role = request.form.get("job_role", "Software Developer")
    interview_type = request.form.get("interview_type", "Technical")
    difficulty = request.form.get("difficulty", "Medium")
    scheduled_time = request.form.get("scheduled_time", "").strip() or datetime.utcnow().strftime("%Y-%m-%d %H:%M")
    candidate_id = request.form.get("candidate_id")
    candidate_id = int(candidate_id) if candidate_id and candidate_id.isdigit() else None
    
    selected_q_ids = request.form.getlist("question_ids")
    q_ids_json = json.dumps([int(qid) for qid in selected_q_ids if qid.isdigit()])

    conn = get_db_connection()
    conn.execute("""
        INSERT INTO interviewer_sessions 
        (interviewer_id, candidate_id, title, job_role, interview_type, difficulty, scheduled_time, selected_question_ids)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
    """, (interviewer["user_id"], candidate_id, title, job_role, interview_type, difficulty, scheduled_time, q_ids_json))
    conn.commit()
    conn.close()

    flash("Interview session created successfully!", "success")
    return redirect(url_for("interviewer_dashboard"))

@app.route("/interviewer/session/<int:session_id>")
def interviewer_conduct_session(session_id):
    interviewer = require_interviewer()
    if not interviewer:
        flash("Unauthorized. Interviewer access required.", "danger")
        return redirect(url_for("login"))

    conn = get_db_connection()
    session_row = conn.execute("""
        SELECT s.*, u.name as candidate_name, u.email as candidate_email, u.target_role as candidate_role,
               u.college_name, u.education, u.technical_skills
        FROM interviewer_sessions s
        LEFT JOIN users u ON s.candidate_id = u.user_id
        WHERE s.session_id = ? AND s.interviewer_id = ?
    """, (session_id, interviewer["user_id"])).fetchone()

    if not session_row:
        conn.close()
        flash("Session not found or unauthorized.", "danger")
        return redirect(url_for("interviewer_dashboard"))

    # Load candidate's latest resume if candidate assigned
    candidate_resume = None
    if session_row["candidate_id"]:
        candidate_resume = conn.execute("""
            SELECT * FROM resumes WHERE user_id = ? ORDER BY uploaded_at DESC LIMIT 1
        """, (session_row["candidate_id"],)).fetchone()

    # Load selected questions
    q_ids = json.loads(session_row["selected_question_ids"]) if session_row["selected_question_ids"] else []
    selected_questions = []
    if q_ids:
        placeholders = ",".join(["?"] * len(q_ids))
        selected_questions = conn.execute(f"SELECT * FROM question_bank WHERE id IN ({placeholders})", q_ids).fetchall()

    conn.close()
    return render_template(
        "interviewer_room.html",
        iv_session=session_row,
        candidate_resume=candidate_resume,
        questions=selected_questions
    )

@app.route("/api/interviewer/session/evaluate", methods=["POST"])
def interviewer_submit_evaluation():
    interviewer = require_interviewer()
    if not interviewer:
        return jsonify({"status": "error", "message": "Unauthorized"}), 403

    data = request.get_json() or {}
    session_id = data.get("session_id")
    technical_score = float(data.get("technical_score", 0.0))
    communication_score = float(data.get("communication_score", 0.0))
    overall_score = float(data.get("overall_score", 0.0))
    meeting_notes = data.get("meeting_notes", "").strip()
    feedback = data.get("feedback", "").strip()

    conn = get_db_connection()
    conn.execute("""
        UPDATE interviewer_sessions SET
            status = 'completed',
            technical_score = ?,
            communication_score = ?,
            overall_score = ?,
            meeting_notes = ?,
            interviewer_feedback = ?,
            completed_at = CURRENT_TIMESTAMP
        WHERE session_id = ? AND interviewer_id = ?
    """, (technical_score, communication_score, overall_score, meeting_notes, feedback, session_id, interviewer["user_id"]))
    conn.commit()
    conn.close()

    return jsonify({
        "status": "success",
        "redirect_url": url_for("interviewer_dashboard")
    })

@app.route("/my-interviews")
def student_interviews_view():
    """Allow students to view their interviewer-led assigned sessions and feedback."""
    user_id = session.get("user_id")
    if not user_id:
        flash("Please log in to view your interviewer sessions.", "warning")
        return redirect(url_for("login"))

    conn = get_db_connection()
    sessions = conn.execute("""
        SELECT s.*, u.name as interviewer_name, u.email as interviewer_email
        FROM interviewer_sessions s
        JOIN users u ON s.interviewer_id = u.user_id
        WHERE s.candidate_id = ?
        ORDER BY s.created_at DESC
    """, (user_id,)).fetchall()
    conn.close()
    return render_template("student_interviews.html", sessions=sessions)

if __name__ == "__main__":
    app.run(debug=True, port=5000)

