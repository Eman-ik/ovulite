"""One-time script to seed the admin user."""
import os
os.environ["DATABASE_URL"] = "postgresql://ovulite:ovulite_dev_password@localhost:5432/ovulite"

from app.auth.security import hash_password
from app.database import SessionLocal
from app.models.user import User

db = SessionLocal()
try:
    count = db.query(User).count()
    print(f"Existing users: {count}")
    if count == 0:
        h = hash_password("ovulite2026")
        admin = User(
            username="admin",
            password_hash=h,
            role="admin",
            full_name="System Administrator",
        )
        db.add(admin)
        db.commit()
        db.refresh(admin)
        print(f"Admin created! user_id={admin.user_id}, username={admin.username}")
    else:
        print("Users already exist, skipping seed.")
except Exception as e:
    print(f"ERROR: {e}")
    db.rollback()
finally:
    db.close()
