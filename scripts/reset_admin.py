import os
import sys
import argparse
import psycopg2

# Add services/ai-api to path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "services", "ai-api")))

from app.security.password import hash_password

def reset_admin(email: str, new_password: str, username: str = "admin"):
    """
    Safely resets administrator credentials without hardcoding secrets.
    Ensures role remains ADMIN and password uses standard bcrypt.
    """
    if not email or not new_password:
        raise ValueError("Email and new_password are required.")

    if len(new_password) < 8:
        raise ValueError("Password must be at least 8 characters.")

    db_url = os.environ["DATABASE_URL"]
    
    conn = psycopg2.connect(db_url)
    cur = conn.cursor()
    
    clean_email = email.strip().lower()
    clean_username = username.strip().lower()
    new_hash = hash_password(new_password)
    
    # Check if admin exists
    cur.execute("SELECT id, username, email, role FROM users WHERE LOWER(email) = %s OR LOWER(username) = %s;", (clean_email, clean_username))
    admin_row = cur.fetchone()
    
    if admin_row:
        admin_id, old_uname, old_email, old_role = admin_row
        cur.execute("""
            UPDATE users 
            SET hashed_password = %s, role = 'ADMIN', is_active = TRUE, updated_at = NOW()
            WHERE id = %s;
        """, (new_hash, admin_id))
        conn.commit()
        print(f"[OK] Administrator ID '{admin_id}' ({clean_email}) password successfully updated to standard bcrypt. Role verified: ADMIN.")
    else:
        # Create admin
        import uuid
        new_id = str(uuid.uuid4())
        cur.execute("""
            INSERT INTO users (id, username, email, hashed_password, full_name, role, is_active, created_at, updated_at)
            VALUES (%s, %s, %s, %s, 'Administrator Medis RSUKT', 'ADMIN', TRUE, NOW(), NOW());
        """, (new_id, clean_username, clean_email, new_hash))
        conn.commit()
        print(f"[OK] New Administrator account created with ID '{new_id}' ({clean_email}). Role: ADMIN.")
        
    conn.close()

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Emergency Admin Recovery Script - Web Klinik RSUKT")
    parser.add_argument("--email", default=os.getenv("ADMIN_RECOVERY_EMAIL", "admin@rsukt.go.id"), help="Admin email")
    parser.add_argument("--password", default=os.getenv("ADMIN_RECOVERY_PASSWORD"), help="New admin password")
    parser.add_argument("--username", default="admin", help="Admin username")
    
    args = parser.parse_args()
    
    pwd = args.password or os.getenv("ADMIN_RECOVERY_PASSWORD")
    if not pwd:
        # Safe interactive prompt
        import getpass
        pwd = getpass.getpass("Enter new admin password (hidden): ")
        
    reset_admin(args.email, pwd, args.username)
