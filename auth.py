import os
import secrets
from datetime import UTC, datetime, timedelta

import jwt
from dotenv import load_dotenv
from pwdlib import PasswordHash

load_dotenv()

## Passwords are never stored as plain text, only as a hash
password_hash = PasswordHash.recommended()


def hash_password(password: str) -> str:
    return password_hash.hash(password)


def verify_password(password: str, hashed_password: str) -> bool:
    return password_hash.verify(password, hashed_password)



## Login tokens
# The secret key signs the tokens. Keep it in .env, never in the code or on GitHub.
# If it isn't set, a random one is made, so everyone is logged out when the server restarts.
SECRET_KEY = os.getenv("SECRET_KEY") or secrets.token_hex(32)
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 30

# Checked when no account matches, so a wrong username takes as long as a wrong password
DUMMY_HASH = password_hash.hash("dummy-password")


def create_access_token(user_id: int) -> str:
    expire = datetime.now(UTC) + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    return jwt.encode({"sub": str(user_id), "exp": expire}, SECRET_KEY, algorithm=ALGORITHM)
