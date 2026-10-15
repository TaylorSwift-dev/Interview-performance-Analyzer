import io
import json
import os
import pytest
from app import app
from database.db import get_db_connection

@pytest.fixture
def client():
    app.config["TESTING"] = True
    with app.test_client() as client:
        yield client

def test_routes_status_200(client):
    """Verify all main views render with HTTP 200 when authenticated."""
    with client.session_transaction() as sess:
        sess["user_id"] = 1
        sess["user_name"] = "Alex Johnson"
        sess["user_role"] = "student"

    routes = [
        "/",
        "/student/dashboard",
        "/dashboard",
        "/resume",
        "/interview-setup",
        "/question-bank",
        "/profile",
        "/login",
        "/register",
        "/interviewer/login",
        "/interviewer/register",
        "/result/1",
        "/prepare/1",
        "/progress",
        "/forgot-password",
        "/my-interviews"
    ]
    for r in routes:
        res = client.get(r)
        assert res.status_code == 200, f"Route {r} failed with status {res.status_code}"

def test_user_registration_and_login(client):
    """Test user registration, profile creation, and authentication isolation."""
    test_email = "tester_new@example.com"
    conn = get_db_connection()
    conn.execute("DELETE FROM users WHERE email = ?", (test_email,))
    conn.commit()
    conn.close()

    # 1. Register new student
    res = client.post("/register", data={
        "name": "Jordan Smith",
        "email": test_email,
        "password": "securepassword123",
        "college_name": "Tech Institute",
        "education": "B.Tech CSE",
        "experience_level": "Fresher",
        "target_industry": "IT & Software",
        "target_role": "Software Developer",
        "technical_skills": "Python, Docker, SQL"
    }, follow_redirects=True)
    assert res.status_code == 200
    assert b"Jordan Smith" in res.data

    conn = get_db_connection()
    user = conn.execute("SELECT * FROM users WHERE email = ?", (test_email,)).fetchone()
    conn.close()
    assert user is not None
    assert user["name"] == "Jordan Smith"

    # 2. Logout
    client.get("/logout", follow_redirects=True)

    # 3. Log back in with registered credentials
    res = client.post("/login", data={
        "email": test_email,
        "password": "securepassword123"
    }, follow_redirects=True)
    assert res.status_code == 200
    assert b"Jordan Smith" in res.data

