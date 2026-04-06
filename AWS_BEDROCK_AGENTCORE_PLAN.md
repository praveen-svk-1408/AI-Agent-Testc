# AWS Bedrock & AgentCore Integration Plan

## Executive Summary

This document outlines a two-phase enterprise integration plan for AWS Bedrock and AgentCore into the AI Agent Test Platform. **Phase 1** (Bedrock as LLM provider) is complete and provides immediate enterprise value. **Phase 2** (AgentCore Runtime deployment) is implemented — the agent project and backend integration layer are ready for deployment.

---

### Phase 2 Implementation Summary

The following files were created/modified to implement AgentCore Runtime deployment:

**New — AgentCore Agent Project (`agentcore_agent/`)**

| File | Purpose |
|------|---------|
| `agentcore/agentcore.json` | Agent configuration (name, framework, entrypoint) |
| `app/TestGenerator/main.py` | `BedrockAgentCoreApp` entrypoint wrapping the LangGraph pipeline |
| `app/TestGenerator/pyproject.toml` | Python dependencies (bedrock-agentcore, langchain, langgraph, boto3) |
| `app/TestGenerator/config.py` | Simplified settings (LLM-only, no DB/filesystem/web server) |
| `app/TestGenerator/workflow.py` | Modified workflow: no crawler, no file I/O, accepts pre-crawled snapshots |
| `app/TestGenerator/agents/*.py` | All 7 agent modules with local imports |
| `app/TestGenerator/schemas/agent.py` | Pydantic models for agent I/O |
| `app/TestGenerator/utils/llm_factory.py` | LLM factory (Bedrock/Groq/Ollama) |
| `app/TestGenerator/utils/output_parser.py` | JSON/Pydantic output parser |

**Modified — Backend Integration Layer**

| File | Change |
|------|--------|
| `backend/app/config.py` | Added `agentcore_enabled` and `agentcore_endpoint` settings |
| `backend/app/services/test_generation.py` | Added conditional: if `agentcore_enabled` → crawl locally, POST to AgentCore agent |
| `backend/app/services/agentcore_client.py` | New HTTP client for invoking the deployed AgentCore agent |

**To activate**: Set `AGENTCORE_ENABLED=true` and `AGENTCORE_ENDPOINT=<url>` in `.env`.

---

## Phase 1: AWS Bedrock as LLM Provider ✅ COMPLETE

### What Was Done

Added AWS Bedrock as a third LLM provider option alongside existing Groq (cloud) and Ollama (local). The centralized `get_llm()` factory pattern meant only **3 files** needed modification.

### Files Changed

| File | Change |
|------|--------|
| `backend/requirements.txt` | Added `langchain-aws>=0.2.0` and `boto3>=1.35.0` |
| `backend/app/config.py` | Added `aws_region`, `bedrock_model_id` settings; updated `llm_provider` to accept `"bedrock"` |
| `backend/app/utils/llm_factory.py` | Added `"bedrock"` branch returning `ChatBedrockConverse` from `langchain-aws` |
| `README.md` | Updated prerequisites, architecture table, and `.env` template with Bedrock provider |

### AWS Account Setup Steps (First Time)

Since there is no existing AWS account, follow these steps:

