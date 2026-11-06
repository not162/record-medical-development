import os
import psycopg2
import bcrypt

db_url = os.environ["DATABASE_URL"]
conn = psycopg2.connect(db_url)
cur = conn.cursor()

cur.execute("""
    SELECT username, email, hashed_password 
    FROM users 
    WHERE username IN ('admin', 'admin1', 'pasien_5c3a25', 'Pasien_umum', 'test_patient_a', 'test_patient_b', 'pasien02');
""")
rows = cur.fetchall()

candidate_passwords = [
    "admin123_",
    "admin123",
    "AdminKlinis2026!#Safe",
    "admin_rsukt",
    "Password123!",
    "pasien123_",
    "pasien123",
    "12345678",
    "rsukt2026",
    "admin",
    "klinik2026",
    "rsukt_klinik",
    "password",
    "Password123",
    "rahasia123",
]

for uname, email, hpass in rows:
    print(f"Checking user: {uname} ({email})")
    matched = None
    for cand in candidate_passwords:
        try:
            if bcrypt.checkpw(cand.encode("utf-8"), hpass.encode("utf-8")):
                matched = cand
                break
        except Exception as e:
            print(f"  Error: {e}")
    if matched:
        print(f"  --> MATCHED CANDIDATE: '{matched}'")
    else:
        print(f"  --> NO MATCH among common candidates. Hash starts with: {hpass[:20]}")

conn.close()

