# ⚡ AutoOps AI

**Enterprise-grade Multi-Agent AI Workflow Automation Platform**

AutoOps AI lets users describe workflows in plain English, then automatically designs and executes a team of AI agents to carry out the task — including real tool execution (CSV analysis, email, Slack, Zoom, calendar, SQL) with live-streamed results.

---

## 🏗️ Architecture

```
Frontend (HTML/JS/CSS)
    ↓
Backend API (FastAPI — Business Layer)
    ↓
Orchestrator Service (Adapter Layer)
    ↓
Core Engine (ODI Multi-Agent Framework — "Brain")
    ↓
Tool Execution Layer (CSV, Email, Slack, Zoom, Calendar, SQL)
    ↓
Database (PostgreSQL / Supabase) + External APIs
```

### Design Principle

| Layer | Role | Modified? |
|-------|------|-----------|
| **Core Engine** | Multi-agent orchestration, LLM reasoning, memory, CTDE | ❌ Read-only dependency |
| **Backend API** | Auth, routing, file uploads, SSE streaming | ✅ Business layer |
| **Tool Layer** | External tool execution injected via callback | ✅ New addition |
| **Frontend** | 7-page SPA with real-time workflow visualization | ✅ Full UI |

---

## 📁 Project Structure

```
autoops-ai/
│
├── .env                              # Environment variables (DB, JWT, API keys)
├── Dockerfile                        # Production container
├── docker-compose.yml                # API + PostgreSQL orchestration
│
├── ODI-based-multi-agent-Framework/  # 🧠 Core Engine (UNCHANGED)
│   ├── orchestrator/
│   │   └── meta_orchestrator.py      # Main orchestration pipeline (9 steps)
│   ├── llm/
│   │   └── llm_service.py           # Groq/OpenAI LLM integration
│   ├── execution/
│   │   └── async_executor.py         # Parallel DAG agent execution
│   ├── memory/
│   │   ├── memory_manager.py         # Semantic memory coordination
│   │   ├── vector_store.py           # ChromaDB persistent vector store
│   │   └── embedding_service.py      # SentenceTransformers embeddings
│   ├── factory/
│   │   └── agent_factory.py          # Dynamic agent creation
│   ├── agents/
│   │   └── base_agent.py             # LLM-powered agent base class
│   └── utils/
│       └── config.py                 # Core engine configuration
│
├── backend/                          # 🔧 FastAPI Business Layer
│   ├── app/
│   │   ├── main.py                   # FastAPI app entry point
│   │   ├── core/
│   │   │   ├── config.py             # App settings (from .env)
│   │   │   ├── database.py           # asyncpg connection pool
│   │   │   └── security.py           # JWT + bcrypt auth
│   │   ├── routes/
│   │   │   ├── auth.py               # POST /api/auth/signup, /login
│   │   │   ├── workflow.py           # POST /api/workflow/run, GET /stream/{id}
│   │   │   ├── dashboard.py          # GET /api/dashboard/stats
│   │   │   ├── files.py              # POST /api/files/upload
│   │   │   └── meetings.py           # CRUD /api/meetings
│   │   ├── schemas/                  # Pydantic request/response models
│   │   ├── services/
│   │   │   ├── orchestrator_service.py  # ⭐ Core integration adapter
│   │   │   ├── tool_dispatcher.py       # Agent→Tool mapping + execution
│   │   │   └── workflow_service.py      # DB workflow CRUD
│   │   └── tools/                    # 🔨 Tool Execution Layer
│   │       ├── base_tool.py          # Abstract tool interface
│   │       ├── csv_tool.py           # CSV reading + analysis
│   │       ├── csv_export_tool.py    # CSV analysis → Excel output file
│   │       ├── report_tool.py        # Structured report generation
│   │       ├── email_tool.py         # SMTP email sending
│   │       ├── email_reader_tool.py  # IMAP email reading
│   │       ├── slack_tool.py         # Slack API messaging
│   │       ├── zoom_tool.py          # Zoom meeting creation (OAuth)
│   │       ├── calendar_tool.py      # Meeting scheduling (DB)
│   │       └── sql_tool.py           # Read-only SQL queries
│   ├── migrations/
│   │   └── 001_initial_schema.sql    # Full database schema
│   └── requirements.txt              # Python dependencies
│
└── frontend/                         # 🎨 Employee Portal UI
    ├── css/styles.css                # Full design system
    ├── index.html                    # Login / Signup
    ├── dashboard.html                # Stats + recent workflows
    ├── workflow.html                 # Run workflow + live execution
    ├── history.html                  # Workflow history
    ├── files.html                    # File management
    ├── schedule.html                 # Meeting scheduler
    ├── settings.html                 # User settings
    └── js/
        ├── api.js                    # JWT-injected fetch client
        ├── auth.js                   # Login/signup logic
        ├── workflow.js               # SSE streaming + DAG visualization
        ├── dashboard.js              # Dashboard data loading
        ├── files.js                  # File upload/list
        ├── history.js                # Workflow history table
        ├── schedule.js               # Meeting CRUD
        └── settings.js               # User profile management
```

