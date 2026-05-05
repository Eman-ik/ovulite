"""Direct database seeder for local development (bypasses migrations)."""
import os
import sys
import psycopg2
from psycopg2.extras import execute_values

# Add app to path so we can import from it
sys.path.insert(0, os.path.dirname(__file__))

from app.auth.security import hash_password

# Database connection
DB_URL = "postgresql://ovulite:ovulite_dev_password@localhost:5432/ovulite"

def create_users_table(cursor):
    """Create users table if it doesn't exist."""
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS users (
            user_id SERIAL PRIMARY KEY,
            username VARCHAR(100) UNIQUE NOT NULL,
            password_hash VARCHAR(255) NOT NULL,
            role VARCHAR(50),
            full_name VARCHAR(200),
            email VARCHAR(200),
            active BOOLEAN DEFAULT true,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            last_login TIMESTAMP,
            CHECK (role IN ('admin', 'veterinarian', 'embryologist', 'viewer', 'et team'))
        )
    """)

def seed_demo_users(cursor, conn):
    """Seed demo users for role-based access control."""
    password = "ovulite2026"
    
    # Use the app's hashing function (argon2 via passlib)
    password_hash = hash_password(password)
    
    demo_users = [
        ("admin", password_hash, "admin", "System Administrator", "admin@ovulite.local", True),
        ("lab_tech", password_hash, "embryologist", "Ahmed Lab Technician", "lab@ovulite.local", True),
        ("et_tech", password_hash, "et team", "Fatima ET Technician", "et@ovulite.local", True),
    ]
    
    execute_values(
        cursor,
        """
        INSERT INTO users (username, password_hash, role, full_name, email, active)
        VALUES %s
        ON CONFLICT (username) DO NOTHING
        """,
        demo_users
    )
    conn.commit()

def main():
    """Main seeder function."""
    try:
        conn = psycopg2.connect(DB_URL)
        cursor = conn.cursor()
        
        print("Creating users table...")
        create_users_table(cursor)
        conn.commit()
        
        # Check existing users
        cursor.execute("SELECT COUNT(*) FROM users")
        count = cursor.fetchone()[0]
        print(f"Existing users: {count}")
        
        if count == 0:
            print("\nSeeding demo users...")
            seed_demo_users(cursor, conn)
            
            # Fetch and display created users
            cursor.execute("""
                SELECT username, role, full_name, email 
                FROM users 
                ORDER BY user_id
            """)
            users = cursor.fetchall()
            
            print("\n✓ Demo users created successfully!")
            print(f"\nLogin Credentials (Password: ovulite2026)\n")
            print("=" * 70)
            
            for i, (username, role, full_name, email) in enumerate(users, 1):
                print(f"\n{i}. {full_name} ({role.upper()})")
                print(f"   Username: {username}")
                print(f"   Password: ovulite2026")
                print(f"   Email:    {email or 'N/A'}")
            
            print("\n" + "=" * 70)
            print("\nRole-Based Access:")
            print("- Admin: Full system control, user management, analytics")
            print("- Embryologist (lab_tech): Lab data entry, embryo grading, lab QC")
            print("- ET Team (et_tech): Recipient entry, embryo transfer, pregnancy outcomes")
        else:
            print("Users already exist, skipping seed.")
            
            # Display existing users
            cursor.execute("""
                SELECT username, role, full_name, email 
                FROM users 
                ORDER BY created_at
            """)
            users = cursor.fetchall()
            
            print("\nExisting users:")
            for username, role, full_name, email in users:
                print(f"  - {username} ({role}): {full_name}")
        
        cursor.close()
        conn.close()
        
    except Exception as e:
        print(f"ERROR: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    main()
