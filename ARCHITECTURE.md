# GulfAgent — System Architecture

> End-to-end architecture of the GulfAgent AI agent platform.

---

## Table of Contents

1. [End-to-End Task Flow](#1-end-to-end-task-flow)
2. [Model Routing](#2-model-routing)
3. [Cost Optimizer](#3-cost-optimizer)
4. [Database Schema](#4-database-schema)
5. [BullMQ Queues](#5-bullmq-queues)
6. [Approval Flow](#6-approval-flow)
7. [GCC Connector Architecture](#7-gcc-connector-architecture)
8. [Security](#8-security)

---

## 1. End-to-End Task Flow

```
┌─────────────────────────────────────────────────────────────────────┐
│                        USER INTERFACES                              │
│  ┌──────────┐  ┌───────────┐  ┌────────┐  ┌──────────┐             │
│  │ WhatsApp │  │ Dashboard │  │  API   │  │Automation│             │
│  │   Text   │  │  (Next.js)│  │  Call  │  │ (Cron)   │             │
│  └────┬─────┘  └─────┬─────┘  └───┬────┘  └────┬─────┘             │
│       │              │            │            │                    │
│       ▼              ▼            ▼            ▼                    │
│  ┌─────────────────────────────────────────────────────┐           │
│  │              FastAPI (main.py)                       │           │
│  │  ┌──────────────┐  ┌────────────┐  ┌─────────────┐ │           │
│  │  │ Rate Limiter │  │  Auth JWT  │  │ Error Env.  │ │           │
│  │  │ (slowapi)    │  │ (Supabase) │  │ {err,code}  │ │           │
│  │  └──────────────┘  └────────────┘  └─────────────┘ │           │
│  └──────────────────────┬──────────────────────────────┘           │
│                         │                                           │
│                         ▼                                           │
│  ┌─────────────────────────────────────────────────────┐           │
│  │           BackgroundTasks + LangGraph                │           │
│  │                                                       │           │
│  │  1. Task record created in Supabase (status:pending)  │           │
│  │  2. Background task triggers LangGraph pipeline       │           │
│  │  3. classify_task → orchestrator.classify()          │           │
│  │  4. route_by_type selects execution path             │           │
│  │  5. execute_simple_llm / execute_browser             │           │
│  │     / execute_connector runs                          │           │
│  │  6. OpenRouter returns result                        │           │
│  │  7. Task record updated (status:completed/failed)    │           │
│  │  8. Credits deducted after completion                │           │
│  └──────────────────────┬──────────────────────────────┘           │
│                         │                                           │
│                         ▼                                           │
│  ┌─────────────────────────────────────────────────────┐           │
│  │                   OUTPUT CHANNELS                    │           │
│  │  ┌────────────┐  ┌──────────┐  ┌────────────────┐  │           │
│  │  │  WhatsApp  │  │ SSE Feed │  │  Webhook Call  │  │           │
│  │  │ (Evolution)│  │ (Stream) │  │  (API response)│  │           │
│  │  └────────────┘  └──────────┘  └────────────────┘  │           │
│  └─────────────────────────────────────────────────────┘           │
└─────────────────────────────────────────────────────────────────────┘
```

### Detailed Step-by-Step

1. **User sends prompt** via WhatsApp text, dashboard TaskInput, API call, or automation trigger
2. **FastAPI** receives the request, validates JWT/Supabase auth, checks rate limits (slowapi), creates a `Task` record in Supabase with `status: pending`
3. **BackgroundTasks** (FastAPI) asynchronously triggers the LangGraph pipeline via `_execute_task_bg()` in `tasks.py`
4. **AgentManager** classifies the prompt and determines the delegation path.
5. **Delegation node runs**:
   - `execute_simple_llm`: Direct OpenRouter call for general queries.
   - `execute_browser`: **BrowserAgent** (browser-use) for web navigation.
   - `execute_code`: **CodeAgent** (E2B Sandbox) for data analysis and script execution.
   - `execute_research`: **ResearchAgent** for multi-step information synthesis.
   - `execute_connector`: GCC-specific connectors.
6. **OpenRouter returns** structured response with result, tokens, cost, latency
7. **Task record updated** in Supabase with result, metadata, cost tracking fields
8. **Credits deducted** AFTER successful completion via `deduct_credits_after_task()`
9. **User notified** via WhatsApp (Evolution API) or SSE event (dashboard live feed)

---

## 2. Model Routing

All LLM calls go through **OpenRouter** as the single gateway. The `ModelOrchestrator` class in `core/model_orchestrator.py` manages routing with a three-tier fallback chain per task type.

### Model Routes Table

| Task Type | Primary Model | Secondary | Emergency | Cost Input/1k | Cost Output/1k |
|---|---|---|---|---|---|
| `simple_qa` | `google/gemini-flash-1.5` | `gemini-flash` | `gemini-flash` | $0.000075 | $0.0003 |
| `browser_task` | `moonshotai/kimi-k2.6` | `gemini-flash` | `gemini-flash` | $0.0009 | $0.0036 |
| `arabic_task` | `mistralai/mistral-large` | `gemini-flash` | `gemini-flash` | $0.002 | $0.008 |
| `code_task` | `moonshotai/kimi-k2.6` | `gemini-flash` | `gemini-flash` | $0.0009 | $0.0036 |
| `research_task` | `google/gemini-pro-1.5` | `gemini-flash` | `gemini-flash` | $0.0025 | $0.0075 |
| `creative_task` | `meta-llama/llama-3.3-70b` | `gemini-flash` | `gemini-flash` | $0.0006 | $0.002 |
| `sensitive_task` | `mistralai/mistral-large` | `gemini-flash` | `gemini-flash` | $0.002 | $0.008 |
| `classifier` | `moonshotai/kimi-k2.6:free` | `gemini-flash` | `gemini-flash` | $0.0 | $0.0 |
| `connector_format` | `google/gemini-flash-1.5` | `gemini-flash` | `gemini-flash` | $0.000075 | $0.0003 |

### Fallback Chain

For each task type, the orchestrator tries models in sequence:
1. **Primary** — best model for the task type (highest quality)
2. **Secondary** — fallback if primary is unavailable or errors
3. **Emergency** — last resort model (always `gemini-flash`)

If all three fail, the task is marked as failed with the error from the last attempt.

### Classifier Routing

Before execution, task type is determined by the classifier:
- **LLM-based** (primary): `orchestrator.classify()` using `moonshotai/kimi-k2.6:free`
- **Keyword pre-screen**: Connector keywords (careem, noon, talabat, dubai now) are detected before LLM classification
- **Fallback**: If classifier fails, defaults to `simple_qa`

---

## 3. Cost Optimizer

For **Basic tier** users, the orchestrator applies cost optimization:
- Non-sensitive task types (`simple_qa`, `research_task`, `creative_task`, `code_task`) prefer `google/gemini-flash-1.5` as the first model regardless of the primary model
- Sensitive types (`sensitive_task`, `browser_task`, `arabic_task`) always use their designated primary model
- **Pro tier** users always get the primary model for their task type

### Cost Calculation

```python
# Per-model cost map in model_orchestrator.py
MODEL_COST_MAP = {
    "google/gemini-flash-1.5":          {"cost_per_1k_in": 0.000075, "cost_per_1k_out": 0.0003},
    "moonshotai/kimi-k2.6":             {"cost_per_1k_in": 0.0009,   "cost_per_1k_out": 0.0036},
    "moonshotai/kimi-k2.6:free":        {"cost_per_1k_in": 0.0,     "cost_per_1k_out": 0.0},
    "mistralai/mistral-large":          {"cost_per_1k_in": 0.002,   "cost_per_1k_out": 0.008},
    "google/gemini-pro-1.5":            {"cost_per_1k_in": 0.0025,  "cost_per_1k_out": 0.0075},
    "meta-llama/llama-3.3-70b":         {"cost_per_1k_in": 0.0006,  "cost_per_1k_out": 0.002},
}
```

`cost_usd = (input_tokens / 1000) × cost_per_1k_in + (output_tokens / 1000) × cost_per_1k_out`

---

## 4. Database Schema

All tables in Supabase (PostgreSQL) with Row-Level Security.

### Entity Relationship

```
users 1 ──── * tasks        users 1 ──── * usage
users 1 ──── * automations  users 1 ──── * user_skills
skills 1 ──── * user_skills skills 1 ──── * automations (via skill_id)
tasks 1 ──── 0..1 approvals automations 1 ──── * tasks (via automation_id)
```

### Tables

#### `users`
| Column | Type | Description |
|---|---|---|
| `id` | UUID PK | Mirrors Supabase `auth.users.id` |
| `email` | VARCHAR(255) UNIQUE | User email |
| `phone` | VARCHAR(20) | E.164 format (+971...) |
| `full_name` | VARCHAR(255) | Display name |
| `subscription_tier` | VARCHAR(20) | `basic` / `pro` / `enterprise` |
| `subscription_status` | VARCHAR(20) | `trial` / `active` / `cancelled` |
| `stripe_customer_id` | VARCHAR(100) | Stripe customer reference |
| `stripe_subscription_id` | VARCHAR(100) | Stripe subscription reference |
| `preferred_language` | VARCHAR(10) | `en` / `ar` |
| `created_at` | TIMESTAMPTZ | Auto-generated |
| `updated_at` | TIMESTAMPTZ | On update |

#### `tasks`
| Column | Type | Description |
|---|---|---|
| `id` | UUID PK | Auto-generated |
| `user_id` | UUID FK → users | Task owner |
| `prompt` | TEXT | User's task description |
| `task_type` | VARCHAR(20) | `simple` / `browser` / `connector_*` |
| `status` | VARCHAR(30) | `pending` / `running` / `awaiting_approval` / `completed` / `failed` / `cancelled` |
| `result` | TEXT | Task output |
| `error_message` | TEXT | Error details on failure |
| `tokens_used` | INTEGER | Total input + output tokens |
| `credits_used` | INTEGER | Credits deducted |
| `metadata` | JSONB | Screenshots, steps, model info |
| `source` | VARCHAR(20) | `dashboard` / `whatsapp` / `api` / `automation` |
| `automation_id` | UUID FK → automations | Parent automation (nullable) |
| `model_used` | TEXT | Model that executed the task |
| `cost_usd` | NUMERIC(12,6) | Dollar cost of execution |
| `latency_ms` | INTEGER | Execution time in ms |
| `fallback_used` | BOOLEAN | Whether fallback model was used |
| `created_at` | TIMESTAMPTZ | Auto-generated |
| `started_at` | TIMESTAMPTZ | When execution began |
| `completed_at` | TIMESTAMPTZ | When execution finished |

#### `usage`
| Column | Type | Description |
|---|---|---|
| `id` | UUID PK | Auto-generated |
| `user_id` | UUID FK → users | Usage owner |
| `year_month` | VARCHAR(7) | `2024-01` format |
| `credits_used` | INTEGER | Credits consumed this month |
| `tasks_run` | INTEGER | Tasks executed this month |
| `credits_limit` | INTEGER | Monthly cap (5,000 basic / 20,000 pro) |
| `updated_at` | TIMESTAMPTZ | Last updated |

#### `automations`
| Column | Type | Description |
|---|---|---|
| `id` | UUID PK | Auto-generated |
| `user_id` | UUID FK → users | Owner |
| `name` | VARCHAR(255) | Automation name |
| `prompt` | TEXT | Task prompt to execute |
| `cron` | VARCHAR(100) | Cron expression |
| `active` | BOOLEAN | Paused or running |
| `skill_id` | UUID FK → skills | Source skill (nullable) |
| `last_run` | TIMESTAMPTZ | Last execution |
| `next_run` | TIMESTAMPTZ | Next scheduled execution |
| `bullmq_job_id` | VARCHAR(255) | BullMQ repeatable job ID |
| `created_at` | TIMESTAMPTZ | Auto-generated |

#### `skills`
| Column | Type | Description |
|---|---|---|
| `id` | UUID PK | Auto-generated |
| `name` | VARCHAR(255) | Skill display name |
| `slug` | VARCHAR(100) UNIQUE | URL-friendly identifier |
| `description` | TEXT | Skill description |
| `category` | VARCHAR(50) | `Research` / `E-commerce` / `Government` / `Finance` / `HR` |
| `prompt_template` | TEXT | Prompt template with variables |
| `icon` | VARCHAR(50) | Emoji or icon name |
| `default_cron` | VARCHAR(100) | Default schedule (nullable) |
| `credit_cost` | INTEGER | Credits per execution |
| `active` | BOOLEAN | Available in marketplace |
| `created_at` | TIMESTAMPTZ | Auto-generated |

#### `user_skills`
| Column | Type | Description |
|---|---|---|
| `id` | UUID PK | Auto-generated |
| `user_id` | UUID FK → users | Skill owner |
| `skill_id` | UUID FK → skills | Activated skill |
| `activated_at` | TIMESTAMPTZ | When activated |

#### `approvals`
| Column | Type | Description |
|---|---|---|
| `id` | UUID PK | Auto-generated |
| `task_id` | UUID FK → tasks | Task requiring approval |
| `action_type` | VARCHAR(50) | `email` / `form_submit` / `payment` / `file_delete` |
| `action_payload` | JSONB | Action parameters |
| `decision` | VARCHAR(10) | `approved` / `denied` / `timeout` (nullable) |
| `expires_at` | TIMESTAMPTZ | 5 minutes from creation |
| `decided_at` | TIMESTAMPTZ | When decision was made |
| `created_at` | TIMESTAMPTZ | Auto-generated |

---

## 5. BullMQ Queues

Two BullMQ queues manage asynchronous operations, backed by Redis.

### Queue: Approvals (`gulfagent-approvals`)

| Job | Description | Behavior |
|---|---|---|
| `auto-deny:{approval_id}` | Delayed job (5 min) | Checks if decision still null, sets to `timeout`, cancels task |

**Worker**: `approval_worker` in `scheduler_agent.py`
- Listens for delayed jobs
- On timeout: marks approval as `timeout`, cancels associated task
- Sends WhatsApp notification: "⏰ Approval timed out. Task cancelled."

### Queue: Automations (`gulfagent-automations`)

| Job | Description | Behavior |
|---|---|---|
| `automation:{automation_id}` | Repeatable BullMQ job | Runs task pipeline, sends WhatsApp result |

**Worker**: `automation_worker` in `scheduler_agent.py`
- On repeatable job trigger: creates Task record, runs LangGraph pipeline, deducts credits, sends WhatsApp result
- On startup: restores active automations from DB and re-registers their repeatable jobs

---

## 5b. E2B Code Sandbox

- **SandboxExecutor**: provides `execute_code()`, `execute_with_files()`, and `execute_data_analysis()` methods using the E2B SDK.
- **Isolation**: Every execution runs in a fresh, isolated E2B sandbox that is auto-destroyed after completion.
- **Limits**: 30-second execution timeout to prevent runaway scripts.
- **File Handling**: Files (CSV, Excel, PDF, images) are uploaded to the sandbox before execution; generated results (e.g., charts) are returned as base64.
- **Routing**: `code_execution` tasks are routed to `moonshotai/kimi-k2.6` via the orchestrator for script generation.
- **WhatsApp Integration**: Chart images generated in the sandbox are returned as base64 for direct delivery via WhatsApp.

---

## 5c. Multi-Agent Manager

- **ManagerAgent**: The entry point for the LangGraph pipeline. It receives every task, classifies it, and delegates to specialized agents.
- **Delegation Logic**:
  - `simple_qa` → Direct LLM response via orchestrator.
  - `browser_task` → **BrowserAgent** using `browser-use`.
  - `code_execution` → **CodeAgent** using E2B Sandbox.
  - `research_task` → **ResearchAgent** (multi-step flow).
  - `connector_*` → GCC-specific connectors.
- **ResearchAgent Flow**: Executes a 3-step process:
  1. Decompose the research question into sub-queries.
  2. Execute 2-3 browser queries to gather information.
  3. Synthesize the findings into a final report.

---

## 6. Approval Flow

```
User submits task ──→ Agent detects destructive action
                            │
                            ▼
              ┌─────────────────────────┐
              │  Approval record created │
              │  action_type, payload    │
              │  expires_at = now + 5min │
              └────────────┬────────────┘
                           │
                           ▼
              ┌─────────────────────────┐
              │  Task status set to      │
              │  "awaiting_approval"     │
              └────────────┬────────────┘
                           │
              ┌────────────▼────────────┐
              │  WhatsApp message sent:  │
              │  "Approve? Reply Y/N"    │
              └────────────┬────────────┘
                           │
            ┌──────────────┼──────────────┐
            ▼              ▼              ▼
    ┌────────────┐  ┌────────────┐  ┌────────────┐
    │  Y / Yes  │  │  N / No   │  │  5 min     │
    │  نعم      │  │  لا       │  │  timeout   │
    └─────┬──────┘  └─────┬──────┘  └─────┬──────┘
          │               │               │
          ▼               ▼               ▼
    ┌────────────┐  ┌────────────┐  ┌────────────┐
    │ Approved    │  │ Denied     │  │ Auto-deny  │
    │ Task resumes│  │ Cancelled  │  │ Timed out  │
    └────────────┘  └────────────┘  └────────────┘
```

### Destructive Actions Requiring Approval

- Sending an email
- Submitting a web form
- Making a payment
- Deleting a file
- Posting content to social media

---

## 7. GCC Connector Architecture

```
┌────────────────────────────────────────────────────┐
│                  Connector Pattern                   │
│                                                      │
│  ┌──────────────────────────────────────────┐       │
│  │           Tool Registry                   │       │
│  │  Registers connectors as available tools  │       │
│  └────────────────────┬─────────────────────┘       │
│                       │                              │
│          ┌────────────┼────────────┐                 │
│          ▼            ▼            ▼                 │
│  ┌────────────┐ ┌────────────┐ ┌────────────┐      │
│  │   Careem   │ │    Noon    │ │   Talabat  │      │
│  │ Connector  │ │ Connector  │ │ Connector  │      │
│  └─────┬──────┘ └─────┬──────┘ └─────┬──────┘      │
│        │              │              │              │
│        ▼              ▼              ▼              │
│  ┌──────────────────────────────────────────┐       │
│  │           BrowserAgent                    │       │
│  │  (browser-use wrapped with screenshot)    │       │
│  └──────────────────────────────────────────┘       │
│                                                      │
│  ┌──────────────────────────────────────────┐       │
│  │     OR Formatting LLM (gemini-flash)     │       │
│  │  Converts structured data → human text   │       │
│  └──────────────────────────────────────────┘       │
└────────────────────────────────────────────────────┘
```

### Connector Detection Flow

1. **Classifier pre-screens** prompt for connector keywords (careem, noon, talabat, dubai now, dubainow)
2. **Task type set** to `connector_careem`, `connector_noon`, `connector_talabat`, or `connector_dubai_now`
3. **route_by_type** maps to `execute_connector` node
4. **Connector instance** created from `backend/connectors/` module
5. **BrowserAgent** used internally by each connector for web navigation
6. **Structured data** formatted via orchestrator using `connector_format` model (gemini-flash)

### Connector Files

| File | Service | Capabilities |
|---|---|---|
| `connectors/careem.py` | Careem | Book ride, check fare, ride history |
| `connectors/noon.py` | Noon | Search products, get prices, check orders |
| `connectors/talabat.py` | Talabat | Browse menus, order status, restaurant search |
| `connectors/dubai_now.py` | DubaiNow | Check fines, renewal status, government services |

---

## 8. Security

### Destructive Code Detection

For `code_execution` tasks, the system scans generated code for `DESTRUCTIVE_CODE_PATTERNS` before execution. Patterns include:
- System commands: `os.system`, `subprocess.run`, `shutil.rmtree`
- File system modifications outside the sandbox's temporary directory.
- Network requests to internal infrastructure.
- If detected, the task is routed through the **Approval Flow**, requiring explicit user confirmation via WhatsApp before proceeding.

### Supabase Row-Level Security (RLS)

All 7 tables have RLS policies ensuring users can only access their own data:

| Table | Policy |
|---|---|
| `users` | `user_id = auth.uid()` |
| `tasks` | `user_id = auth.uid()` |
| `usage` | `user_id = auth.uid()` |
| `automations` | `user_id = auth.uid()` |
| `skills` | Public read; write admin-only |
| `user_skills` | `user_id = auth.uid()` |
| `approvals` | Via task ownership join |

### JWT Validation

- All API routes (except webhooks and health) protected by `Depends(get_current_user_id)`
- JWT validated against Supabase Auth service
- Magic link authentication flow (no passwords stored)

### Rate Limiting

| Scope | Limit | Applied To |
|---|---|---|
| Default | 60 requests/min | All authenticated routes |
| POST | 10 requests/min | Task creation, automation create/update, billing |
| GET | 30 requests/min | List operations, detail views |
| Webhooks | Unlimited | Stripe + WhatsApp webhooks |

Configured via `slowapi` in `core/rate_limiter.py`.

### CORS Whitelist

```python
allow_origins = [
    "http://localhost:3000",           # Local dev
    settings.next_public_app_url,      # Production domain
]
```

### Stripe Webhook Verification

All Stripe webhook events are verified using `stripe.Webhook.construct_event()` with the signing secret. Unverified payloads are rejected with 400 status.

### Error Handling

All API errors return structured envelopes:
```json
{
    "data": null,
    "error": {
        "code": "INTERNAL_SERVER_ERROR",
        "message": "An unexpected error occurred."
    }
}
```

Error codes: `TASK_NOT_FOUND`, `AUTOMATION_NOT_FOUND`, `SKILL_NOT_FOUND`, `STRIPE_ERROR`, `STRIPE_CHECKOUT_ERROR`, `PRICE_NOT_FOUND`, `INVALID_TIER`, `NO_SUBSCRIPTION`, `PORTAL_ERROR`, `CREDIT_LIMIT_REACHED`, `AUTOMATION_LIMIT_REACHED`, `RATE_LIMIT_EXCEEDED`.

---

## Project Structure

```
gulfagent/
├── README.md                         # ← This file
├── ARCHITECTURE.md                   # ← You are here
├── CHANGELOG.md
├── CLAUDE.md                         # AI context for CTO.new
├── TASKS.md                          # Build roadmap
├── .env.example
├── docker-compose.yml
├── railway.toml
│
├── backend/
│   ├── main.py                       # FastAPI app + lifespan
│   ├── config.py                     # Pydantic settings
│   ├── requirements.txt
│   │
│   ├── agents/
│   │   ├── base_agent.py             # Abstract agent interface
│   │   ├── browser_agent.py          # browser-use wrapper
│   │   ├── whatsapp_agent.py         # Evolution API handler
│   │   ├── scheduler_agent.py        # BullMQ worker + scheduler
│   │   └── screenshot_storage.py     # Supabase Storage uploads
│   │
│   ├── api/
│   │   ├── tasks.py                  # Task CRUD + SSE stream
│   │   ├── automations.py            # Automation CRUD
│   │   ├── skills.py                 # Skills marketplace
│   │   ├── billing.py                # Stripe checkout/setup
│   │   ├── webhooks.py               # WhatsApp + Stripe webhooks
│   │   ├── usage.py                  # Usage summary
│   │   ├── approvals.py              # Approval decision endpoints
│   │   ├── users.py                  # User profile + phone linking
│   │   ├── admin.py                  # Orchestrator admin endpoints
│   │   └── deps.py                   # Shared dependencies
│   │
│   ├── core/
│   │   ├── langgraph_pipeline.py     # StateGraph definition
│   │   ├── model_orchestrator.py     # OpenRouter model routing
│   │   ├── tool_registry.py          # Agent tool registration
│   │   ├── usage_tracker.py          # Credit checks + deductions
│   │   ├── approval_manager.py       # Approval CRUD + timeout
│   │   └── rate_limiter.py           # slowapi configuration
│   │
│   ├── connectors/
│   │   ├── careem.py                 # Careem ride booking
│   │   ├── noon.py                   # Noon product search
│   │   ├── talabat.py                # Talabat food ordering
│   │   └── dubai_now.py              # DubaiNow government services
│   │
│   ├── payments/
│   │   ├── hyperpay.py               # HyperPay gateway
│   │   └── tabby.py                  # Tabby/Tamara BNPL
│   │
│   └── db/
│       ├── models.py                 # SQLAlchemy models
│       ├── session.py                # Async session factory
│       ├── seed_skills.py            # 10 skill templates
│       └── migrations/               # Alembic migrations
│
├── frontend/
│   ├── app/
│   │   ├── layout.tsx                # Root layout + RTL support
│   │   ├── page.tsx                  # Landing / login
│   │   ├── globals.css               # Dark theme (#0A0A0A)
│   │   ├── login/page.tsx            # Supabase magic link
│   │   ├── welcome/page.tsx          # Arabic onboarding
│   │   ├── auth/                     # Auth callback routes
│   │   ├── components/               # Shared components
│   │   │   ├── TaskFeed.tsx          # SSE live activity
│   │   │   ├── TaskInput.tsx         # Task submission form
│   │   │   ├── ApprovalModal.tsx     # Approve/deny overlay
│   │   │   ├── UsageBar.tsx          # Credits progress bar
│   │   │   ├── ErrorBoundary.tsx     # Error boundaries
│   │   │   └── rtl-provider.tsx      # RTL context provider
│   │   └── dashboard/
│   │       ├── page.tsx              # Main dashboard
│   │       ├── tasks/page.tsx        # Task history
│   │       ├── automations/page.tsx  # Automation management
│   │       ├── skills/page.tsx       # Skills marketplace
│   │       ├── usage/page.tsx        # Usage analytics
│   │       └── settings/page.tsx     # User settings
│   ├── middleware.ts                 # Protected route guard
│   ├── lib/                          # Utility functions
│   ├── package.json
│   └── tailwind.config.ts
│
└── infra/
    ├── docker-compose.yml            # Production compose
    ├── nginx.conf                    # Reverse proxy + SSL
    └── deploy.sh                     # Dokploy deployment
```