---

## 🔧 Tech Stack

| Component | Technology |
|-----------|-----------|
| **LLM** | Groq API (Llama 3.3 70B) via OpenAI client |
| **Backend** | FastAPI + Uvicorn |
| **Database** | PostgreSQL (Supabase) via asyncpg |
| **Vector Store** | ChromaDB 0.5.23 (persistent, local) |
| **Embeddings** | SentenceTransformers (all-MiniLM-L6-v2) |
| **Auth** | bcrypt + PyJWT |
| **Streaming** | Server-Sent Events (SSE) via sse-starlette |
| **Frontend** | Vanilla HTML/CSS/JS (no framework) |
| **Email** | SMTP (Gmail) |
| **Deployment** | Docker + docker-compose |

---

## ⚡ Core Engine Pipeline (9 Steps)

The MetaOrchestrator executes this pipeline for every workflow:

```
1. Analyze scenario via LLM    → Design agent team (names, roles, dependencies)
2. Resolve dependencies        → Build DAG execution order
3. Create agents               → Instantiate via AgentFactory
4. Retrieve memory context     → Semantic search in ChromaDB
5. Execute agents              → Parallel DAG execution with message passing
6. Multi-agent dialogues       → Agents coordinate and negotiate
7. Feedback evaluation         → Evaluate performance metrics
8. CTDE training               → Update shared policies
9. Save execution trace        → Store in vector DB for future learning
```

---

## 🔨 Tool Execution Layer

Tools are injected **after each agent completes** via the `event_callback` in `orchestrator_service.py`. The core engine is never modified — tools run as a post-processing step.

### LLM-Assigned Tool Architecture

The LLM explicitly assigns tools to agents during the design phase via the `"tool"` field. No keyword guessing is needed — the system prompt includes a full tool catalog, and the LLM returns the exact tool name for each agent.

**Flow:**
```
User prompt → LLM sees tool catalog → Designs agents WITH tool assignments → Backend reads tool directly → Always correct
```

### Available Tools

| Tool Name | What It Does |
|-----------|--------------|
| `csv_export_tool` | Reads CSV/Excel, performs statistical analysis, generates Excel output |
| `report_tool` | Generates structured summary report from all agent results |
| `email_reader_tool` | Reads/searches inbox emails via IMAP |
| `email_tool` | Sends emails via SMTP |
| `slack_tool` | Posts messages to Slack channels |
| `zoom_tool` | Creates Zoom video meetings |
| `calendar_tool` | Schedules meetings and manages calendar |
| `sql_tool` | Runs read-only SQL queries against a database |
| `null` | LLM reasoning only (no external tool) |

### Tool Result Forwarding

Tool outputs from earlier agents are passed to downstream agents via `previous_tool_results`, enabling the report tool to include actual CSV analysis data (rows, columns, statistics) rather than just LLM-generated text.

---

## 🗄️ Database Schema

PostgreSQL with 9 core tables:

| Table | Purpose |
|-------|---------|
| `users` | User accounts (email, hashed password, role) |
| `sessions` | JWT session tracking |
| `workflows` | Workflow runs (input, status, timestamps) |
| `agents` | Agents created per workflow |
| `logs` | Execution log entries |
| `outputs` | Final workflow output JSON |
| `files` | Uploaded + generated files |
| `workflow_files` | File ↔ workflow associations |
| `meetings` | Scheduled meetings |

---

## 🚀 Running Locally

### Prerequisites

- Python 3.9+
- PostgreSQL (or Supabase account)
- Groq API key

### Setup

```bash
# 1. Clone the repo
cd autoops-ai

# 2. Install dependencies
pip install -r backend/requirements.txt

# 3. Configure environment
cp .env.example .env
# Edit .env with your DATABASE_URL, GROQ_API_KEY, JWT_SECRET, etc.

# 4. Run database migrations
# Execute backend/migrations/001_initial_schema.sql in your PostgreSQL

# 5. Start the server
cd backend
python -m uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
```

### Docker

```bash
docker-compose up --build
```

