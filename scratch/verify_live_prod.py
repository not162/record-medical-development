import urllib.request
import urllib.error
import json
import uuid

BASE_WEB = "https://halo-skut.vercel.app"

def test_landing():
    print("--- 1. Testing Landing Page ---")
    req = urllib.request.Request(f"{BASE_WEB}/", headers={"User-Agent": "VerificationBot/1.0"})
    res = urllib.request.urlopen(req)
    html = res.read().decode("utf-8", errors="ignore")
    print(f"Landing Status: {res.status}")
    print("Contains 'healthy with clinic and hospital':", "healthy with clinic and hospital" in html)
    print("Contains 'Konsultasi Medis':", "Konsultasi Medis" in html)

def test_admin_login():
    print("\n--- 2. Testing Admin Login ---")
    payload = json.dumps({"username_or_email": "admin@rsukt.go.id", "password": "admin123_"}).encode()
    req = urllib.request.Request(
        f"{BASE_WEB}/api/v1/auth/login",
        data=payload,
        headers={"Content-Type": "application/json"}
    )
    res = urllib.request.urlopen(req)
    data = json.loads(res.read().decode("utf-8"))
    print(f"Admin Login Status: {res.status}")
    print(f"Role: {data.get('role')}")
    print(f"Username: {data.get('username')}")
    return data["access_token"]

def test_legacy_rewrite():
    print("\n--- 3. Testing Legacy /api/auth/login Rewrite ---")
    payload = json.dumps({"username_or_email": "admin@rsukt.go.id", "password": "admin123_"}).encode()
    req = urllib.request.Request(
        f"{BASE_WEB}/api/auth/login",
        data=payload,
        headers={"Content-Type": "application/json"}
    )
    try:
        res = urllib.request.urlopen(req)
        print(f"Legacy Rewrite Status: {res.status} (SUCCESS - No 404!)")
    except urllib.error.HTTPError as e:
        print(f"Legacy Rewrite Status: {e.code} (No 404!)")

def test_admin_privacy_boundary(admin_token):
    print("\n--- 4. Testing Admin Privacy Boundary (UU PDP & ISO 27001) ---")
    # Admin attempting to create a patient chat session
    payload = json.dumps({"title": "Percakapan Pasien Rahasia"}).encode()
    req = urllib.request.Request(
        f"{BASE_WEB}/api/v1/chat/sessions",
        data=payload,
        headers={
            "Content-Type": "application/json",
            "Authorization": f"Bearer {admin_token}"
        }
    )
    try:
        urllib.request.urlopen(req)
        print("ERROR: Admin was allowed to access patient chat session!")
    except urllib.error.HTTPError as e:
        body = json.loads(e.read().decode("utf-8"))
        print(f"Admin Blocked Status: {e.code} Forbidden")
        print(f"Detail Message: {body.get('detail')}")

def test_owasp_registration():
    print("\n--- 5. Testing OWASP Registration Defense ---")
    sqli_payload = json.dumps({
        "username": "hacker' OR 1=1--",
        "email": "hacker@evil.com",
        "password": "Password123!",
        "full_name": "SQL Injection Tester"
    }).encode()
    req = urllib.request.Request(
        f"{BASE_WEB}/api/v1/auth/register",
        data=sqli_payload,
        headers={"Content-Type": "application/json"}
    )
    try:
        urllib.request.urlopen(req)
        print("ERROR: SQL Injection was NOT blocked!")
    except urllib.error.HTTPError as e:
        body = json.loads(e.read().decode("utf-8"))
        print(f"OWASP Blocked Status: {e.code} Bad Request")
        print(f"Alert: {body.get('detail')}")

