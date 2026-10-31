import os
from dotenv import load_dotenv
import psycopg2

load_dotenv("services/ai-api/.env")
db_url = os.getenv("DATABASE_URL")
assert db_url, "DATABASE_URL not found!"

print("Connecting to PostgreSQL:", db_url.split("@")[-1])
conn = psycopg2.connect(db_url)
conn.autocommit = True
cur = conn.cursor()

print("Applying schema updates to PostgreSQL chat_sessions...")
cur.execute("ALTER TABLE chat_sessions ADD COLUMN IF NOT EXISTS summary TEXT;")
print("- Column 'summary' added/verified.")

cur.execute("CREATE INDEX IF NOT EXISTS ix_chat_sessions_user_updated ON chat_sessions(user_id, updated_at);")
print("- Index 'ix_chat_sessions_user_updated' created/verified.")

cur.execute("CREATE INDEX IF NOT EXISTS ix_chat_sessions_user_deleted_updated ON chat_sessions(user_id, is_deleted, updated_at);")
print("- Index 'ix_chat_sessions_user_deleted_updated' created/verified.")

cur.execute("""
    SELECT column_name, data_type 
    FROM information_schema.columns 
    WHERE table_name = 'chat_sessions' AND column_name = 'summary';
""")
res = cur.fetchall()
print("Verification:", res)

conn.close()
print("PostgreSQL migration completed successfully!")