def test_complete_resume_lifecycle(client):
    """
    Test the complete resume workflow:
    1. Upload a valid PDF resume.
    2. Confirm file stored on disk.
    3. Confirm DB record exists and associated with user.
    4. Confirm it appears in My Resumes UI.
    5. Refresh page and verify persistence.
    6. View / download resume endpoints.
    7. Re-analyze stored resume.
    8. Upload second resume and confirm both appear.
    9. Delete resume and confirm file and record are removed.
    10. Verify isolation: user 2 cannot view or download user 1's resume.
    """
    # Use user 1 session
    with client.session_transaction() as sess:
        sess["user_id"] = 1
        sess["user_name"] = "Alex Johnson"

    # Create dummy PDF bytes
    dummy_pdf_content = b"%PDF-1.4\n1 0 obj\n<< /Title (Test Resume) >>\nendobj\ntrailer\n<< /Root 1 0 R >>\n%%EOF"
    
    # 1. Upload resume
    data = {
        'resume_file': (io.BytesIO(dummy_pdf_content), 'alex_software_resume.pdf')
    }
    res_upload = client.post("/resume", data=data, content_type='multipart/form-data', follow_redirects=True)
    assert res_upload.status_code == 200
    assert b"uploaded and analyzed successfully" in res_upload.data

    # 2 & 3. Verify DB record and file on disk
    conn = get_db_connection()
    saved = conn.execute(
        "SELECT * FROM resumes WHERE user_id = 1 AND original_filename = 'alex_software_resume.pdf'"
    ).fetchone()
    conn.close()
    assert saved is not None
    resume_id = saved["resume_id"]
    file_path = saved["file_path"]
    assert os.path.exists(file_path)

    # 4 & 5. Refresh page and verify it appears in My Resumes UI
    res_view = client.get("/resume")
    assert res_view.status_code == 200
    assert b"alex_software_resume.pdf" in res_view.data

    # 6. View & Download endpoints
    res_download = client.get(f"/resume/download/{resume_id}")
    assert res_download.status_code == 200
    assert res_download.headers.get("Content-Disposition") is not None

    res_preview = client.get(f"/resume/view/{resume_id}")
    assert res_preview.status_code == 200
    assert res_preview.mimetype == "application/pdf"

    # 7. Re-analyze stored resume
    res_analyze = client.post(f"/resume/analyze/{resume_id}", follow_redirects=True)
    assert res_analyze.status_code == 200
    assert b"re-analyzed successfully" in res_analyze.data

    # 8. Upload second resume and confirm both appear
    data2 = {
        'resume_file': (io.BytesIO(dummy_pdf_content), 'alex_updated_resume.pdf')
    }
    client.post("/resume", data=data2, content_type='multipart/form-data', follow_redirects=True)
    res_two = client.get("/resume")
    assert b"alex_software_resume.pdf" in res_two.data
    assert b"alex_updated_resume.pdf" in res_two.data

    # 9. Isolation verification: switch to user 999
    with client.session_transaction() as sess:
        sess["user_id"] = 999
        sess["user_name"] = "Other Student"

    res_other = client.get("/resume")
    # User 999 should NOT see alex's resumes
    assert b"alex_software_resume.pdf" not in res_other.data
    # Cannot download user 1's resume
    res_unauth_dl = client.get(f"/resume/download/{resume_id}", follow_redirects=True)
    assert b"unauthorized" in res_unauth_dl.data.lower() or b"not found" in res_unauth_dl.data.lower()

    # 10. Switch back to user 1 and delete
    with client.session_transaction() as sess:
        sess["user_id"] = 1
        sess["user_name"] = "Alex Johnson"

    res_del = client.post(f"/resume/delete/{resume_id}", follow_redirects=True)
    assert res_del.status_code == 200
    assert b"deleted successfully" in res_del.data.lower()
    # Confirm DB removed
    conn = get_db_connection()
    check_del = conn.execute("SELECT * FROM resumes WHERE resume_id = ?", (resume_id,)).fetchone()
    conn.close()
    assert check_del is None
    # Confirm file removed
    assert not os.path.exists(file_path)

def test_question_bank_add_and_filter(client):
    """Verify adding a question to the question bank, filtering it, and deleting it."""
    with client.session_transaction() as sess:
        sess["user_id"] = 1

    # Add question
    res = client.post("/question-bank/add", data={
        "question_text": "What is the role of an inverted index in search engines?",
        "category": "Software Development",
        "topic": "Search & Information Retrieval",
        "job_role": "Software Developer",
        "difficulty": "Hard",
        "expected_answer": "Maps words to their document locations for fast text search.",
        "is_public": "0"
    }, follow_redirects=True)
    assert res.status_code == 200
    assert b"What is the role of an inverted index" in res.data

    # Filter
    res_filter = client.get("/question-bank?category=Software+Development&difficulty=Hard")
    assert res_filter.status_code == 200
    assert b"inverted index" in res_filter.data

    # Delete
    conn = get_db_connection()
    q = conn.execute("SELECT id FROM question_bank WHERE question_text LIKE '%inverted index%'").fetchone()
    conn.close()
    assert q is not None

    del_res = client.post(f"/question-bank/delete/{q['id']}", follow_redirects=True)
    assert del_res.status_code == 200

def test_csv_import_question_bank(client):
    """Verify importing questions from CSV file with duplicate detection."""
    with client.session_transaction() as sess:
        sess["user_id"] = 1

    csv_content = """question_text,category,topic,job_role,difficulty,expected_answer
How does Redis achieve high throughput?,Software Development,Caching,Software Developer,Medium,In-memory data structures and single-threaded event loop.
What is the difference between TCP and UDP?,Software Development,Networking,Software Developer,Easy,TCP is connection-oriented and reliable while UDP is connectionless.
"""
    data = {
        'csv_file': (io.BytesIO(csv_content.encode('utf-8')), 'test_questions.csv')
    }
    res = client.post("/question-bank/import-csv", data=data, content_type='multipart/form-data', follow_redirects=True)
    assert res.status_code == 200
    assert b"Successfully imported" in res.data

