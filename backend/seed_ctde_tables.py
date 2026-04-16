import asyncio
import asyncpg
import os
from dotenv import load_dotenv

load_dotenv()

async def create_tables():
    DB_URL = os.getenv("DATABASE_URL")
    if not DB_URL:
        print("DATABASE_URL not set in .env")
        return
        
    conn = await asyncpg.connect(DB_URL)
    
    try:
        await conn.execute("""
            CREATE TABLE IF NOT EXISTS agent_policies (
                id SERIAL PRIMARY KEY,
                agent_role TEXT NOT NULL,
                category TEXT NOT NULL CHECK (category IN ('best_practices', 'common_failures', 'optimal_patterns')),
                rule_text TEXT NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                UNIQUE(agent_role, category, rule_text)
            );
            
            CREATE TABLE IF NOT EXISTS execution_insights (
                id SERIAL PRIMARY KEY,
                insight_data JSONB NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );
            
            -- If you ever drop it in the future, remove the entire table.
        """)
        print("Tables agent_policies and execution_insights successfully created in PostgreSQL.")
    except Exception as e:
        print(f"Error creating tables: {e}")
    finally:
        await conn.close()

if __name__ == "__main__":
    asyncio.run(create_tables())
