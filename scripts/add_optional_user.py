path = r"services/ai-api/app/security/auth.py"
with open(path, "r", encoding="utf-8") as f:
    text = f.read()

optional_user_code = """
oauth2_optional_scheme = OAuth2PasswordBearer(
    tokenUrl=f"{settings.API_V1_PREFIX}/auth/login",
    auto_error=False
)

def get_optional_user(
    token: Optional[str] = Depends(oauth2_optional_scheme),
    db: Session = Depends(get_db)
) -> Optional[User]:
    \"\"\"Extracts authenticated user if token present, or returns None for guest tier.\"\"\"
    if not token:
        return None
    try:
        payload = decode_access_token(token)
        user_id: Optional[str] = payload.get("sub")
        if not user_id:
            return None
        user = db.query(User).filter(User.id == user_id).first()
        if user and user.is_active:
            return user
        return None
    except Exception:
        return None
"""

if "def get_optional_user" not in text:
    text += "\n" + optional_user_code
    with open(path, "w", encoding="utf-8") as f:
        f.write(text)
    print("get_optional_user added to auth.py!")
else:
    print("get_optional_user already exists.")
