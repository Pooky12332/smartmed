import os
from pathlib import Path

from cryptography.fernet import Fernet
from dotenv import load_dotenv
from sqlalchemy import Text
from sqlalchemy.types import TypeDecorator

load_dotenv()

ENV_FILE = Path(__file__).resolve().parent / ".env"

## Encryption key
# Personal details are encrypted with this key before they are saved in the database.
# It is kept in .env, never in the code or on GitHub. If there isn't one yet, a new key is made and saved there.
# Don't lose or change it: anything encrypted with the old key can't be read again.
ENCRYPTION_KEY = os.getenv("ENCRYPTION_KEY")

if not ENCRYPTION_KEY:
    ENCRYPTION_KEY = Fernet.generate_key().decode()
    lines = ENV_FILE.read_text(encoding="utf-8").splitlines() if ENV_FILE.exists() else []
    # Replaces an empty "ENCRYPTION_KEY=" line (e.g. copied from .env.example), otherwise adds one
    lines = [line for line in lines if not line.strip().startswith("ENCRYPTION_KEY")]
    lines.append(f"ENCRYPTION_KEY={ENCRYPTION_KEY}")
    ENV_FILE.write_text("\n".join(lines) + "\n", encoding="utf-8")
    os.environ["ENCRYPTION_KEY"] = ENCRYPTION_KEY
    print("[!] No ENCRYPTION_KEY in .env, so a new one was made and saved there")

fernet = Fernet(ENCRYPTION_KEY)



## Encrypted column
# Use this as a column type to encrypt the value when it is saved and decrypt it when it is read.
# The rest of the code still sees the normal value; only the database file holds the encrypted text.
class EncryptedString(TypeDecorator):
    impl = Text
    cache_ok = True

    def process_bind_param(self, value, dialect):
        if value is None:
            return None
        return fernet.encrypt(value.encode()).decode()

    def process_result_value(self, value, dialect):
        if value is None:
            return None
        return fernet.decrypt(value.encode()).decode()