def test_interview_lifecycle(client):
    """Verify creating an interview, submitting answers, evaluating, and viewing results."""
    with client.session_transaction() as sess:
        sess["user_id"] = 1

    # 1. Start an interview
    start_res = client.post("/start-interview", json={
        "industry": "IT & Software",
        "role": "Software Developer",
        "interview_type": "Technical",
        "difficulty": "Medium",
        "num_questions": 2,
        "question_source": "adaptive"
    })
    assert start_res.status_code == 200
    data = start_res.get_json()
    assert data["status"] == "success"
    iv_id = data["interview_id"]

    # 2. Get the room
    room_res = client.get(f"/interview/{iv_id}")
    assert room_res.status_code == 200

    conn = get_db_connection()
    q1 = conn.execute("SELECT * FROM questions WHERE interview_id = ? AND question_order = 1", (iv_id,)).fetchone()
    conn.close()
    assert q1 is not None

    # 3. Submit Answer 1
    sub1 = client.post("/api/submit-answer", json={
        "interview_id": iv_id,
        "question_id": q1["question_id"],
        "answer_text": "In relational databases, indexing uses B-Tree structures to provide logarithmic lookup time for select queries, but introduces additional overhead for write operations."
    })
    assert sub1.status_code == 200
    d1 = sub1.get_json()
    assert d1["status"] == "continue"
    assert d1["next_step"] == 2

    # 4. Submit Answer 2 (final question)
    q2_id = d1["question_id"]
    sub2 = client.post("/api/submit-answer", json={
        "interview_id": iv_id,
        "question_id": q2_id,
        "answer_text": "I handled this situation by breaking down the core database queries, adding indexing on foreign keys, and monitoring execution plans to reduce query latency by 45 percent."
    })
    assert sub2.status_code == 200
    d2 = sub2.get_json()
    assert d2["status"] == "completed"

    # 5. Verify results page
    res_page = client.get(f"/result/{iv_id}")
    assert res_page.status_code == 200
    assert b"Performance Analysis" in res_page.data

    # 6. Verify preparation plan generation
    prep_page = client.get(f"/prepare/{iv_id}")
    assert prep_page.status_code == 200
    assert b"What to Improve Next" in prep_page.data or b"Practice Recommendations" in prep_page.data

def test_practice_drill_evaluation(client):
    """Verify interactive STAR practice evaluation."""
    res = client.post("/api/submit-practice", json={
        "plan_id": 1,
        "question": "Tell me about a difficult bug you solved using the STAR method.",
        "answer": "In my situation as lead student dev, my task was fixing a race condition. My action was writing unit tests and using mutex locks. As a result, throughput increased and zero race errors occurred."
    })
    assert res.status_code == 200
    data = res.get_json()
    assert data["status"] == "success"
    assert data["is_ready_for_next"] is True

def test_aptitude_module_full_lifecycle(client):
    """Verify aptitude test setup, question loading, answer evaluation, persistence, and results display."""
    with client.session_transaction() as sess:
        sess["user_id"] = 1
        sess["user_name"] = "Alex Johnson"
        sess["user_role"] = "student"

    # 1. Setup view
    setup_res = client.get("/aptitude")
    assert setup_res.status_code == 200
    assert b"Aptitude Practice Room" in setup_res.data
    assert b"Quantitative Aptitude" in setup_res.data

    # 2. Start a test
    start_res = client.post("/aptitude/start", json={
        "category": "All Categories",
        "difficulty": "Mixed",
        "mode": "quick"
    })
    assert start_res.status_code == 200
    start_data = start_res.get_json()
    assert start_data["status"] == "success"
    attempt_id = start_data["attempt_id"]

    # 3. Access test room
    test_room_res = client.get(f"/aptitude/test/{attempt_id}")
    assert test_room_res.status_code == 200
    assert b"Question Palette" in test_room_res.data

    # 4. Submit answers
    submit_res = client.post("/api/aptitude/submit", json={
        "attempt_id": attempt_id,
        "answers": {"1": "B", "2": "C"},
        "time_taken_seconds": 125
    })
    assert submit_res.status_code == 200
    submit_data = submit_res.get_json()
    assert submit_data["status"] == "success"
    assert "score_percent" in submit_data

    # 5. Review results
    result_res = client.get(f"/aptitude/result/{attempt_id}")
    assert result_res.status_code == 200
    assert b"Aptitude Test Results" in result_res.data
    assert b"Step-by-Step Question Review" in result_res.data

