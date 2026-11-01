import os
import psycopg2

db_url = os.getenv("DATABASE_URL", "postgresql://neondb_owner:npg_LaWS9INA1Qde@ep-rough-flower-b48s8vjt-pooler.c-6.us-east-2.aws.neon.tech/neondb?sslmode=require")

conn = psycopg2.connect(db_url)
cur = conn.cursor()

print("=== 1.3 & 1.4 EMAIL NORMALIZATION & LEGACY AUDIT ===")

# 1. Check for case-insensitive duplicate emails
cur.execute("""
    SELECT LOWER(TRIM(email)), COUNT(*) 
    FROM users 
    GROUP BY LOWER(TRIM(email)) 
    HAVING COUNT(*) > 1;
""")
dup_emails = cur.fetchall()

# 2. Check for case-insensitive duplicate usernames
cur.execute("""
    SELECT LOWER(TRIM(username)), COUNT(*) 
    FROM users 
    GROUP BY LOWER(TRIM(username)) 
    HAVING COUNT(*) > 1;
""")
dup_unames = cur.fetchall()

print(f"Duplicate emails found: {len(dup_emails)}")
for de in dup_emails:
    print(f"  Conflict Email: {de[0]} (Count: {de[1]})")

print(f"Duplicate usernames found: {len(dup_unames)}")
for du in dup_unames:
    print(f"  Conflict Username: {du[0]} (Count: {du[1]})")

if not dup_emails and not dup_unames:
    print("\n[OK] No conflicts found! Safe to execute idempotent normalization migration.")
    
    # Check rows that need update
    cur.execute("""
        SELECT id, username, email 
        FROM users 
        WHERE email != LOWER(TRIM(email)) OR username != TRIM(username);
    """)
    to_update = cur.fetchall()
    print(f"Rows requiring whitespace/casing normalization: {len(to_update)}")
    for r in to_update:
        print(f"  Row ID {r[0]}: Username='{r[1]}', Email='{r[2]}'")

conn.close()
