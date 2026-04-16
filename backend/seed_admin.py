import os
import asyncio
import asyncpg
from dotenv import load_dotenv

# Append path to import from the backend application
import sys
sys.path.append(os.path.dirname(os.path.abspath(__file__)))
from app.core.security import get_password_hash

async def seed_admin():
    print("=========================================")
    print("  AutoOps AI - Admin Bootstrapping Tool  ")
    print("=========================================")
    
    # Load environment variables
    load_dotenv(os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), '.env'))
    
    db_url = os.getenv("DATABASE_URL")
    
    if not db_url:
        print("❌ Error: DATABASE_URL not found in environment variables.")
        return

    print("🌱 Connecting to the database...")
    
    try:
        conn = await asyncpg.connect(db_url)
        print("✅ Successfully connected to the database.")
        
        email = "admin@autoops.com"
        password = "AdminPassword123!"
        hashed_pw = get_password_hash(password)
        full_name = "System Admin"
        role = "admin"
        
        # Check if admin already exists
        existing = await conn.fetchval("SELECT id FROM users WHERE email = $1", email)
        if existing:
            print(f"⚠️ Administrator '{email}' is already provisioned. (User ID: {existing})")
            print("You can log in at the frontend.")
        else:
            # Insert the new master admin
            query = """
                INSERT INTO users (full_name, email, password_hash, role, is_active)
                VALUES ($1, $2, $3, $4, $5)
                RETURNING id
            """
            new_id = await conn.fetchval(query, full_name, email, hashed_pw, role, True)
            print(f"🎉 Success! Master admin account generated.")
            print("-----------------------------------------")
            print("  🔑 CREDENTIALS")
            print(f"  Email    :  {email}")
            print(f"  Password :  {password}")
            print(f"  Role     :  {role}")
            print("-----------------------------------------")
            print("You may now log in to the platform with these credentials.")

        await conn.close()
        
    except Exception as e:
        print(f"❌ Failed to seed admin account: {e}")

if __name__ == "__main__":
    asyncio.run(seed_admin())
