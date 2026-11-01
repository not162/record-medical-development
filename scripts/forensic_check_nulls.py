import psycopg2

db_url = "postgresql://neondb_owner:npg_LaWS9INA1Qde@ep-rough-flower-b48s8vjt-pooler.c-6.us-east-2.aws.neon.tech/neondb?sslmode=require"
conn = psycopg2.connect(db_url)
cur = conn.cursor()

# Get column names of users table
cur.execute("""
    SELECT column_name, data_type, is_nullable 
    FROM information_schema.columns 
    WHERE table_name = 'users'
    ORDER BY ordinal_position;
""")
cols = cur.fetchall()
print("=== Columns of 'users' table ===")
for col, dtype, nullable in cols:
    print(f"  {col:<20} | {dtype:<15} | Nullable: {nullable}")

# Check for NULL values across all users
cur.execute("""
    SELECT id, username, email, role, is_active, created_at,
           (hashed_password IS NULL) as null_pwd,
           (email IS NULL) as null_email,
           (role IS NULL) as null_role,
           (is_active IS NULL) as null_active
    FROM users;
""")
user_records = cur.fetchall()
print(f"\nTotal users: {len(user_records)}")
null_count = 0
for r in user_records:
    uid, uname, email, role, is_active, created, null_pwd, null_email, null_role, null_active = r
    if null_pwd or null_email or null_role or null_active or not is_active:
        print(f"  Suspicious/Null account: {uname} ({email}) - Active: {is_active}, Role: {role}, Nulls: (pwd={null_pwd}, email={null_email}, role={null_role}, active={null_active})")
        null_count += 1

print(f"Total accounts with NULLs/inactive: {null_count}")

# Check for mixed casing in usernames and emails
print("\n=== Casing & Whitespace in DB ===")
cur.execute("SELECT id, username, email FROM users;")
for uid, uname, email in cur.fetchall():
    has_upper_email = any(c.isupper() for c in email) if email else False
    has_upper_uname = any(c.isupper() for c in uname) if uname else False
    has_space = (" " in email) if email else False or (" " in uname) if uname else False
    if has_upper_email or has_upper_uname or has_space:
        print(f"  Non-normalized in DB: Username='{uname}', Email='{email}' (upper_uname={has_upper_uname}, upper_email={has_upper_email}, space={has_space})")

conn.close()

