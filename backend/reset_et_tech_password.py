import os
os.environ["DATABASE_URL"] = "postgresql://ovulite:ovulite_dev_password@localhost:5432/ovulite"

from app.database import SessionLocal
from app.models.user import User
from app.auth.security import hash_password

db = SessionLocal()

try:
    user = db.query(User).filter(User.username == "et_tech").first()

    if not user:
        print("et_tech user not found")
    else:
        user.password_hash = hash_password("ovulite2026")
        user.role = "et team"
        user.active = True
        db.commit()
        print("et_tech password reset successfully")
        print("Username: et_tech")
        print("Password: ovulite2026")
        print("Role:", user.role)

finally:
    db.close()