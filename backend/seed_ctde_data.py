import asyncio
import os
import json
from datetime import datetime, timedelta
import asyncpg
from dotenv import load_dotenv

load_dotenv()

async def seed_data():
    DB_URL = os.getenv("DATABASE_URL")
    if not DB_URL:
        print("DATABASE_URL not set in .env")
        return
        
    conn = await asyncpg.connect(DB_URL)
    
    try:
        print("Inserting dummy CTDE Governance Policies...")
        
        # 1. Analyze CSV File
        await conn.execute("""
            INSERT INTO agent_policies (agent_role, category, rule_text) VALUES 
            ('Analyze CSV File', 'best_practices', 'Always normalize whitespace and drop entirely empty rows before beginning analysis.'),
            ('Analyze CSV File', 'best_practices', 'When detecting financial figures, ensure they are cast to floats, stripping out currency symbols.'),
            ('Analyze CSV File', 'common_failures', 'Do not assume that the first row is always the header. Check data types across the first 5 rows.'),
            ('Analyze CSV File', 'optimal_patterns', 'Using pandas vectorized operations is highly preferred over iterating row-by-row for large datasets.')
            ON CONFLICT DO NOTHING;
        """)

        # 2. Schedule Zoom Meeting
        await conn.execute("""
            INSERT INTO agent_policies (agent_role, category, rule_text) VALUES 
            ('Schedule Zoom Meeting', 'best_practices', 'Always schedule meetings strictly between 9:00 AM and 5:00 PM EST.'),
            ('Schedule Zoom Meeting', 'common_failures', 'Failing to include the auto-generated passcode in the payload.'),
            ('Schedule Zoom Meeting', 'optimal_patterns', 'Using Server-to-Server OAuth grants the most stable connection.')
            ON CONFLICT DO NOTHING;
        """)

        # 3. Send Email Invitation
        await conn.execute("""
            INSERT INTO agent_policies (agent_role, category, rule_text) VALUES 
            ('Send Email Invitation', 'best_practices', 'Always use professional, Calendly-style HTML formatting with clear CTA buttons.'),
            ('Send Email Invitation', 'common_failures', 'Triggering spam filters by not including a plain-text fallback body.'),
            ('Send Email Invitation', 'optimal_patterns', 'Personalize the email greeting by fetching the recipient''s actual full name.')
            ON CONFLICT DO NOTHING;
        """)
        
        # 4. Generate Final Report
        await conn.execute("""
            INSERT INTO agent_policies (agent_role, category, rule_text) VALUES 
            ('Generate Final Report', 'best_practices', 'Include an executive summary prominently at the top of the Markdown file.'),
            ('Generate Final Report', 'common_failures', 'Generating Markdown tables without proper pipe alignment, breaking the UI rendering.')
            ON CONFLICT DO NOTHING;
        """)

        print("Inserting dummy Execution Insights...")
        
        # Insert some dummy historical insights
        for i in range(1, 6):
            insight = {
                "workflow_id": f"dummy-uuid-00{i}",
                "total_time_seconds": 45.2 + (i * 2.1),
                "agents_used": ["Analyze CSV File", "Generate Final Report"],
                "success_rate": 100,
                "efficiency_gain_seconds": 12.5 + i,
                "summary": f"Execution iteration #{i} completed seamlessly with optimized Pandas operations."
            }
            insight_json = json.dumps(insight)
            
            # Scatter timestamps in the past
            past_time = datetime.utcnow() - timedelta(hours=i*5)
            
            await conn.execute("""
                INSERT INTO execution_insights (insight_data, created_at) 
                VALUES ($1, $2)
            """, insight_json, past_time)

        print("✅ Success! The CTDE UI will now be populated.")
    except Exception as e:
        print(f"Error seeding data: {e}")
    finally:
        await conn.close()

if __name__ == "__main__":
    asyncio.run(seed_data())
