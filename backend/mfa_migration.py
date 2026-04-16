import asyncio
import os
import asyncpg
from dotenv import load_dotenv

load_dotenv()

async def run_migration():
    DB_URL = os.getenv("DATABASE_URL")
    if not DB_URL:
        print("DATABASE_URL not set in .env")
        return
        
    conn = await asyncpg.connect(DB_URL)
    
    try:
        print("Running MFA Database Migration...")
        
        # 1. Add otp_verified to users
        await conn.execute("""
            ALTER TABLE users ADD COLUMN IF NOT EXISTS otp_verified BOOLEAN DEFAULT FALSE;
        """)
        
        # 2. Create otp_codes table
        await conn.execute("""
            CREATE TABLE IF NOT EXISTS otp_codes (
                id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
                user_id INTEGER REFERENCES users(id) ON DELETE CASCADE,
                email TEXT NOT NULL,
                otp TEXT NOT NULL,
                expires_at TIMESTAMP NOT NULL,
                used BOOLEAN DEFAULT FALSE,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );
        """)

        print("✅ MFA Database Migration Complete! 'otp_verified' column and 'otp_codes' table created.")
    except Exception as e:
        print(f"Error executing migration: {e}")
    finally:
        await conn.close()

if __name__ == "__main__":
    asyncio.run(run_migration())
