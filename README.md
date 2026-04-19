# ⚡ AutoOpsAI: The Autonomous AI Workforce

> **AutoOpsAI** is an Enterprise-grade Multi-Agent Workflow Engine. It translates plain English into a dynamic workforce of AI agents that analyze data, schedule meetings, send emails, and collaborate in real-time.

---

## 📖 The Tale of Two Companies

Let's look at how work gets done in 2024 vs. 2026.

**🏢 Company A (The Old Way)**
The Director of Operations receives a massive, messy CSV export containing hundreds of shipment delays. 
Normally, fixing this requires a chain reaction of human bottlenecks:
1. **The Data Analyst** spends 2 hours crunching the numbers and cleaning the data in Excel.
2. **The Project Manager** reads the Excel output, spends 45 minutes writing a summary report.
3. **The Secretary** spends 15 minutes finding a time that works, schedules a Zoom meeting for the engineering team, and broadcasts the link on Slack.

*Total time: ~3 hours.*

**🚀 Company B (Using AutoOpsAI)**
The Director uploads the CSV and types: 
*"Analyze this CSV, write a summary report, send the report to the team, and schedule a Zoom meeting with the engineering team."*

AutoOpsAI doesn't just run a rigid, hard-coded python script. It dynamically **spawns** a Data Analyst AI, a Manager AI, and a Secretary AI. It hands them tools (Pandas, Zoom OAuth, Slack API, SMTP). It watches them coordinate, share data, and complete the job while the Director watches their thoughts stream live on a beautiful dashboard.

*Total time: 30 seconds.*

---

## 🧠 The Novelty: The ODI Engine

The true magic of AutoOpsAI lies in its brain: the **ODI (Observe, Delegate, Intervene) Multi-Agent Framework**. 

Unlike standard linear chatbots, our ODI Engine gives agents true autonomy and memory:
*   **Observe:** The engine reads the prompt, searches ChromaDB vector memory for past contextual workflows, and observes the available Tool Catalog.
*   **Delegate:** It maps out a Directed Acyclic Graph (DAG). It realizes the *Secretary Agent* cannot act until the *Analysis Agent* finishes crunching the CSV. It delegates tasks in the exact optimal order.
*   **Intervene:** (CTDE - Centralized Training, Decentralized Execution). The MetaOrchestrator watches the agents talk to each other. If an agent hallucinates or crashes, the orchestrator intervenes, evaluates feedback, and securely updates shared policies.
   <img width="2950" height="1502" alt="odi" src="https://github.com/user-attachments/assets/4b816e4b-8e8b-4f96-800d-6c1e8a9bf5db" />


---

## 🏗️ System Wireframe

<img width="1600" height="1504" alt="image" src="https://github.com/user-attachments/assets/fb3183a0-0fc5-42e4-8bba-1dfdefe2f42f" />


---

## Demo Video




https://github.com/user-attachments/assets/67072f45-d55c-4a98-ba30-a43720ddb03f






## 🔨 The Arsenal (Tool Vault)

Our LLMs don't just talk; they act. They are equipped with a vault of deterministic tools:

| Tool | Capability |
|-----------|--------------|
| 📊 **csv_export_tool** | Bypasses simple reading. Generates a multi-sheet Excel file with correlations, distributions, and statistical summaries. |
| 📑 **report_tool** | Compiles upstream agent data into beautiful, human-readable markdown formats. |
| 📧 **email_tool** | SMTP integration to dynamically dispatch emails to external teams. |
| 💬 **slack_tool** | API-driven Slack webhook broadcasting. |
| 📹 **zoom_tool** | Secure OAuth Zoom meeting creation with password-protected invites and joining URLs. |
| 📅 **calendar_tool** | Postgres-backed scheduling database. |

---

## 🏆 Brownie Concepts Implemented (The Enterprise Steel)

To ensure this platform isn't just a "cool toy" but a true Enterprise-ready application, we built an absolute fortress of advanced computer science concepts around it. 

### 1. 🗄️ Redis Queue & Pub/Sub (Scalable Background Workers)
* **The Problem:** AI generation takes time. If 100 users click "Run" simultaneously, typical servers crash from out-of-memory (OOM) errors. Furthermore, Server-Sent Events (SSE) break when you have multiple load-balanced web workers.
* **The Solution:** We decoupled execution! FastApi instantly drops the workflow into a **Redis Queue** (`orchestrator_queue`) and tells the user "Queued." A dedicated, isolated background worker drains this list sequentially, completely preventing OOM crashes. Real-time streaming logs are broadcast via **Redis Pub/Sub** (`workflow:{id}:stream`), meaning you can scale to 1,000 backend servers and the frontend terminal stream will never drop.

