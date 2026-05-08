import os
os.environ["DATABASE_URL"] = "postgresql://ovulite:ovulite_dev_password@localhost:5432/ovulite"

from app.database import SessionLocal
from app.models.user import User
from app.auth.security import verify_password

db = SessionLocal()

user = db.query(User).filter(User.username == "et_tech").first()

if not user:
    print("User not found")
else:
    print("Username:", user.username)
    print("Role:", user.role)
    print("Active:", user.active)
    print("Password hash:", user.password_hash[:50])
    print("Password valid:", verify_password("ovulite2026", user.password_hash))

db.close()