#### Step 1: Create AWS Account
1. Go to [aws.amazon.com](https://aws.amazon.com/) and click "Create an AWS Account"
2. Provide email, phone number, and a payment method (free tier available)
3. Complete identity verification

#### Step 2: Create IAM User
1. Sign in to **AWS Console** → search for **IAM**
2. Go to **Users** → **Create User**
3. Name: `ai-agent-test-dev` (or your preference)
4. Attach policy: **`AmazonBedrockFullAccess`**
5. Go to **Security Credentials** → **Create Access Key** → choose "CLI"
6. **Save** the Access Key ID and Secret Access Key (shown only once)

#### Step 3: Install & Configure AWS CLI
1. Download AWS CLI v2 from [aws.amazon.com/cli](https://aws.amazon.com/cli/) (Windows MSI installer)
2. Open PowerShell and run:
   ```powershell
   aws configure
   ```
3. Enter:
   - **Access Key ID**: (from Step 2)
   - **Secret Access Key**: (from Step 2)
   - **Default region**: `us-east-1` (or `us-west-2`)
   - **Output format**: `json`

#### Step 4: Enable Model Access in Bedrock
1. AWS Console → search **Amazon Bedrock**
2. Left sidebar → **Model Access**
3. Click **Manage model access**
4. Check **Meta Llama 3.3 70B Instruct**
5. Click **Submit** — wait for "Access granted" status

#### Step 5: Verify Setup
```powershell
aws bedrock list-foundation-models --region us-east-1 --query "modelSummaries[?contains(modelId, 'llama')]" --output table
```

#### Step 6: Install Dependencies & Configure
```bash
cd backend
pip install -r requirements.txt
```

Update `.env`:
```env
LLM_PROVIDER=bedrock
AWS_REGION=us-east-1
BEDROCK_MODEL_ID=us.meta.llama3-3-70b-instruct-v1:0
```

AWS credentials are auto-discovered from `aws configure` — no keys in `.env` needed.

#### Step 7: Test
Start backend, create a test case, trigger generation. All 7 agents will use Bedrock automatically via the `get_llm()` factory.

### Architecture After Phase 1

```
┌──────────────┐     ┌──────────────┐     ┌──────────────┐
│  React       │REST │  FastAPI     │     │  PostgreSQL  │
│  Frontend    │────►│  Backend     │────►│  Database     │
│  Port 5173   │ WS  │  Port 8000   │     │  Port 5432   │
└──────────────┘     └──────┬───────┘     └──────────────┘
                            │
                   ┌────────┴────────┐
                   │  get_llm()      │
                   │  Factory        │
                   └──┬──────┬───┬───┘
                      │      │   │
                ┌─────┘  ┌───┘   └────┐
                ▼        ▼            ▼
          ┌─────────┐ ┌───────┐ ┌──────────┐
          │ Bedrock │ │ Groq  │ │ Ollama   │
          │ (AWS)   │ │(Cloud)│ │ (Local)  │
          └─────────┘ └───────┘ └──────────┘
```

No agent code changes — `ChatBedrockConverse` is a drop-in replacement implementing the same `BaseChatModel` interface.

---

## Phase 2: AgentCore Runtime Deployment ✅ IMPLEMENTED

### Why This Is a Major Change

The current application is a **full-stack monolith** with deep local dependencies. AgentCore Runtime is designed for **stateless agent handlers**. Moving the pipeline to AgentCore means splitting the application into two independently deployed services.

### Current Architecture Dependencies vs AgentCore Runtime

| Current App Feature | AgentCore Runtime Capability | Gap |
|---|---|---|
| FastAPI REST API (20+ endpoints) | Single handler entrypoint | AgentCore does NOT replace the web server |
| PostgreSQL database (async) | No database | Must keep own DB for suites, cases, runs, artifacts |
| Local filesystem (artifacts, .spec.ts) | Ephemeral storage (wiped per session) | Generated files can't persist in Runtime |
| Playwright subprocesses (crawling + execution) | Has "Browser Tool" for agent browsing | Not designed for `npx playwright test` subprocesses |
| WebSocket real-time updates | Supports streaming responses | Different protocol; frontend client rewrite needed |
| Background tasks (`asyncio.create_task`) | Request → response (sync or streaming) | No fire-and-forget background processing |
| In-memory progress tracking | Stateless per session | `_generation_progress` dict doesn't persist |

### Recommended Architecture: Hybrid Split

Extract ONLY the LangGraph AI pipeline into AgentCore Runtime. Keep everything else in FastAPI.

```
┌──────────────┐     ┌──────────────────────┐     ┌───────────────────────────┐
│  React       │REST │  FastAPI Backend      │HTTP │  AgentCore Runtime        │
│  Frontend    │────►│  (Platform Layer)     │────►│  (AI Pipeline Only)       │
│              │ WS  │                       │     │                           │
└──────────────┘     │  Owns:                │     │  1. Orchestrator          │
                     │  ✓ REST API           │     │  2. DOM Analyst           │
                     │  ✓ PostgreSQL DB      │     │  3. Test Generator        │
                     │  ✓ WebSocket server   │     │  4. Test Case Reviewer    │
                     │  ✓ Playwright crawl   │     │  5. Step Generator        │
                     │  ✓ Playwright execute  │     │  6. Step Reviewer         │
                     │  ✓ Artifact storage   │     │  7. Code Generator        │
                     │  ✓ File management    │     │                           │
                     └──────────────────────┘     │  Uses: Bedrock LLM        │
                                                  │  Input: snapshots + desc  │
                                                  │  Output: steps + code     │
                                                  └───────────────────────────┘
```

### Implementation Steps

#### Step 1: Create AgentCore Agent Project

```powershell
npm install -g @aws/agentcore
agentcore create
# Select: LangGraph framework, Python language
cd ai-test-generator-agent
```

This scaffolds:
```
ai-test-generator-agent/
├── agentcore/
│   ├── agentcore.json       # Agent configuration
│   ├── aws-targets.json     # Deployment targets
│   └── .env.local           # API keys (gitignored)
├── app/
│   └── TestGenerator/
│       ├── main.py          # Agent entrypoint (BedrockAgentCoreApp)
│       ├── pyproject.toml   # Python dependencies
│       └── model/           # Model configuration
```

#### Step 2: Extract LangGraph Workflow into Agent Entrypoint

Create `main.py` entrypoint:

```python
from bedrock_agentcore import BedrockAgentCoreApp
from workflow import run_workflow  # extracted LangGraph pipeline

app = BedrockAgentCoreApp()

@app.entrypoint
async def handler(request):
    """
    Input: {
        title, description, base_url, test_type, app_description,
        page_snapshots: [{url, page_title, elements, forms, accessibility_tree}],
        login_url?, login_username?, login_password?
    }
    Output: {
        steps: [{order, action, selector, value, expected_result, description}],
        code_content: "// TypeScript .spec.ts file content",
        code_file_name: "test_name.spec.ts",
        test_cases: [{tc_id, title, category, priority, test_steps, expected_results}]
    }
    """
    result = await run_workflow(
        title=request["title"],
        description=request["description"],
        base_url=request["base_url"],
        test_type=request.get("test_type", "functional"),
        app_description=request.get("app_description", ""),
        page_snapshots=request.get("page_snapshots", []),
        login_url=request.get("login_url"),
        login_username=request.get("login_username"),
        login_password=request.get("login_password"),
    )
    yield result

app.run()
```

#### Step 3: Copy Agent Modules

Files to copy from `backend/app/agents/` into the AgentCore project:

| Source File | Purpose |
|-------------|---------|
| `requirement_analyzer.py` | Orchestrator — decomposes NL into goals/pages/assertions |
| `dom_analyst.py` | Analyzes DOM snapshots for semantic groups & selectors |
| `test_generator.py` | Generates IEEE 829 test cases |
| `test_case_reviewer.py` | Validates test case coverage (Loop A) |
| `step_generator.py` | Converts test cases to Playwright action steps |
| `reverifier.py` | Validates step executability against real DOM (Loop B) |
| `code_generator.py` | Produces final .spec.ts TypeScript code |
| `workflow.py` | LangGraph state machine orchestrating all 7 agents |

Also copy:
| Source File | Purpose |
|-------------|---------|
| `utils/llm_factory.py` | LLM factory (will use Bedrock directly in AgentCore) |
| `utils/robust_parser.py` | JSON/Pydantic output parser |
| `schemas/agent.py` | All Pydantic models for agent I/O |

#### Step 4: Remove Crawler from Workflow

The LangGraph workflow currently has a `load_snapshots_node` that calls the Playwright crawler. This **cannot run inside AgentCore Runtime** (no browser binary available).

**Change**: Modify the workflow to accept pre-crawled `page_snapshots` as input instead of crawling live. The FastAPI backend will:
1. Crawl pages BEFORE calling the agent (already supported via `POST /test-suites/{id}/crawl`)
2. Pass DOM snapshots as part of the request payload to AgentCore

```python
# In workflow.py — change load_snapshots_node:
def load_snapshots_node(state: WorkflowState) -> dict:
    # OLD: crawl pages live
    # NEW: snapshots already provided in state input
    if state.get("page_snapshots"):
        return {"status": "snapshots_loaded"}
    else:
        raise ValueError("page_snapshots must be provided as input")
```

#### Step 5: Remove All DB Operations from Workflow

Currently `test_generation.py` orchestrates both the workflow AND database persistence. Split this:

- **AgentCore agent**: Pure computation — LLM calls only, returns structured data
- **FastAPI backend**: Handles all DB reads/writes before and after calling the agent

```python
# In FastAPI test_generation.py — change generate_test_case_steps():
async def generate_test_case_steps(case_id, db, progress_callback):
    # 1. DB Read: fetch case + suite
    case = await get_test_case(case_id, db)
    suite = await get_test_suite(case.suite_id, db)
    
    # 2. Load pre-crawled snapshots (or trigger crawl)
    snapshots = await load_cached_snapshots(suite.id)
    
    # 3. Call AgentCore Runtime agent (HTTP)
    result = await invoke_agentcore_agent({
        "title": case.title,
        "description": case.description,
        "base_url": suite.base_url,
        "test_type": case.test_type,
        "page_snapshots": snapshots,
        "login_url": suite.login_url,
        "login_username": suite.login_username,
        "login_password": suite.login_password,
    })
    
    # 4. DB Write: persist steps, code, update status
    await persist_generated_steps(case_id, result["steps"], db)
    await write_spec_file(suite.id, result["code_file_name"], result["code_content"])
    await update_case_status(case_id, "generated", db)
```

#### Step 6: Deploy & Test

```powershell
# Local testing
agentcore dev

# Deploy to AWS
agentcore deploy

# Test the deployed agent
agentcore invoke

# Optional: add enterprise features
agentcore add memory           # Cross-session learning
agentcore add evaluator        # LLM-as-a-Judge quality monitoring
agentcore add online-eval      # Continuous evaluation
agentcore deploy               # Sync changes
```

### Files Changed Summary (Phase 2)

| Action | Files | Impact |
|--------|-------|--------|
| **New** | `agentcore_agent/app/TestGenerator/main.py` | AgentCore entrypoint handler |
| **Copy + Modify** | 7 agent files + workflow.py + schemas | Extracted into AgentCore package |
| **Modify** | `backend/app/services/test_generation.py` | Replace local `run_workflow()` with HTTP call to AgentCore |
| **Modify** | `backend/app/agents/workflow.py` | Remove crawler node, accept pre-crawled snapshots |
| **New** | `backend/app/services/agentcore_client.py` | HTTP client to invoke deployed AgentCore agent |
| **New** | `agentcore_agent/agentcore/agentcore.json` | Agent configuration |
| **No Change** | All routers, models, frontend, test execution, artifact management | Platform layer unchanged |

### AgentCore Services to Adopt

| Service | Purpose | Priority |
|---------|---------|----------|
| **Runtime** | Serverless deployment, auto-scaling, session isolation | Required |
| **Memory** | Remember patterns across test generations (learn from past runs) | Nice-to-have |
| **Gateway** | Expose the agent as an MCP-compatible tool | Nice-to-have |
| **Observability** | OpenTelemetry tracing, CloudWatch dashboards | Recommended |
| **Evaluations** | LLM-as-a-Judge to monitor test generation quality | Recommended |
| **Policy** | Cedar-based access control for multi-tenant deployments | Future |
| **Identity** | Secure credentials across AWS + third-party services | Future |

### Cost Considerations

| Component | Pricing Model | Estimate per Test Case |
|-----------|--------------|----------------------|
| AgentCore Runtime | Pay per compute-second | ~60-120s compute ($0.01-0.05) |
| Bedrock LLM (Llama 3.3 70B) | Input/output tokens | ~$0.02-0.10 per generation |
| Data transfer | Standard AWS rates | Negligible |

### Key Risks & Mitigations

| Risk | Impact | Mitigation |
|------|--------|------------|
| Cold start latency | First invocation slower (5-15s) | Keep minimum instances warm; acceptable for background generation |
| Network overhead | Adds ~1-2s per agent call | Batch all 7 agents in single request; use streaming for progress |
| Snapshot payload size | DOM snapshots can be large (1-5MB) | Compress snapshots; limit crawl depth; trim irrelevant elements |
| No local Playwright in Runtime | Can't crawl or execute tests inside agent | Crawl in FastAPI before calling agent; test execution stays local |
| LLM provider lock-in | Agent tied to Bedrock | LLM factory pattern still works; can swap providers |

---

## Decision Matrix

| Criteria | Phase 1 Only (Current) | Phase 1 + Phase 2 |
|----------|----------------------|-------------------|
| Enterprise LLM access | ✅ AWS Bedrock via IAM | ✅ AWS Bedrock native |
| Infrastructure management | Self-hosted FastAPI | Hybrid: self-hosted + managed Runtime |
| Auto-scaling | Manual (run more instances) | Automatic (AgentCore scales agents) |
| Session isolation | None (shared process) | Full (per-invocation isolation) |
| Observability | Custom logging | Built-in OpenTelemetry + CloudWatch |
| Cost | LLM API costs only | LLM + Runtime compute costs |
| Implementation effort | ✅ Done (3 files changed) | ~2-3 weeks of development |
| Risk | Low | Medium (architecture split) |

### Recommendation

**Start with Phase 1 (already complete).** Phase 2 should be triggered when:
- Concurrent test generation by multiple users becomes a bottleneck
- Security/compliance requires session isolation between tenants
- Operations team needs built-in observability dashboards
- Organization mandates all AI workloads run on managed AWS infrastructure

---

## References

- [AgentCore CLI](https://github.com/aws/agentcore-cli) — Create, develop, deploy agents
- [AgentCore Python SDK](https://github.com/aws/bedrock-agentcore-sdk-python) — `BedrockAgentCoreApp`, `serve_ag_ui`, `serve_a2a`
- [AgentCore Samples](https://github.com/awslabs/agentcore-samples) — Tutorials and examples
- [AgentCore Documentation](https://docs.aws.amazon.com/bedrock-agentcore/) — Official developer guide
- [LangChain AWS Integration](https://docs.langchain.com/oss/python/integrations/chat/bedrock) — `ChatBedrockConverse` reference
- [AgentCore Pricing](https://aws.amazon.com/bedrock/agentcore/pricing/)