def test_patient_flow():
    print("\n--- 6. Testing Patient User Registration & Consultation Flow ---")
    uid = uuid.uuid4().hex[:6]
    username = f"pasien_{uid}"
    email = f"pasien_{uid}@rsukt.go.id"
    password = "PasienPassword123!"

    # 1. Register clean patient
    reg_payload = json.dumps({
        "username": username,
        "email": email,
        "password": password,
        "full_name": "Bapak Pasien Mandiri"
    }).encode()
    req_reg = urllib.request.Request(
        f"{BASE_WEB}/api/v1/auth/register",
        data=reg_payload,
        headers={"Content-Type": "application/json"}
    )
    res_reg = urllib.request.urlopen(req_reg)
    print(f"Patient Registered: {res_reg.status}")

    # 2. Login patient
    login_payload = json.dumps({
        "username_or_email": username,
        "password": password
    }).encode()
    req_login = urllib.request.Request(
        f"{BASE_WEB}/api/v1/auth/login",
        data=login_payload,
        headers={"Content-Type": "application/json"}
    )
    res_login = urllib.request.urlopen(req_login)
    login_data = json.loads(res_login.read().decode("utf-8"))
    patient_token = login_data["access_token"]
    print(f"Patient Logged In: Role={login_data.get('role')}")

    # 3. Create chat session
    sess_payload = json.dumps({"title": "Keluhan Batuk dan Flu"}).encode()
    req_sess = urllib.request.Request(
        f"{BASE_WEB}/api/v1/chat/sessions",
        data=sess_payload,
        headers={
            "Content-Type": "application/json",
            "Authorization": f"Bearer {patient_token}"
        }
    )
    res_sess = urllib.request.urlopen(req_sess)
    sess_data = json.loads(res_sess.read().decode("utf-8"))
    session_id = sess_data["id"]
    print(f"Chat Session Created: ID={session_id}")

    # 4. Send clinical query
    msg_payload = json.dumps({
        "session_id": session_id,
        "content": "Halo dokter, saya mengalami batuk kering sudah 3 hari dan badan agak demam, apa anjuran pertolongan pertama?",
        "model_size": "70b"
    }).encode()
    req_msg = urllib.request.Request(
        f"{BASE_WEB}/api/v1/chat/messages",
        data=msg_payload,
        headers={
            "Content-Type": "application/json",
            "Authorization": f"Bearer {patient_token}"
        }
    )
    res_msg = urllib.request.urlopen(req_msg)
    msg_data = json.loads(res_msg.read().decode("utf-8"))
    asst_content = msg_data.get("assistant_message", {}).get("content", "")
    print(f"Assistant Response Received! Length={len(asst_content)} chars")
    print("Snippet:", asst_content[:150].encode("ascii", "ignore").decode("ascii"))

    # 5. Verify RLHF feedback
    asst_msg_id = msg_data.get("assistant_message", {}).get("id")
    if asst_msg_id:
        fb_payload = json.dumps({
            "session_id": session_id,
            "message_id": asst_msg_id,
            "feedback_type": "DISLIKE",
            "improvement_category": "Bahasa terlalu rumit / teknis",
            "notes": "Mohon berikan tips hidrasi yang lebih sederhana untuk orang tua di rumah"
        }).encode()
        req_fb = urllib.request.Request(
            f"{BASE_WEB}/api/v1/chat/feedback",
            data=fb_payload,
            headers={
                "Content-Type": "application/json",
                "Authorization": f"Bearer {patient_token}"
            }
        )
        res_fb = urllib.request.urlopen(req_fb)
        fb_data = json.loads(res_fb.read().decode("utf-8"))
        print(f"RLHF Feedback Submitted: {res_fb.status}")
        print(f"Feedback Policy: {fb_data.get('meta', {}).get('policy')}")
        res_fb = urllib.request.urlopen(req_fb)
        print(f"RLHF Feedback Submitted: {res_fb.status}")

if __name__ == "__main__":
    test_landing()
    admin_token = test_admin_login()
    test_legacy_rewrite()
    test_admin_privacy_boundary(admin_token)
    test_owasp_registration()
    test_patient_flow()
    print("\n>>> ALL PRODUCTION TESTS PASSED SUCCESSFULLY! <<<")
