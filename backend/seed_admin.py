"""Seed script to create demo users for role-based access control testing."""
import os
os.environ["DATABASE_URL"] = "sqlite:///./ovulite_local.db"

from app.auth.security import hash_password
from app.database import SessionLocal
from app.models.user import User

db = SessionLocal()
try:
    count = db.query(User).count()
    print(f"Existing users: {count}")
    
    if count == 0:
        password = "ovulite2026"
        password_hash = hash_password(password)
        
        # Demo users for role-based access control
        demo_users = [
            {
                "username": "admin",
                "full_name": "System Administrator",
                "role": "admin",
                "email": "admin@ovulite.local",
            },
            {
                "username": "lab_tech",
                "full_name": "Ahmed Lab Technician",
                "role": "embryologist",
                "email": "lab@ovulite.local",
            },
            {
                "username": "et_tech",
                "full_name": "Fatima ET Technician",
                "role": "et team",
                "email": "et@ovulite.local",
            },
        ]
        
        created_users = []
        for user_data in demo_users:
            user = User(
                username=user_data["username"],
                password_hash=password_hash,
                role=user_data["role"],
                full_name=user_data["full_name"],
                email=user_data.get("email"),
                active=True,
            )
            db.add(user)
            created_users.append(user_data)
        
        db.commit()
        
        print("\n✓ Demo users created successfully!")
        print(f"\nLogin Credentials (Password: {password})\n")
        print("=" * 70)
        for i, user_data in enumerate(created_users, 1):
            print(f"\n{i}. {user_data['full_name']} ({user_data['role'].upper()})")
            print(f"   Username: {user_data['username']}")
            print(f"   Password: {password}")
            print(f"   Email:    {user_data.get('email', 'N/A')}")
        print("\n" + "=" * 70)
        print("\nRole-Based Access:")
        print("- Admin: Full system control, user management, analytics")
        print("- Embryologist (lab_tech): Lab data entry, embryo grading, lab QC")
        print("- ET Team (et_tech): Recipient entry, embryo transfer, pregnancy outcomes")
        
    else:
        print("Users already exist, skipping seed.")
        print("\nTo reset and recreate users, drop and recreate the database:")
        print("DROP DATABASE ovulite; CREATE DATABASE ovulite;")
        
except Exception as e:
    print(f"ERROR: {e}")
    import traceback
    traceback.print_exc()
    db.rollback()
finally:
    db.close()