### 2. ⚡ Redis Caching Layer (High-Speed Reads)
* **The Problem:** Dashboards and governance rules are read constantly but updated rarely. Hitting PostgreSQL every time slows the app down.
* **The Solution:** We implemented an asynchronous transparent Redis caching layer (`core/cache.py`). Dashboards and CTDE rules are served instantly from RAM. We use **Surgical Write-Through Invalidation**—the very millisecond a rule is updated via the Manager portal, the specific cache key is annihilated. 

### 3. 🛡️ Fault Tolerance & Global Exception Handling
* **The Problem:** AI workflows are notoriously brittle. LLMs hallucinate badly formatted JSON, or external APIs (like Groq) throw `429 Rate Limit` errors. Usually, this crashes the entire server.
* **The Solution:** We wrapped the agentic layer in custom `try/except` captures. If an agent crashes, the backend doesn't die. Instead, the orchestrator gracefully catches the error, streams the crash log directly to the user's UI using the SSE channel, and halts the specific DAG branch safely.

### 4. 🪃 Idempotency (Safe Retries)
* **The Problem:** What happens if a network glitch causes a user to submit the identical AI training rule twice? Or a manager accidentally clicks "Add Team Member" three times?
* **The Solution:** We enforced strict idempotency across the stack. Our PostgreSQL tables use composite `UNIQUE(agent_role, category, rule_text)` constraints paired with `ON CONFLICT DO NOTHING`. Bouncing duplicate database inserts effortlessly prevents database bloat. 

### 5. 🔑 Multi-Factor Authentication (Email OTP)
* **The Problem:** Standard passwords are easily breached through credential stuffing. Hackers gaining access to an AI workflow engine is disastrous.
* **The Solution:** We built a custom SMTP-based MFA system. After password verification, FastAPI holds the JWT token and emails a 6-digit rolling code to the user's inbox. The code expires strictly in 5 minutes via a dynamic DB table. The JWT is only granted upon `/verify-otp`.

### 6. 🚦 Protected APIs (Role-Based Access Control)
* **The Problem:** Interns shouldn't be able to delete AI memory or view company-wide execution analytics.
* **The Solution:** Heavy use of FastAPI dependency injection. Routes like `/api/manager` or `/api/governance` are locked behind `require_manager()`, halting any requests that lack a cryptographic 'manager' or 'admin' claim in their JWT token.

### 7. 🔒 HTTPS / Secure Communication
* **The Problem:** Plaintext HTTP exposes API keys and company data to packet sniffers.
* **The Solution:** AutoOpsAI runs behind a containerized NGINX reverse proxy (`nginx.conf`). All external and internal node communications are routed and encrypted appropriately to prevent man-in-the-middle attacks.

### 8. 🪪 Password Hashing
* **The Problem:** Storing raw passwords makes a database breach fatal.
* **The Solution:** We implemented industry-standard `bcrypt` via our `core/security.py` module. Passwords are mathematically secured via `get_password_hash` prior to database entry.

### 9. 📝 CRUD Operations (Human-in-the-Loop Governance)
* **The Problem:** Most AI projects lock their "prompts" or "rules" directly in the `.py` code. 
* **The Solution:** We built a full Human Governance dashboard. Managers can **C**reate, **R**ead, **U**pdate, and **D**elete AI memory and training policies dynamically via the UI. These are saved to PostgreSQL and injected into the MetaOrchestrator at runtime, giving humans ultimate override power over the machine.

---

## 🚀 Quickstart Guide

### Prerequisites
- Python 3.9+
- Node.js (React/Vite)
- PostgreSQL (or Supabase)
- Redis Server
- API Keys (Groq, Slack, Zoom, Email SMTP)

### 1. Launch the Stack
Copy `.env.example` to `.env` and fill in your keys.
```bash
# We recommend using docker-compose to spin up PostgreSQL, Redis, and Nginx automatically.
docker-compose up -d --build
```

*(If running locally for development without docker)*
```bash
# Terminal 1: Backend
cd backend
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
python -m uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload

# Terminal 2: Frontend
cd frontend-react
npm install
npm run dev
```