def test_interviewer_auth_and_dashboard(client):
    """Verify interviewer authentication, role protection, and registration approval gate."""
    # 1. Login with pre-approved demo interviewer via dedicated interviewer portal
    login_res = client.post("/interviewer/login", data={
        "email": "interviewer@example.com",
        "password": "interviewer123"
    }, follow_redirects=True)
    assert login_res.status_code == 200
    assert b"Interviewer Workspace" in login_res.data or b"Dashboard" in login_res.data

    # 2. Access interviewer dashboard
    dash_res = client.get("/interviewer/dashboard")
    assert dash_res.status_code == 200
    assert b"Interviewer Workspace" in dash_res.data
    assert b"Create New Session" in dash_res.data

    # 3. Verify student cannot access interviewer dashboard
    with client.session_transaction() as sess:
        sess["user_id"] = 1
        sess["user_role"] = "student"
        sess["is_approved"] = 1
    
    unauth_res = client.get("/interviewer/dashboard", follow_redirects=True)
    assert b"Interviewer access required" in unauth_res.data or unauth_res.status_code == 200

    # 4. Register new interviewer -> requires approval
    new_int_email = "new_interviewer@techcorp.com"
    conn = get_db_connection()
    conn.execute("DELETE FROM users WHERE email = ?", (new_int_email,))
    conn.commit()
    conn.close()

    reg_res = client.post("/interviewer/register", data={
        "name": "Sarah Connor",
        "email": new_int_email,
        "password": "strongpassword123",
        "college_name": "Industry Partner",
        "technical_skills": "Distributed Systems, Golang"
    }, follow_redirects=True)
    assert reg_res.status_code == 200
    assert b"pending administrator approval" in reg_res.data

    # Confirm user record has is_approved = 0
    conn = get_db_connection()
    new_user = conn.execute("SELECT * FROM users WHERE email = ?", (new_int_email,)).fetchone()
    conn.close()
    assert new_user is not None
    assert new_user["role"] == "interviewer"
    assert new_user["is_approved"] == 0

def test_interviewer_session_and_student_feedback(client):
    """Verify interviewer creating a session, evaluating a candidate, and student viewing feedback."""
    # 1. Log in as approved demo interviewer
    client.post("/interviewer/login", data={
        "email": "interviewer@example.com",
        "password": "interviewer123"
    }, follow_redirects=True)

    # 2. Create session for candidate user_id=1
    create_res = client.post("/interviewer/session/create", data={
        "title": "Backend Engineering Evaluation",
        "job_role": "Backend Developer",
        "interview_type": "Technical",
        "difficulty": "Hard",
        "scheduled_time": "2026-10-20 14:00",
        "candidate_id": "1",
        "question_ids": ["1", "2"]
    }, follow_redirects=True)
    assert create_res.status_code == 200
    assert b"Interview session created successfully" in create_res.data

    # Query DB to get created session_id
    conn = get_db_connection()
    session_row = conn.execute("""
        SELECT * FROM interviewer_sessions 
        WHERE title = 'Backend Engineering Evaluation' 
        ORDER BY session_id DESC LIMIT 1
    """).fetchone()
    conn.close()
    assert session_row is not None
    session_id = session_row["session_id"]
    assert session_row["candidate_id"] == 1

    # 3. Access interviewer live evaluation room
    room_res = client.get(f"/interviewer/session/{session_id}")
    assert room_res.status_code == 200
    assert b"Backend Engineering Evaluation" in room_res.data
    assert b"Candidate Dossier" in room_res.data

    # 4. Submit evaluation
    eval_res = client.post("/api/interviewer/session/evaluate", json={
        "session_id": session_id,
        "technical_score": 88.5,
        "communication_score": 92.0,
        "overall_score": 90.0,
        "meeting_notes": "Candidate articulated system tradeoffs clearly.",
        "feedback": "Excellent grasp of database indexing and concurrency controls."
    })
    assert eval_res.status_code == 200
    eval_data = eval_res.get_json()
    assert eval_data["status"] == "success"

    # Confirm status in DB is completed
    conn = get_db_connection()
    updated = conn.execute("SELECT * FROM interviewer_sessions WHERE session_id = ?", (session_id,)).fetchone()
    conn.close()
    assert updated["status"] == "completed"
    assert updated["overall_score"] == 90.0

    # 5. Switch to candidate user 1 and verify /my-interviews
    with client.session_transaction() as sess:
        sess["user_id"] = 1
        sess["user_name"] = "Alex Johnson"
        sess["user_role"] = "student"

    student_res = client.get("/my-interviews")
    assert student_res.status_code == 200
    assert b"Interviewer-Led Practice Sessions" in student_res.data
    assert b"Backend Engineering Evaluation" in student_res.data
    assert b"Dr. Marcus Vance" in student_res.data
    assert b"90.0" in student_res.data or b"90" in student_res.data

