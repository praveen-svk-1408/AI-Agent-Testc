# AI Agent Test Platform

A multi-agent LLM-powered platform that converts natural-language test descriptions into executable **Playwright + TypeScript** test suites. Describe what you want to test in plain English, and the platform generates, manages, and runs browser tests for you.

## Architecture

```
┌──────────────────┐        ┌──────────────────┐        ┌──────────────┐
│   Next.js 16     │  REST  │   FastAPI         │        │  PostgreSQL  │
│   (TypeScript)   │◄──────►│   (Python 3.13)   │◄──────►│  18          │
│   Port 3000      │   WS   │   Port 8000       │        │  Port 5432   │
└──────────────────┘        └──────────────────┘        └──────────────┘
     Frontend                   Backend / Agents              Database
```

| Layer    | Stack                                                        |
| -------- | ------------------------------------------------------------ |
| Frontend | Next.js 16, React 19, TypeScript, Tailwind CSS, App Router   |
| Backend  | FastAPI, SQLAlchemy 2.0 (async), Pydantic v2, Alembic        |
| Database | PostgreSQL 18                                                |
| Realtime | WebSocket (live run progress, agent status)                  |

## Project Structure

```
├── backend/
│   ├── app/
│   │   ├── main.py            # FastAPI app, CORS, routers
│   │   ├── config.py          # Pydantic Settings
│   │   ├── database.py        # Async SQLAlchemy engine & session
│   │   ├── models/            # ORM models (TestSuite, TestCase, TestStep, TestRun, Artifact)
│   │   ├── schemas/           # Pydantic request/response DTOs
│   │   ├── routers/           # API endpoints (suites, cases, runs, generation)
│   │   ├── services/          # Business logic (Phase 2+)
│   │   ├── agents/            # LLM agents (Phase 2+)
│   │   └── utils/
│   ├── migrations/            # Alembic migrations
│   ├── requirements.txt
│   └── .env
├── frontend/
│   ├── src/
│   │   ├── app/               # Next.js App Router pages & layout
│   │   ├── components/        # Shared UI components
│   │   ├── hooks/             # Custom React hooks
│   │   ├── services/          # API client & WebSocket
│   │   ├── lib/               # Utilities & constants
│   │   └── types/             # TypeScript domain types
│   ├── .env.local
│   └── package.json
└── plan.md                    # Full project roadmap
```

## Prerequisites

- **Python 3.13+**
- **Node.js 20+** and npm
- **PostgreSQL 18** installed and running locally

## Getting Started

### 1. Database Setup

Open a terminal and create the database:

```bash
psql -U postgres
```

```sql
CREATE DATABASE ai_agent_test;
\q
```

### 2. Backend Setup

```bash
cd backend

# Create and activate virtual environment
python -m venv venv
venv\Scripts\activate        # Windows
# source venv/bin/activate   # macOS / Linux

# Install dependencies
pip install -r requirements.txt

# Configure environment
# Edit .env and set your PostgreSQL password:
#   DATABASE_URL=postgresql+asyncpg://postgres:YOUR_PASSWORD@localhost:5432/ai_agent_test
#   SYNC_DATABASE_URL=postgresql+psycopg2://postgres:YOUR_PASSWORD@localhost:5432/ai_agent_test

# Run database migrations
alembic upgrade head

# Start the backend server
uvicorn app.main:app --reload --host 127.0.0.1 --port 8000
```

The API will be available at **http://localhost:8000**. Health check: `GET /health`

### 3. Frontend Setup

```bash
cd frontend

# Install dependencies
npm install

# Start the dev server
npm run dev
```

The frontend will be available at **http://localhost:3000**.

## API Endpoints

| Method | Endpoint                              | Description                      |
| ------ | ------------------------------------- | -------------------------------- |
| GET    | `/health`                             | Health check                     |
| POST   | `/test-suites`                        | Create a test suite              |
| GET    | `/test-suites`                        | List all test suites             |
| GET    | `/test-suites/{id}`                   | Get suite with test cases        |
| PATCH  | `/test-suites/{id}`                   | Update a test suite              |
| DELETE | `/test-suites/{id}`                   | Delete a test suite              |
| POST   | `/test-suites/{id}/test-cases`        | Create a test case in a suite    |
| GET    | `/test-suites/{id}/test-cases`        | List test cases for a suite      |
| GET    | `/test-cases/{id}`                    | Get test case with steps         |
| DELETE | `/test-cases/{id}`                    | Delete a test case               |
| POST   | `/test-cases/{id}/generate`           | Trigger AI test step generation  |
| POST   | `/test-runs`                          | Create and start a test run      |
| GET    | `/test-runs`                          | List test runs (filter by case)  |
| GET    | `/test-runs/{id}`                     | Get run details with artifacts   |

## Frontend Pages

| Route                              | Description                                          |
| ---------------------------------- | ---------------------------------------------------- |
| `/`                                | Dashboard — test suite grid, create/delete suites    |
| `/suites/[id]`                     | Suite detail — test cases list, generate & run        |
| `/suites/[id]/cases/[caseId]`      | Case detail — generated steps, run on browser         |
| `/runs`                            | All test runs table                                   |
| `/runs/[id]`                       | Run detail — status, errors, artifacts                |

## Development

```bash
# Backend — auto-reloads on file changes
cd backend
venv\Scripts\activate
uvicorn app.main:app --reload

# Frontend — auto-reloads on file changes
cd frontend
npm run dev

# Build frontend for production
npm run build
npm start
```

## Roadmap

See [plan.md](plan.md) for the full implementation roadmap.

- **Phase 1** ✅ Foundation — DB schema, API, frontend scaffold
- **Phase 2** — LLM Agents (LangChain/LangGraph, page crawler, test generator)
- **Phase 3** — Playwright execution engine, artifact capture
- **Phase 4** — WebSocket live updates, headed browser viewing
- **Phase 5** — Polish, error recovery, re-generation workflows
- **Phase 6** — Deployment, CI/CD, monitoring