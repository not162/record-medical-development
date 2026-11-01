import re

# 1. Update services/ai-api/app/security/auth.py
auth_path = r"services/ai-api/app/security/auth.py"
with open(auth_path, "r", encoding="utf-8") as f:
    content = f.read()

# Replace bcrypt and password functions
new_auth_header = """import jwt
import datetime
from typing import Optional
from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.orm import Session

from app.config import settings
from app.database import get_db
from app.models import User
from app.security.password import (
    hash_password,
    verify_password,
    verify_and_check_rehash,
)

oauth2_scheme = OAuth2PasswordBearer(tokenUrl=f"{settings.API_V1_PREFIX}/auth/login")"""

# Pattern to replace from 'import bcrypt' down to end of verify_password
pattern = r"import bcrypt[\s\S]*?def verify_password\(plain_password: str, hashed_password: str\) -> bool:[\s\S]*?return False"
if re.search(pattern, content):
    content = re.sub(pattern, new_auth_header, content, count=1)
    with open(auth_path, "w", encoding="utf-8") as f:
        f.write(content)
    print("auth.py updated successfully!")
else:
    print("Could not match auth.py pattern")
