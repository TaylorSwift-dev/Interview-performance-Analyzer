from app import app

client = app.test_client()

print("Running test suite on all Flask routes...")
all_passed = True

# 1. Unauthenticated public routes
public_routes = [
    ("/", 200),
    ("/login", 200),
    ("/register", 200),
    ("/interviewer/login", 200),
    ("/interviewer/register", 200),
    ("/forgot-password", 200),
    # Protected routes must return 302 redirecting unauthenticated visitors
    ("/dashboard", 302),
    ("/student/dashboard", 302),
    ("/resume", 302),
    ("/interview-setup", 302),
    ("/progress", 302),
]

for route, expected_code in public_routes:
    res = client.get(route)
    if res.status_code == expected_code:
        print(f"  [PASS] Unauth {route} returned status {res.status_code}")
    else:
        print(f"  [FAIL] Unauth {route} returned status {res.status_code}, expected {expected_code}")
        all_passed = False

# 2. Authenticated student session
with client.session_transaction() as sess:
    sess["user_id"] = 1
    sess["user_name"] = "Alex Johnson"
    sess["user_role"] = "student"

authenticated_routes = [
    ("/dashboard", 200),
    ("/student/dashboard", 200),
    ("/resume", 200),
    ("/interview-setup", 200),
    ("/progress", 200),
    ("/result/1", 200),
    ("/prepare/1", 200),
]

for route, expected_code in authenticated_routes:
    res = client.get(route)
    if res.status_code == expected_code:
        print(f"  [PASS] Auth {route} returned status {res.status_code}")
    else:
        print(f"  [FAIL] Auth {route} returned status {res.status_code}, expected {expected_code}")
        all_passed = False

if all_passed:
    print("\nALL ROUTES AND TEMPLATES PASSED VERIFICATION!")
else:
    print("\nSome routes encountered errors.")
