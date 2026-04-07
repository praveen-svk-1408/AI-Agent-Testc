# AWS Bedrock AgentCore — Deployment Guide

Complete step-by-step guide to deploy the AITestAgent to Amazon Bedrock AgentCore Runtime.

---

## Table of Contents

1. [Prerequisites](#1-prerequisites)
2. [AWS Account Setup](#2-aws-account-setup)
3. [Enable Bedrock Model Access](#3-enable-bedrock-model-access)
4. [Install the AgentCore CLI](#4-install-the-agentcore-cli)
5. [Configure AWS Credentials](#5-configure-aws-credentials)
6. [Configure Deployment Targets](#6-configure-deployment-targets)
7. [Install Agent Dependencies Locally](#7-install-agent-dependencies-locally)
8. [Local Development & Testing](#8-local-development--testing)
9. [Deploy to AWS](#9-deploy-to-aws)
10. [Invoke the Deployed Agent](#10-invoke-the-deployed-agent)
11. [Connect Backend to Deployed Agent](#11-connect-backend-to-deployed-agent)
12. [Add AgentCore Capabilities (Optional)](#12-add-agentcore-capabilities-optional)
13. [Monitoring & Observability](#13-monitoring--observability)
14. [Troubleshooting](#14-troubleshooting)

---

## 1. Prerequisites

Install the following on your development machine before you start:

| Tool          | Version   | Install                                                      |
|---------------|-----------|--------------------------------------------------------------|
| Node.js       | >= 20.x   | https://nodejs.org/                                          |
| Python        | >= 3.11   | https://www.python.org/downloads/                            |
| uv            | latest    | `pip install uv` or https://docs.astral.sh/uv/getting-started/installation/ |
| AWS CLI v2    | latest    | https://docs.aws.amazon.com/cli/latest/userguide/getting-started-install.html |
| Git           | latest    | https://git-scm.com/                                         |

> **Why is `uv` required?** The AgentCore CLI uses `uv` internally to resolve dependencies and package
> Python agents during `agentcore dev` and `agentcore deploy`. You can use `python -m venv` + `pip`
> for your own local testing (see Section 7), but `uv` must be installed for the CLI to work.

Verify installations:

```powershell
node --version          # v20.x or later
python --version        # 3.11+
uv --version            # any
aws --version           # aws-cli/2.x
```

> **Project Structure:** The AgentCore CLI expects `app/` and `agentcore/` as siblings at the project root:
> ```
> AI-Agent-Testc/          ← project root (run all agentcore CLI commands here)
>   agentcore/             ← CLI config (agentcore.json, aws-targets.json)
>   app/AITestAgent/       ← agent source code
>   backend/               ← FastAPI backend
>   frontend/              ← React frontend
> ```

---

## 2. AWS Account Setup

### 2.1 Create an IAM User or Role

You need an IAM identity with the following **managed policies** attached:

| Policy Name                     | Purpose                                    |
|---------------------------------|--------------------------------------------|
| `BedrockAgentCoreFullAccess`    | Deploy/manage AgentCore agents & runtime   |
| `AmazonBedrockFullAccess`       | Invoke Bedrock models (Claude Haiku)       |

**Option A — IAM User (for local dev):**

1. Go to **AWS Console → IAM → Users → Create user**
2. Name: `agentcore-deployer`
3. Attach policies: `BedrockAgentCoreFullAccess`, `AmazonBedrockFullAccess`
4. Create an **Access Key** (CLI access) — save the Access Key ID and Secret

**Option B — IAM Role (for CI/CD or EC2):**

1. Create a role with the same policies
2. Use `aws sts assume-role` or instance profile for credentials

### 2.2 Additional Permissions (if using custom VPC or secrets)

If your agent needs VPC access or Secrets Manager for API keys, also attach:

- `AWSLambdaVPCAccessExecutionRole` (VPC networking)
- `SecretsManagerReadWrite` (for identity/secrets features)

---

## 3. Enable Bedrock Model Access

The AITestAgent uses **Claude 3 Haiku** (`us.anthropic.claude-3-haiku-20240307-v1:0`).

1. Open **AWS Console → Amazon Bedrock → Model access** (region: `ap-south-1`)
2. Click **Manage model access**
3. Find **Anthropic → Claude 3 Haiku** and check the box
4. Click **Save changes**
5. Wait for status to show **Access granted**

> **Note:** If you want to use a different model (e.g., Claude 3.5 Sonnet for better code generation),
> enable that model too and set the `BEDROCK_MODEL_ID` environment variable when deploying.

---

## 4. Install the AgentCore CLI

```powershell
npm install -g @aws/agentcore
```

Verify:

```powershell
agentcore --version
```

> **Upgrading from Starter Toolkit?** If you previously had `bedrock-agentcore-starter-toolkit` installed, uninstall it first:
> ```powershell
> pip uninstall bedrock-agentcore-starter-toolkit
> # or
> pipx uninstall bedrock-agentcore-starter-toolkit
> ```

---

## 5. Configure AWS Credentials

### Option A — AWS CLI Profile (recommended)

```powershell
aws configure
```

Enter:
- **AWS Access Key ID**: (from Step 2.1)
- **AWS Secret Access Key**: (from Step 2.1)
- **Default region**: `ap-south-1`
- **Output format**: `json`

### Option B — Environment Variables

```powershell
$env:AWS_ACCESS_KEY_ID = "AKIA..."
$env:AWS_SECRET_ACCESS_KEY = "wJalr..."
$env:AWS_DEFAULT_REGION = "ap-south-1"
```

### Option C — AWS SSO

```powershell
aws configure sso
aws sso login --profile your-profile
$env:AWS_PROFILE = "your-profile"
```

Verify access:

```powershell
aws sts get-caller-identity
aws bedrock list-foundation-models --region ap-south-1 --query "modelSummaries[?contains(modelId,'haiku')].[modelId]" --output table
```

---

## 6. Configure Deployment Targets

Edit `agentcore/aws-targets.json` with your AWS Account ID:

```json
[
  {
    "name": "default",
    "region": "ap-south-1",
    "account": "123456789012",
    "memorySizeMb": 2048,
    "timeoutSeconds": 900
  }
]
```

Replace `123456789012` with your actual AWS Account ID. You can find it with:

```powershell
aws sts get-caller-identity --query "Account" --output text
```

### Runtime Configuration Notes

| Setting            | Value  | Rationale                                                |
|--------------------|--------|----------------------------------------------------------|
| `memory_size_mb`   | 2048   | 7-agent pipeline needs headroom for concurrent processing |
| `timeout_seconds`  | 900    | Full pipeline (crawl + 7 agents + retries) can take 5-10 min |

---

## 7. Install Agent Dependencies Locally

### Option A — Using uv (recommended, matches CLI toolchain)

```powershell
cd app/AITestAgent
uv venv
.venv\Scripts\activate      # Windows
# source .venv/bin/activate  # Linux/Mac

uv pip install -e .
```

### Option B — Using python venv + pip

```powershell
cd app/AITestAgent
python -m venv .venv
.venv\Scripts\activate      # Windows
# source .venv/bin/activate  # Linux/Mac

pip install -e .
```

> **Note:** Either option works for local testing. The AgentCore CLI still requires `uv` to be
> installed on your system — it uses `uv` internally when packaging and deploying your agent.

This installs:
- `strands-agents` — Strands Agents SDK
- `strands-agents-tools` — Built-in tools (browser, code interpreter)
- `bedrock-agentcore` — AgentCore Runtime SDK
- `pydantic` — Schema validation

---

## 8. Local Development & Testing

### 8.1 Start the Local Dev Server

From the **project root** (not from the `agentcore/` subdirectory):

```powershell
agentcore dev
```

> **Important:** The AgentCore CLI must be run from the project root directory (where the `agentcore/` and `app/` folders are siblings). Running it from inside `agentcore/` will fail.

This starts a local invocation endpoint that mimics the AgentCore Runtime. The CLI watches for file changes.

### 8.2 Test with a Sample Invocation

Open a new terminal and invoke locally:

```powershell
agentcore invoke --prompt '{
  "title": "Login Test",
  "description": "Test that a user can log in with valid credentials Email: test@example.com Password: password123",
  "base_url": "http://localhost:3005",
  "test_type": "functional",
  "app_description": "Sample e-commerce application"
}'
```

### 8.3 Create an API Keys File (if needed)

If your agent uses any external API keys, create `agentcore/.env.local` (auto-gitignored):

```env
BEDROCK_MODEL_ID=us.anthropic.claude-3-haiku-20240307-v1:0
AWS_REGION=ap-south-1
```

---

## 9. Deploy to AWS

### 9.1 Deploy

From the project root:

```powershell
agentcore deploy
```

The CLI will:
1. Package your agent code
2. Provision a CDK stack (CloudFormation) in your AWS account
3. Create an AgentCore Runtime endpoint
4. Output the **Agent ARN** — save this!

Example output:
```
✓ Deploying AITestAgent...
✓ Stack created: AgentCoreStack-AITestAgent
✓ Agent ARN: arn:aws:bedrock-agentcore:us-east-1:123456789012:agent/AITestAgent
✓ Deployment complete!
```

### 9.2 Save the Agent ARN

Copy the Agent ARN from the deploy output. You'll need it to:
- Invoke the agent from your backend
- Configure the FastAPI integration

---

## 10. Invoke the Deployed Agent

### 10.1 Via AgentCore CLI

```powershell
agentcore invoke --prompt '{
  "title": "Login Test",
  "description": "Test user login with valid credentials and verify redirect to dashboard",
  "base_url": "https://myapp.example.com",
  "test_type": "e2e",
  "app_description": "E-commerce web application",
  "login_url": "/login",
  "login_username": "testuser@example.com",
  "login_password": "TestPass123"
}'
```

### 10.2 Via AWS CLI (boto3 / direct)

```powershell
aws bedrock-agentcore invoke-agent `
  --agent-id "AITestAgent" `
  --region ap-south-1 `
  --payload '{"title":"Login Test","description":"Test login flow","base_url":"https://myapp.example.com","test_type":"functional"}'
```

### 10.3 Via Python (boto3)

```python
import boto3, json

client = boto3.client("bedrock-agentcore", region_name="ap-south-1")

response = client.invoke_agent_runtime(
    agentRuntimeArn="arn:aws:bedrock-agentcore:ap-south-1:123456789012:agent/AITestAgent",
    payload=json.dumps({
        "title": "Login Test",
        "description": "Test user login",
        "base_url": "https://myapp.example.com",
        "test_type": "functional",
    }),
)

# Stream the response events
for event in response["body"]:
    chunk = json.loads(event["chunk"]["bytes"].decode())
    print(chunk)
```

---

## 11. Connect Backend to Deployed Agent

Once deployed, configure the FastAPI backend to invoke the AgentCore agent instead of the local LangGraph pipeline.

### 11.1 Update Environment Variables

Add these to your `backend/.env` file:

```env
# AgentCore Runtime Integration
AGENTCORE_ENABLED=true
AGENTCORE_AGENT_ARN=arn:aws:bedrock-agentcore:ap-south-1:123456789012:agent/AITestAgent
AGENTCORE_REGION=ap-south-1

# AWS Credentials (if not using IAM role / instance profile)
AWS_ACCESS_KEY_ID=AKIA...
AWS_SECRET_ACCESS_KEY=wJalr...
```

### 11.2 Install boto3

```powershell
cd backend
pip install -r requirements.txt   # boto3>=1.35.0 is already listed
```

### 11.3 How It Works

When `AGENTCORE_ENABLED=true`:
- `POST /test-cases/{id}/generate` calls `_invoke_agentcore()` in `backend/app/services/test_generation.py`
- The function uses boto3 to invoke the deployed AgentCore agent
- Progress events stream back via WebSocket to the frontend
- Results (test steps, generated code) are persisted to the database as before

When `AGENTCORE_ENABLED=false` (default):
- The existing LangGraph `run_workflow()` pipeline runs locally — no AWS dependency

### 11.4 Test the Integration

1. Start the backend: `cd backend && python start.py`
2. Start the frontend: `cd frontend && npm run dev`
3. Create a test suite → create a test case → click **Generate**
4. Check the WebSocket messages for AgentCore pipeline progress events

---

## 12. Add AgentCore Capabilities (Optional)

The AgentCore CLI supports adding features incrementally:

### Memory (persistent context across sessions)

```powershell
agentcore add memory
agentcore deploy
```

### Identity (secure API key management)

```powershell
agentcore add identity
agentcore deploy
```

### Evaluators (LLM-as-a-Judge quality monitoring)

```powershell
agentcore add evaluator
agentcore deploy
```

### Online Evaluation (continuous monitoring on live traffic)

```powershell
agentcore add online-eval
agentcore deploy
```

> Always run `agentcore deploy` after adding/removing capabilities.

---

## 13. Monitoring & Observability

### 13.1 CloudWatch Logs

AgentCore agents automatically emit logs to CloudWatch:

```powershell
aws logs describe-log-groups --log-group-name-prefix "/aws/bedrock-agentcore" --region ap-south-1
```

View recent logs:

```powershell
aws logs tail "/aws/bedrock-agentcore/AITestAgent" --follow --region ap-south-1
```

### 13.2 OpenTelemetry Tracing

AgentCore supports OpenTelemetry out of the box. Add observability:

```powershell
agentcore add observability
agentcore deploy
```

This enables distributed tracing across all 7 agents in the pipeline.

### 13.3 AWS Console

1. Go to **Amazon Bedrock → AgentCore → Agents** in the AWS Console
2. Click on **AITestAgent**
3. View: invocation history, latency metrics, error rates, trace details

---

## 14. Troubleshooting

### Common Issues

| Problem | Cause | Fix |
|---------|-------|-----|
| `agentcore deploy` fails with permissions error | Missing IAM policies | Attach `BedrockAgentCoreFullAccess` and `AmazonBedrockFullAccess` |
| `AccessDeniedException` on model invocation | Claude Haiku not enabled | Go to Bedrock Console → Model access → Enable Claude 3 Haiku |
| `ModuleNotFoundError: strands` | Dependencies not installed | Run `uv pip install -e .` in `app/AITestAgent/` |
| Timeout errors during pipeline execution | `timeout_seconds` too low | Increase to 900 in `aws-targets.json` |
| `account_id` empty error | Not configured in aws-targets.json | Run `aws sts get-caller-identity` and set the account_id |
| Backend returns 500 on generate | `AGENTCORE_AGENT_ARN` not set | Add the ARN from `agentcore deploy` output to `.env` |
| Agent invocation returns empty | Agent not fully deployed | Wait 1-2 min after deploy, then retry |

### Useful Commands

```powershell
# Check deployed agent status
agentcore invoke

# Redeploy after code changes
agentcore deploy

# View local dev logs
agentcore dev --verbose

# Destroy all deployed resources (CAUTION: irreversible)
agentcore destroy
```

### Getting the Agent ARN After Deployment

If you lost the ARN from the deploy output:

```powershell
# Check the deployed state file
cat agentcore/.cli/deployed-state.json

# Or list agents via AWS CLI
aws bedrock-agentcore list-agents --region ap-south-1
```

---

## Quick Reference — Full Deployment Sequence

```powershell
# 1. Install CLI
npm install -g @aws/agentcore

# 2. Configure AWS
aws configure

# 3. Set your Account ID in aws-targets.json
#    Edit agentcore/aws-targets.json → set "account_id": "YOUR_ACCOUNT_ID"

# 4. Install agent dependencies
cd app/AITestAgent
uv venv
.venv\Scripts\activate
uv pip install -e .
cd ../..

# 5. Test locally (from project root)
agentcore dev
# (in another terminal) agentcore invoke --prompt '{"title":"Test","description":"Test login","base_url":"http://localhost:3000","test_type":"functional"}'

# 6. Deploy to AWS (from project root)
agentcore deploy

# 7. Configure backend
#    Add to backend/.env:
#      AGENTCORE_ENABLED=true
#      AGENTCORE_AGENT_ARN=<arn-from-step-6>
#      AGENTCORE_REGION=ap-south-1

# 8. Start backend
cd backend
pip install -r requirements.txt
python start.py

# Done! Generate test cases from the frontend.
```