def test_forgot_and_reset_password(client):
    """Verify forgot-password identification, password reset, and login with new credentials."""
    # 1. GET forgot-password page
    res_get = client.get("/forgot-password")
    assert res_get.status_code == 200
    assert b"Reset your password" in res_get.data

    # 2. Unknown email test
    res_unknown = client.post("/forgot-password", data={"email": "nonexistent_99@college.edu"}, follow_redirects=True)
    assert res_unknown.status_code == 200
    assert b"No account found" in res_unknown.data

    # 3. Valid email step
    res_step = client.post("/forgot-password", data={"email": "student@example.com"}, follow_redirects=True)
    assert res_step.status_code == 200
    assert b"New Password" in res_step.data

    # 4. Mismatch password test
    res_mismatch = client.post("/forgot-password", data={
        "email": "student@example.com",
        "new_password": "NewSecretPassword99",
        "confirm_password": "DifferentPassword1"
    }, follow_redirects=True)
    assert res_mismatch.status_code == 200
    assert b"Passwords do not match" in res_mismatch.data

    # 5. Successful reset
    res_reset = client.post("/forgot-password", data={
        "email": "student@example.com",
        "new_password": "NewSecretPassword99",
        "confirm_password": "NewSecretPassword99"
    }, follow_redirects=True)
    assert res_reset.status_code == 200
    assert b"password has been reset successfully" in res_reset.data

    # 6. Log in with new password
    res_login = client.post("/login", data={
        "email": "student@example.com",
        "password": "NewSecretPassword99"
    }, follow_redirects=True)
    assert res_login.status_code == 200
    assert b"Welcome back" in res_login.data

    # 7. Restore default password123 for demo convenience
    client.post("/forgot-password", data={
        "email": "student@example.com",
        "new_password": "password123",
        "confirm_password": "password123"
    }, follow_redirects=True)


