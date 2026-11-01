import os
import json
import datetime
import psycopg2

db_url = os.getenv("DATABASE_URL", "postgresql://neondb_owner:npg_LaWS9INA1Qde@ep-rough-flower-b48s8vjt-pooler.c-6.us-east-2.aws.neon.tech/neondb?sslmode=require")

backup_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "database", "backups"))
os.makedirs(backup_dir, exist_ok=True)

ts = datetime.datetime.now(datetime.timezone.utc).strftime("%Y%m%d_%H%M%S")
backup_file = os.path.join(backup_dir, f"users_backup_{ts}.json")
rollback_sql_file = os.path.join(backup_dir, f"users_rollback_{ts}.sql")

print("=== 1.8 MANDATORY PRE-MIGRATION BACKUP ===")
print("Connecting to database...")

conn = psycopg2.connect(db_url)
cur = conn.cursor()

# 1. Fetch schema information
cur.execute("""
    SELECT column_name, data_type, is_nullable
    FROM information_schema.columns
    WHERE table_name = 'users'
    ORDER BY ordinal_position;
""")
schema = cur.fetchall()

# 2. Fetch all user records
cur.execute("SELECT * FROM users ORDER BY created_at ASC;")
rows = cur.fetchall()
col_names = [desc[0] for desc in cur.description]

records = []
rollback_statements = []

for row in rows:
    record = {}
    for i, col in enumerate(col_names):
        val = row[i]
        if isinstance(val, (datetime.datetime, datetime.date)):
            record[col] = val.isoformat()
        else:
            record[col] = val
    records.append(record)
    
    # Generate SQL rollback statement safely
    if record["full_name"]:
        clean_name = record["full_name"].replace("'", "''")
        full_name_sql = f"'{clean_name}'"
    else:
        full_name_sql = "NULL"

    rollback_statements.append(
        f"UPDATE users SET username = '{record['username']}', email = '{record['email']}', "
        f"hashed_password = '{record['hashed_password']}', full_name = {full_name_sql}, "
        f"role = '{record['role']}', is_active = {record['is_active']} "
        f"WHERE id = '{record['id']}';"
    )

backup_payload = {
    "timestamp": ts,
    "table": "users",
    "total_records": len(records),
    "schema": [{"column": s[0], "type": s[1], "nullable": s[2]} for s in schema],
    "records": records
}

# Write JSON backup
with open(backup_file, "w", encoding="utf-8") as f:
    json.dump(backup_payload, f, indent=2, ensure_ascii=False)

# Write SQL rollback
with open(rollback_sql_file, "w", encoding="utf-8") as f:
    f.write(f"-- ROLLBACK SCRIPT FOR USERS TABLE CREATED AT {ts} UTC\n")
    f.write(f"-- TOTAL RECORDS TO RESTORE: {len(rollback_statements)}\n\n")
    f.write("BEGIN;\n")
    for stmt in rollback_statements:
        f.write(stmt + "\n")
    f.write("COMMIT;\n")

# Verify backup can be read
with open(backup_file, "r", encoding="utf-8") as f:
    verify_data = json.load(f)

print(f"[OK] Backup JSON written to: {backup_file}")
print(f"[OK] Rollback SQL written to: {rollback_sql_file}")
print(f"[OK] Verification check passed: {len(verify_data['records'])} records successfully verified.")
print(f"[OK] Schema verified: {len(verify_data['schema'])} columns recorded.")

conn.close()