Open [http://localhost:8000](http://localhost:8000) in your browser.

---

## 🎨 Frontend Pages

| Page | URL | Features |
|------|-----|----------|
| **Login/Signup** | `/` | Email + password auth, role selection |
| **Dashboard** | `/dashboard.html` | Stats cards, recent workflows, quick actions |
| **Run Workflow** | `/workflow.html` | Text input, file upload, SSE live logs, DAG visualization, agent cards |
| **History** | `/history.html` | Past workflow table with status badges |
| **Files** | `/files.html` | Upload, list, delete files |
| **Schedule** | `/schedule.html` | Meeting CRUD |
| **Settings** | `/settings.html` | Profile management |

---

## 📝 Changelog

### Session 3 — 2026-04-15 (LLM-Assigned Tool Architecture)

**Architecture Change:**
- ✅ Removed fragile keyword-based `_map_agent_to_tool()` from `orchestrator_service.py` (50 lines deleted)
- ✅ Removed duplicate `map_agent_to_tool()` from `tool_dispatcher.py` (54 lines deleted)
- ✅ Tool assignments now come exclusively from LLM via `"tool"` field in agent configs
- ✅ LLM system prompt includes full tool catalog with usage rules
- ✅ `agents_designed` event handler reads `"tool"` directly from LLM response
- ✅ `agent_completed` handler reads tool from `agent_tool_map` (no fallback)
- ✅ Added logging for tool assignments at design time and execution time

**Why:** The old keyword-matching approach broke whenever the LLM chose creative agent names (e.g., "Data Examiner", "Information Inspector"). The new approach mirrors how CrewAI/AutoGen work — the LLM knows about tools and assigns them deterministically.

### Session 2 — 2026-04-15 (Tool Layer Integration)

**Bugs Found & Fixed:**
- ✅ Fixed Supabase DB connection (was using pooler endpoint, switched to direct)
- ✅ Fixed ChromaDB version conflict (downgraded from 1.2.0 → 0.5.23, cleared corrupted storage)
- ✅ Fixed `tokenizers` version conflict (chromadb vs transformers)
- ✅ Fixed `email_tool.py` — undefined `is_html` variable (line 73)
- ✅ Fixed tool mapping order — "SQL Database Query Agent" was mapping to `csv_tool` instead of `sql_tool`
- ✅ Fixed tool mapping keywords — agents named "Data Examiner" by LLM weren't matching (added examiner, reviewer, inspector, csv, compiler)
- ✅ Installed missing `asyncpg` and `openpyxl` packages

**New Features:**
- ✅ Created `csv_export_tool.py` — reads CSV, runs full analysis, generates Excel output file with 5 sheets (Summary, Column Analysis, Correlations, Distributions, Source Data)
- ✅ Created `report_tool.py` — generates structured report with actual CSV analysis data, numeric highlights table, output file info
- ✅ Added `tool_results_store` in `orchestrator_service.py` — passes tool outputs from earlier agents to downstream agents
- ✅ Added encoding fallback in `csv_tool.py` — tries utf-8 → latin-1 → cp1252 → iso-8859-1 → utf-16
- ✅ Refined agent→tool mapping — generic data roles (Collector, Preprocessor, Sanitizer) no longer trigger tools (LLM reasoning only)

**Verified Working:**
- ✅ All 20 FastAPI routes register
- ✅ Database connection (Supabase PostgreSQL 17.6)
- ✅ All 9 DB tables present with existing data
- ✅ bcrypt password hashing + JWT auth
- ✅ MetaOrchestrator full initialization (LLM, Agents, Memory, CTDE, Dialogues)
- ✅ ChromaDB vector store (0 entries, fresh start)
- ✅ SSE streaming pipeline (queue → EventSource)
- ✅ Full workflow execution end-to-end
- ✅ Frontend served correctly (all 7 pages)

### Session 1 — 2026-04-14 (Initial Build)

- Built FastAPI backend with full routing
- Implemented JWT auth system (signup, login, session management)
- Created PostgreSQL schema (9 tables)
- Built orchestrator_service.py (core engine adapter)
- Built tool_dispatcher.py with 7 initial tools
- Created full frontend (7 pages) with glassmorphism design
- Set up Docker + docker-compose deployment config
- Integrated ODI-based-multi-agent-Framework as read-only dependency

---

## ⚠️ Known Issues

| Issue | Severity | Status |
|-------|----------|--------|
| `asyncio.new_event_loop()` in calendar/sql/email tools crashes when called from async context | 🟡 Medium | Pending |
| UUID type handling in `workflow_service.py` (str vs UUID for asyncpg) | 🟡 Low | Pending |
| Core engine `.env` has different Groq API key than backend `.env` | 🟢 Info | Noted |

---

## 👥 Team

- **Aditya Pratap Singh** — Lead Developer
- **Priyanshu** — Core Engine

---

## 📄 License

Private / Proprietary


python -m uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
