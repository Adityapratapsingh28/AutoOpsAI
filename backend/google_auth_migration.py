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
        print("Running Google Auth Database Migration...")
        
        # 1. Drop NOT NULL on password_hash
        await conn.execute("""
            ALTER TABLE users ALTER COLUMN password_hash DROP NOT NULL;
        """)
        
        # 2. Add provider column with default 'email'
        await conn.execute("""
            ALTER TABLE users ADD COLUMN IF NOT EXISTS provider TEXT DEFAULT 'email';
        """)
        
        # 3. Add google_id column
        await conn.execute("""
            ALTER TABLE users ADD COLUMN IF NOT EXISTS google_id TEXT UNIQUE;
        """)

        print("✅ Google Auth Database Migration Complete!")
        
        # Output the schema to verify
        schema_query = """
        SELECT column_name, data_type, is_nullable, column_default
        FROM information_schema.columns
        WHERE table_name = 'users';
        """
        columns = await conn.fetch(schema_query)
        print("\n--- Updated `users` Table Schema ---")
        for col in columns:
            print(f"- {col['column_name']} ({col['data_type']}) | Nullable: {col['is_nullable']} | Default: {col['column_default']}")
            
    except Exception as e:
        print(f"Error executing migration: {e}")
    finally:
        await conn.close()

if __name__ == "__main__":
    asyncio.run(run_migration())
