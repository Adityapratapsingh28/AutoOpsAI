import asyncio
import asyncpg
import os

DATABASE_URL = "postgresql://postgres:GiV5P3T6YtVLqsIY@db.qmwtokynbmmruqpilpgo.supabase.co:5432/postgres"

async def test_conn():
    print(f"Attempting to connect to: {DATABASE_URL}")
    try:
        # Test without SSL first
        conn = await asyncpg.connect(DATABASE_URL, timeout=10)
        print("✅ Connection successful without explicit SSL!")
        await conn.close()
    except Exception as e:
        print(f"❌ Connection failed without SSL: {e}")
        
    try:
        # Test with ssl='require'
        print("Attempting to connect with ssl='require'...")
        conn = await asyncpg.connect(DATABASE_URL, ssl='require', timeout=10)
        print("✅ Connection successful with ssl='require'!")
        await conn.close()
    except Exception as e:
        print(f"❌ Connection failed with ssl='require': {e}")

if __name__ == "__main__":
    asyncio.run(test_conn())