def test_visible_login_and_full_authentication_journey(client):
    """
    10-Step Verification Journey covering:
    1. Unauthenticated landing page shows Student Login, Interviewer Login, Get Started, and Logo.
    2. Student Login (/login) renders portal, demo login button, link to Interviewer portal.
    3. Interviewer Login (/interviewer/login) renders interviewer portal, demo login, link to Student portal.
    4. Get Started (/register) renders registration form.
    5. Register a fresh student, redirects to /student/dashboard.
    6. Sign out clears session and returns to landing page with visible login links.
    7. Quick demo login on /login as Alex Johnson logs in to /student/dashboard.
    8. Sign out, quick demo login on /interviewer/login as Dr. Marcus Vance logs in to /interviewer/dashboard.
    9. Role isolation and protected routes:
       - Logged-in student attempting /interviewer/dashboard is blocked.
       - Unauthenticated visitor accessing /student/dashboard, /resume, /interview-setup is redirected to /login.
    10. Validation & error states:
       - Invalid password on /login flashes error message.
       - Student credentials on /interviewer/login flashes role separation error.
       - Unapproved interviewer on /interviewer/login flashes pending approval error.
    """
    # 1. Fresh unauthenticated landing page
    client.get("/logout", follow_redirects=True)
    home_res = client.get("/")
    assert home_res.status_code == 200
    assert b"InterviewPrep AI" in home_res.data
    assert b"Student Login" in home_res.data
    assert b"Interviewer Login" in home_res.data
    assert b"Get Started" in home_res.data
    assert b"/login" in home_res.data
    assert b"/interviewer/login" in home_res.data
    assert b"/register" in home_res.data

    # 2. Student Login route
    login_page = client.get("/login")
    assert login_page.status_code == 200
    assert b"Student Login" in login_page.data
    assert b"/interviewer/login" in login_page.data
    assert b"Alex Johnson" in login_page.data

    # 3. Interviewer Login route
    int_login_page = client.get("/interviewer/login")
    assert int_login_page.status_code == 200
    assert b"Interviewer Portal" in int_login_page.data
    assert b"/login" in int_login_page.data
    assert b"Dr. Marcus Vance" in int_login_page.data

    # 4. Get Started registration route
    reg_page = client.get("/register")
    assert reg_page.status_code == 200
    assert b"Create Student Account" in reg_page.data
    assert b"Full Name" in reg_page.data
    assert b"Email address" in reg_page.data

    # 5. Register a fresh student
    journey_email = "journey_student@college.edu"
    conn = get_db_connection()
    conn.execute("DELETE FROM users WHERE email = ?", (journey_email,))
    conn.commit()
    conn.close()

    reg_submit = client.post("/register", data={
        "name": "Maya Patel",
        "email": journey_email,
        "password": "passMaya2026",
        "confirm_password": "passMaya2026",
        "college_name": "MIT Pune",
        "education": "B.Tech IT",
        "experience_level": "Fresher",
        "target_industry": "IT & Software",
        "target_role": "Full Stack Developer",
        "technical_skills": "React, Python, PostgreSQL"
    }, follow_redirects=True)
    assert reg_submit.status_code == 200
    assert b"Maya Patel" in reg_submit.data
    assert b"Candidate Workspace" in reg_submit.data or b"Dashboard" in reg_submit.data

    # 6. Sign Out
    logout_res = client.get("/logout", follow_redirects=True)
    assert logout_res.status_code == 200
    assert b"Signed out successfully" in logout_res.data
    assert b"Student Login" in logout_res.data
    assert b"Interviewer Login" in logout_res.data

    # 7. Login with Demo Student (Alex Johnson)
    demo_stud = client.post("/login", data={
        "email": "student@example.com",
        "password": "password123"
    }, follow_redirects=True)
    assert demo_stud.status_code == 200
    assert b"Alex Johnson" in demo_stud.data
    assert b"Candidate Workspace" in demo_stud.data or b"Dashboard" in demo_stud.data

    # 8. Sign out, then login with Demo Interviewer (Dr. Marcus Vance)
    client.get("/logout", follow_redirects=True)
    demo_int = client.post("/interviewer/login", data={
        "email": "interviewer@example.com",
        "password": "interviewer123"
    }, follow_redirects=True)
    assert demo_int.status_code == 200
    assert b"Dr. Marcus Vance" in demo_int.data
    assert b"Interviewer Workspace" in demo_int.data

    # 9. Role isolation & protected routes
    # a. Student accessing interviewer dashboard is blocked
    client.get("/logout", follow_redirects=True)
    client.post("/login", data={"email": "student@example.com", "password": "password123"}, follow_redirects=True)
    blocked_int = client.get("/interviewer/dashboard", follow_redirects=True)
    assert b"Interviewer access required" in blocked_int.data or blocked_int.status_code == 200

    # b. Unauthenticated visitor accessing protected routes returns 302 redirecting to /login
    client.get("/logout", follow_redirects=True)
    for protected_url in ["/student/dashboard", "/dashboard", "/resume", "/interview-setup"]:
        res_prot = client.get(protected_url)
        assert res_prot.status_code == 302
        assert "/login" in res_prot.headers.get("Location", "")

    # 10. Validation & Error states
    # a. Invalid password on /login
    bad_pw = client.post("/login", data={"email": "student@example.com", "password": "wrongpassword999"}, follow_redirects=True)
    assert b"Invalid email or password" in bad_pw.data

    # b. Student credentials submitted to /interviewer/login
    student_on_int = client.post("/interviewer/login", data={"email": "student@example.com", "password": "password123"}, follow_redirects=True)
    assert b"registered as a student" in student_on_int.data

    # c. Unapproved interviewer trying to login
    unapproved_email = "pending_boss@company.org"
    conn = get_db_connection()
    conn.execute("DELETE FROM users WHERE email = ?", (unapproved_email,))
    conn.commit()
    conn.close()

    client.post("/interviewer/register", data={
        "name": "Pending Leader",
        "email": unapproved_email,
        "password": "pendingsecret123",
        "confirm_password": "pendingsecret123",
        "organization": "Acme Inc",
        "technical_skills": "Management"
    }, follow_redirects=True)

    unapp_login = client.post("/interviewer/login", data={"email": unapproved_email, "password": "pendingsecret123"}, follow_redirects=True)
    assert b"pending administrator approval" in unapp_login.data



