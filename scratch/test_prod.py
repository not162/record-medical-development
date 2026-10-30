import urllib.request
import json

def test_endpoint(name, url, method="GET", data=None, headers=None):
    if headers is None:
        headers = {}
    body = json.dumps(data).encode("utf-8") if data else None
    if data:
        headers["Content-Type"] = "application/json"
    req = urllib.request.Request(url, data=body, headers=headers, method=method)
    try:
        res = urllib.request.urlopen(req)
        content = res.read().decode("utf-8", errors="ignore")
        print(f"[PASS] {name}: Status {res.status} (Length {len(content)})")
        try:
            return json.loads(content)
        except Exception:
            return content
    except urllib.error.HTTPError as e:
        err_content = e.read().decode("utf-8", errors="ignore")
        print(f"[FAIL] {name}: Status {e.code} - {err_content[:200]}")
        return None
    except Exception as e:
        print(f"[ERROR] {name}: {e}")
        return None

print("=== FINAL VERIFICATION: HALO-SKUT.VERCEL.APP ===")
# 1. Login page HTML
test_endpoint("Login Page HTML", "https://halo-skut.vercel.app/login")

# 2. Login API
login_res = test_endpoint("Login API (admin@rsukt.go.id)", "https://halo-skut.vercel.app/api/v1/auth/login", "POST", {
    "username_or_email": "admin@rsukt.go.id",
    "password": "admin123_"
})

if login_res and isinstance(login_res, dict) and "access_token" in login_res:
    token = login_res["access_token"]
    role = login_res.get("role")
    auth_hdr = {"Authorization": f"Bearer {token}"}
    print(f"-> Token acquired: {token[:20]}... Role: {role}")
    
    # 3. Auth Me
    test_endpoint("Auth /me API", "https://halo-skut.vercel.app/api/v1/auth/me", "GET", headers=auth_hdr)
    
    # 4. Admin Dashboard API
    test_endpoint("Admin Dashboard API", "https://halo-skut.vercel.app/api/v1/admin/dashboard", "GET", headers=auth_hdr)

    # 5. Create Clinical Session
    sess = test_endpoint("Chat Create Session", "https://halo-skut.vercel.app/api/v1/chat/sessions", "POST", {
        "title": "Evaluasi Nyeri Prekordial & Dispnea"
    }, headers=auth_hdr)
    
    if sess and "id" in sess:
        sess_id = sess["id"]
        # 6. Send Clinical Anamnesis Message
        chat_msg = test_endpoint("Chat Post Clinical Message", "https://halo-skut.vercel.app/api/v1/chat/messages", "POST", {
            "session_id": sess_id,
            "content": "Pasien mengeluhkan sesak napas saat aktivitas ringan, batuk dengan dahak, tensi 135/85 mmHg.",
            "reasoning_mode": "thinking"
        }, headers=auth_hdr)

# 7. Also test with username 'admin'
test_endpoint("Login API with username 'admin'", "https://halo-skut.vercel.app/api/v1/auth/login", "POST", {
    "username_or_email": "admin",
    "password": "admin123_"
})
