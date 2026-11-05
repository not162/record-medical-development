import psycopg2
import os

db_url = os.environ["DATABASE_URL"]

conn = psycopg2.connect(db_url)
cur = conn.cursor()

cur.execute("""
    SELECT id, username, email, role, is_active, 
           length(hashed_password) as hash_len,
           substring(hashed_password from 1 for 15) as hash_prefix,
           hashed_password,
           created_at
    FROM users 
    ORDER BY created_at ASC;
""")
users = cur.fetchall()

print(f"Total users in DB: {len(users)}\n")
print(f"{'Username':<22} | {'Role':<7} | {'Active':<6} | {'Len':<4} | {'Prefix':<15} | {'Format Pattern'}")
print("-" * 75)
for u in users:
    uid, uname, email, role, active, hlen, hprefix, hfull, created = u
    
    # Identify algorithm pattern
    pattern = "UNKNOWN"
    if not hfull:
        pattern = "NULL/EMPTY"
    elif hfull.startswith("$2b$") or hfull.startswith("$2a$") or hfull.startswith("$2y$"):
        pattern = "bcrypt"
    elif hfull.startswith("$argon2id$") or hfull.startswith("$argon2i$"):
        pattern = "argon2"
    elif hfull.startswith("pbkdf2:"):
        pattern = "pbkdf2"
    elif len(hfull) == 64 and all(c in "0123456789abcdefABCDEF" for c in hfull):
        pattern = "sha256_hex"
    elif len(hfull) == 32 and all(c in "0123456789abcdefABCDEF" for c in hfull):
        pattern = "md5_hex"
    elif hlen < 40:
        pattern = "POSSIBLE_PLAINTEXT"
        
    print(f"{uname:<22} | {role:<7} | {str(active):<6} | {hlen:<4} | {hprefix:<15} | {pattern}")

conn.close()

