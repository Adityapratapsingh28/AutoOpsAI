import os
import asyncio
import asyncpg
import uuid
import random
from datetime import datetime, timedelta
from dotenv import load_dotenv

async def seed_dummy_data():
    print("=========================================")
    print("  AutoOps AI - Dummy Data Ingestion Tool ")
    print("=========================================")
    
    # Load environment variables
    # The .env file is in the project root
    env_path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), '.env')
    load_dotenv(env_path)
    
    db_url = os.getenv("DATABASE_URL")
    
    if not db_url:
        print("❌ Error: DATABASE_URL not found in environment variables.")
        return

    print("🌱 Connecting to the database...")
    
    try:
        conn = await asyncpg.connect(db_url)
        print("✅ Successfully connected to the database.")
        
        # 1. ORGANIZATIONS
        org_id = await conn.fetchval("SELECT id FROM organizations LIMIT 1")
        if not org_id:
            org_id = await conn.fetchval(
                "INSERT INTO organizations (name) VALUES ($1) RETURNING id", 
                "Acme Global Corp"
            )
            print("🏢 Created organization: Acme Global Corp")
            
        # Update all existing users to belong to this organization
        await conn.execute("UPDATE users SET org_id = $1", org_id)

        # 2. TEAMS
        teams_data = [
            ("Engineering", "engineering", "Builds the core AutoOps product and manages infrastructure."),
            ("Marketing", "marketing", "Grows the audience and handles campaigns."),
            ("Sales", "sales", "Closes deals and handles enterprise clients."),
            ("Human Resources", "hr", "Manages internal teams and recruitment.")
        ]
        
        team_ids = {}
        for name, slug, desc in teams_data:
            existing = await conn.fetchval("SELECT id FROM teams WHERE slug=$1", slug)
            if not existing:
                t_id = await conn.fetchval(
                    "INSERT INTO teams (name, slug, description) VALUES ($1, $2, $3) RETURNING id",
                    name, slug, desc
                )
                team_ids[slug] = t_id
            else:
                team_ids[slug] = existing
        print(f"👥 verified {len(teams_data)} teams in the database.")

        # 3. TEAM MEMBERS
        users = await conn.fetch("SELECT id, full_name, email, role FROM users")
        
        if users:
            for u in users:
                # Randomly assign to a team
                slugs = list(team_ids.keys())
                chosen_slug = random.choice(slugs)
                t_id = team_ids[chosen_slug]
                t_name = [t[0] for t in teams_data if t[1] == chosen_slug][0]
                
                # Setup designation
                designation = f"Senior {chosen_slug.capitalize()} Specialist"
                if u["role"] == "manager":
                    designation = f"Director of {chosen_slug.capitalize()}"
                
                # Check if already a member
                exists = await conn.fetchval("SELECT id FROM team_members WHERE user_id=$1", u['id'])
                if not exists:
                    await conn.execute("""
                        INSERT INTO team_members (user_id, team_id, team_name, work_email, designation) 
                        VALUES ($1, $2, $3, $4, $5)
                    """, u['id'], t_id, t_name, u['email'], designation)
            print("👔 Team members mapped successfully.")

        # 4. WORKFLOWS
        target_user_ids = [u['id'] for u in users] if users else None
        
        if target_user_ids:
            workflows_data = [
                {"input": "Analyze Q1 Sales data and generate performance metrics report", "status": "completed", "time": 12.5, "result": "Analyzed 1500 rows. Extracted 5 key correlations.", "agent_log": "Data Analyzer Agent successfully digested the attached sales dataset. Outliers detected and resolved."},
                {"input": "Draft an email to clients about the new UI update and attach the roadmap", "status": "completed", "time": 4.2, "result": "Email drafted and reviewed.", "agent_log": "Communication Agent composed a highly professional roadmap broadcast."},
                {"input": "Scrape competitor pricing page to dynamically adjust our tiers", "status": "failed", "time": 8.0, "result": "Access denied by Cloudflare WAF.", "agent_log": "Data Gatherer Agent hit an IP block on the target website."},
                {"input": "Schedule a Zoom meeting for next Friday sprint planning", "status": "completed", "time": 2.1, "result": "Zoom Meeting scheduled. Link broadcast to Slack.", "agent_log": "Scheduler Agent completed OAuth flow and generated the meeting room."},
                {"input": "Generate weekly engagement report from the Postgres database", "status": "running", "time": 5.5, "result": None, "agent_log": "SQL Agent is currently executing read-only queries against the replica."},
                {"input": "Find discrepancies in the Q4 accounting logs versus Stripe payouts", "status": "completed", "time": 45.2, "result": "Found $1.5k discrepancy mostly due to uncaptured failed transfers.", "agent_log": "Financial Analyst Agent ran a diff engine over the standard logs."}
            ]

            reports_created = 0
            for i in range(12): # Create 12 dummy workflows
                wd = random.choice(workflows_data)
                
                # For Postgres UUIDs, we just pass the string representation for a uuid4
                w_id = str(uuid.uuid4())
                u_id = random.choice(target_user_ids)
                
                # Distribute timestamps over the last 14 days
                days_ago = random.randint(0, 14)
                created_dt = datetime.now() - timedelta(days=days_ago)
                
                await conn.execute("""
                    INSERT INTO workflows (id, user_id, input_text, status, execution_time, result_summary, created_at)
                    VALUES ($1, $2, $3, $4, $5, $6, $7)
                """, w_id, u_id, wd['input'], wd['status'], wd['time'] + random.uniform(-1, 2), wd['result'], created_dt)

                # 5. LOGS (Agents executing)
                level = 'info'
                if wd['status'] == 'failed': level = 'error'
                elif wd['status'] == 'running': level = 'warning'
                
                await conn.execute("""
                    INSERT INTO logs (workflow_id, agent_name, message, level, created_at) 
                    VALUES ($1, $2, $3, $4, $5)
                """, w_id, "SystemOrchestrator", wd['agent_log'], level, created_dt + timedelta(seconds=1))

                # 6. REPORTS
                if wd['status'] == 'completed' and random.random() > 0.3: # ~70% of completed workflows generate a report
                    title = f"AI Execution Artifact: {wd['input'][:30]}..."
                    summary_md = f"""### Executive Review
This report was autonomously generated by AutoOps AI.
**Objective:** {wd['input']}

#### 📈 Key Findings
- **Resolution:** {wd['result']}
- The associated multi-agent graph performed flawlessly.
					
> *Note: Metrics are based on the latest context graph injected.*
"""
                    await conn.execute("""
                        INSERT INTO reports (workflow_id, title, summary, created_at)
                        VALUES ($1, $2, $3, $4)
                    """, w_id, title, summary_md, created_dt + timedelta(seconds=15))
                    reports_created += 1

            print(f"📊 12 dummy workflows generated along with {reports_created} reports.")

        # Ensure system_logs exists
        await conn.execute("""
            CREATE TABLE IF NOT EXISTS system_logs (
                id SERIAL PRIMARY KEY,
                message TEXT,
                level TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)

        # 7. SYSTEM LOGS
        sys_logs = [
            ("MetaOrchestrator booted and models loaded successfully.", "info"),
            ("Rate limit warning reached on Zoom API endpoint. Delaying requests.", "warning"),
            ("SMTP connection failed for email_tool. Max connection retries exceeded.", "error"),
            ("ChromaDB vector space vacuum completed. Reclaimed 15MB.", "info"),
            ("Unhandled exception in CSV parsing pipeline (ValueError). Captured successfully.", "warning")
        ]
        
        for msg, level in sys_logs:
            days_ago = random.randint(0, 5)
            dt = datetime.now() - timedelta(days=days_ago, hours=random.randint(0, 23))
            await conn.execute("""
                INSERT INTO system_logs (message, level, created_at)
                VALUES ($1, $2, $3)
            """, msg, level, dt)

        print("🛡️ System logs populated.")
        
        print("=========================================")
        print("✅ DUMMY DATA SEEDING COMPLETE")
        print("You can now refresh the Manager Dashboard.")
        print("=========================================")

        await conn.close()
        
    except Exception as e:
        print(f"❌ Failed to seed dummy data: {e}")

if __name__ == "__main__":
    asyncio.run(seed_dummy_data())
