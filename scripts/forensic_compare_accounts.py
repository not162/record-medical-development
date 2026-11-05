import os
import psycopg2
import json

db_url = os.environ["DATABASE_URL"]
conn = psycopg2.connect(db_url)
cur = conn.cursor()

# Query old accounts, admin, and new account
cur.execute("""
    SELECT id, username, email, hashed_password, full_name, role, is_active, created_at, updated_at
    FROM users 
    WHERE username IN ('admin', 'admin1', 'pasien_5c3a25', 'Pasien_umum', 'dev_1793440170_1', 'pasien_1793439135');
""")
rows = cur.fetchall()
colnames = [desc[0] for desc in cur.description]

print(f"{'Field':<18} | {'admin':<20} | {'pasien_5c3a25 (old)':<20} | {'Pasien_umum (old)':<20} | {'dev_..._1 (new)':<20}")
print("-" * 105)

data_by_uname = {r[1]: r for r in rows}
cols_to_compare = ['id', 'username', 'email', 'full_name', 'role', 'is_active', 'created_at', 'updated_at']

for col_idx, col_name in enumerate(colnames):
    if col_name == 'hashed_password':
        vals = [data_by_uname.get(k, [None]*9)[col_idx][:15] + '...' if data_by_uname.get(k) else 'N/A' 
                for k in ['admin', 'pasien_5c3a25', 'Pasien_umum', 'dev_1793440170_1']]
    else:
        vals = [str(data_by_uname.get(k, [None]*9)[col_idx]) if data_by_uname.get(k) else 'N/A' 
                for k in ['admin', 'pasien_5c3a25', 'Pasien_umum', 'dev_1793440170_1']]
    print(f"{col_name:<18} | {vals[0]:<20} | {vals[1]:<20} | {vals[2]:<20} | {vals[3]:<20}")

conn.close()

