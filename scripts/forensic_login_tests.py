import urllib.request
import json

base_url = "https://halo-skut.vercel.app/api/v1/auth/login"

test_cases = [
    # 1. Exact matches
    ("admin exact username", {"username_or_email": "admin", "password": "admin123_"}),
    ("admin exact email lowercase", {"username_or_email": "admin@rsukt.go.id", "password": "admin123_"}),
    # 2. Case sensitivity test
    ("admin uppercase username", {"username_or_email": "ADMIN", "password": "admin123_"}),
    ("admin uppercase email", {"username_or_email": "Admin@rsukt.go.id", "password": "admin123_"}),
    ("admin email with whitespace", {"username_or_email": " admin@rsukt.go.id ", "password": "admin123_"}),
    # 3. Old patient test_patient_a
    ("test_patient_a exact", {"username_or_email": "test_patient_a", "password": "Password123!"}),
    ("test_patient_a email", {"username_or_email": "patient_a@test.com", "password": "Password123!"}),
    ("test_patient_a uppercase email", {"username_or_email": "Patient_a@test.com", "password": "Password123!"}),
    ("test_patient_a email whitespace", {"username_or_email": " patient_a@test.com ", "password": "Password123!"}),
    # 4. Old patient Pasien_umum (note mixed case in DB: 'Pasien_umum' vs 'pasien_umum')
    ("Pasien_umum mixed case username", {"username_or_email": "Pasien_umum", "password": "Password123!"}),
    ("Pasien_umum lowercase username", {"username_or_email": "pasien_umum", "password": "Password123!"}),
    ("Pasien_umum email", {"username_or_email": "pasien@gmail.com", "password": "Password123!"}),
    ("Pasien_umum uppercase email", {"username_or_email": "Pasien@gmail.com", "password": "Password123!"}),
]

for label, payload in test_cases:
    req = urllib.request.Request(
        base_url,
        data=json.dumps(payload).encode("utf-8"),
        headers={"Content-Type": "application/json"}
    )
    try:
        with urllib.request.urlopen(req, timeout=10) as r:
            body = json.loads(r.read().decode())
            print(f"[SUCCESS 200] {label:<35} -> Token: {body.get('token_type')}, Role: {body.get('role')}")
    except urllib.error.HTTPError as e:
        err_body = e.read().decode()
        print(f"[FAIL {e.code}] {label:<35} -> {err_body}")
    except Exception as e:
        print(f"[ERROR] {label:<35} -> {e}")

