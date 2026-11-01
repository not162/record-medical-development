path = r"services/ai-api/app/routes/auth.py"
with open(path, "r", encoding="utf-8") as f:
    text = f.read()

# Remove the diagnostic logging block
diag_block = """    # Diagnostic logging (Masked per 0.3)
    if "@" in clean_target:
        parts = clean_target.split("@")
        masked_target = f"{parts[0][:2]}***@{parts[1]}"
    else:
        masked_target = f"{clean_target[:2]}***" if len(clean_target) >= 2 else "***"
        
    user_found = user is not None
    hash_prefix = user.hashed_password[:7] if (user and user.hashed_password) else "NONE"
    
    # Verifikasi kata sandi dengan multi-format & lazy migration
    is_valid, needs_rehash, new_hash = verify_and_check_rehash(req.password, user.hashed_password if user else None)
    if is_valid and needs_rehash and new_hash and user:
        try:
            user.hashed_password = new_hash
            user.updated_at = datetime.datetime.now(datetime.timezone.utc)
            db.commit()
            print(f"[*] Password lazily re-hashed to standard bcrypt 12 for user '{user.username}'.")
        except Exception as _rehash_err:
            db.rollback()
            print(f"[!] Warning: lazy rehash error: {_rehash_err}")

    user_status = "ACTIVE" if (user and user.is_active) else ("INACTIVE" if user else "NOT_FOUND")
    user_role = user.role if user else "UNKNOWN"

    print(
        f"[DIAGNOSTIC_AUTH_LOG] target='{masked_target}' found={user_found} "
        f"hash_prefix='{hash_prefix}' pwd_valid={is_valid} status='{user_status}' "
        f"role='{user_role}' provider='custom_jwt_bcrypt'",
        flush=True
    )"""

clean_block = """    # Verifikasi kata sandi dengan multi-format & lazy migration
    is_valid, needs_rehash, new_hash = verify_and_check_rehash(req.password, user.hashed_password if user else None)
    if is_valid and needs_rehash and new_hash and user:
        try:
            user.hashed_password = new_hash
            user.updated_at = datetime.datetime.now(datetime.timezone.utc)
            db.commit()
        except Exception as _rehash_err:
            db.rollback()"""

if diag_block in text:
    text = text.replace(diag_block, clean_block)
    with open(path, "w", encoding="utf-8") as f:
        f.write(text)
    print("Cleaned up diagnostic logging successfully!")
else:
    print("Could not find diagnostic block directly, checking normalized...")
    text = text.replace("\r\n", "\n")
    diag_block = diag_block.replace("\r\n", "\n")
    clean_block = clean_block.replace("\r\n", "\n")
    if diag_block in text:
        text = text.replace(diag_block, clean_block)
        with open(path, "w", encoding="utf-8") as f:
            f.write(text)
        print("Cleaned up diagnostic logging (normalized)!")
    else:
        print("Not matched.")
