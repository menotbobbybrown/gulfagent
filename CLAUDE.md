# GulfAgent — CLAUDE.md

> AI Agent Platform for GCC founders. Production-ready Bud.app competitor.
> Built by ModelNorth Ventures. Target: UAE SMEs, Saudi enterprise, Pakistani diaspora in Gulf.

---

## Project Overview

GulfAgent is a WhatsApp-first, Arabic-native AI agent platform that lets GCC
businesses automate tasks using computer use, browser automation, and
pre-built regional workflows. Think Bud.app but sovereign, local, and
actually reliable.

---

## Tech Stack

| Layer | Technology |
|---|---|
| Frontend | Next.js 14 (App Router) + Tailwind CSS |
| Backend | FastAPI (Python 3.11) |
| Agent Orchestration | LangGraph |
| Browser Agent | browser-use |
| WhatsApp | Evolution API (self-hosted) |
| Task Queue | BullMQ + Redis |
| Database | Supabase (PostgreSQL) |
| Auth | Supabase Auth (magic link) |
| Storage | Supabase Storage |
| Payments | Stripe + HyperPay + Tabby/Tamara (AED currency) |
| Infra | Docker + Dokploy on Hetzner VPS |
| LLM Gateway | OpenRouter (unified API for 8+ models) |

---

### Model Routing

| Task Type | Primary Model | Secondary Model | Emergency Fallback |
|---|---|---|---|
| Simple chat / query | Claude Sonnet 4 | GPT-4o | Gemini 2.5 Pro |
| Complex reasoning / code | Claude Opus 4 | GPT-4.1 | Gemini 2.5 Pro |
| Browser automation | Claude Sonnet 4 | GPT-4o | Gemini 2.5 Flash |
| Arabic / bilingual | Qwen3-8B | Claude Sonnet 4 | GPT-4o-mini |
| Tool calling / structured output | Claude Sonnet 4 | GPT-4o-mini | Gemini 2.5 Flash |
| Summarization | Claude Haiku 3.5 | GPT-4o-mini | Gemini 2.5 Flash |
| Classification / routing | GPT-4o-mini | Claude Haiku 3.5 | Qwen3-8B |
| Financial / compliance | Claude Sonnet 4 | GPT-4o | Gemini 2.5 Pro |

All models accessed through OpenRouter's unified API. Routing logic in `core/model_orchestrator.py`.

---

## Project Structure

```
gulfagent/
├── CLAUDE.md
├── TASKS.md
├── docker-compose.yml
├── .env.example
│
├── backend/
│   ├── main.py                  # FastAPI app entry
│   ├── requirements.txt
│   ├── config.py                # Settings via pydantic-settings
│   │
│   ├── agents/
│   │   ├── browser_agent.py     # browser-use wrapper
│   │   ├── whatsapp_agent.py    # Evolution API handler
│   │   ├── scheduler_agent.py   # BullMQ task scheduler
│   │   └── base_agent.py        # Shared agent interface
│   │
│   ├── api/
│   │   ├── tasks.py             # POST /tasks, GET /tasks/{id}
│   │   ├── automations.py       # CRUD for scheduled tasks
│   │   ├── skills.py            # Skills marketplace routes
│   │   ├── webhooks.py          # WhatsApp webhook receiver
│   │   ├── billing.py           # Stripe webhooks + usage
│   │   ├── admin.py             # Admin dashboard routes
│   │   ├── usage.py             # Usage stats API
│   │   └── deps.py              # Shared FastAPI dependencies
│   │
│   ├── core/
    │   │   ├── langgraph_pipeline.py   # Main agent graph
    │   │   ├── model_orchestrator.py   # OpenRouter model routing
    │   │   ├── tool_registry.py        # All agent tools
    │   │   ├── usage_tracker.py        # Credits/token tracking
    │   │   ├── approval_manager.py     # Approval CRUD + timeout
    │   │   └── rate_limiter.py         # slowapi rate limits
    │   │
    │   ├── connectors/              # GCC service connectors
    │   │   ├── careem.py            # Careem ride booking
    │   │   ├── noon.py              # Noon product search
    │   │   ├── talabat.py           # Talabat food ordering
    │   │   └── dubai_now.py         # DubaiNow government services
    │   │
    │   ├── payments/                # GCC payment gateways
    │   │   ├── hyperpay.py          # HyperPay AED processing
    │   │   └── tabby.py             # Tabby/Tamara BNPL
│   │
│   └── db/
│       ├── models.py            # SQLAlchemy models
│       └── migrations/          # Alembic migrations
│
├── frontend/
│   ├── package.json
│   └── app/
│       ├── layout.tsx
│       ├── page.tsx             # Landing / login
│       ├── dashboard/
│       │   ├── page.tsx         # Main dashboard
│       │   ├── tasks/page.tsx   # Task history + live feed
│       │   ├── automations/page.tsx
│       │   ├── skills/page.tsx
│       │   └── settings/page.tsx
│       └── components/
│           ├── TaskFeed.tsx     # SSE live activity feed
│           ├── TaskInput.tsx    # Task submission
│           ├── ApprovalModal.tsx # Approve/deny overlay
│           └── UsageBar.tsx     # Credits remaining
│
└── infra/
    ├── docker-compose.yml
    ├── nginx.conf
    └── deploy.sh
```

---

## Core Features (MVP Scope)

### 1. Task Runner
- User submits task via dashboard or WhatsApp
- Agent classifies task type (browser, search, data, communication) via OpenRouter-based classification
- LangGraph executes with appropriate tools
- Result returned via dashboard + WhatsApp

### 2. Approval Flow
- Before any destructive action (send email, make payment, post content)
- Push notification + WhatsApp message: "Approve? Y/N"
- 5 min timeout → auto-deny
- One-tap approve from WhatsApp

### 3. Browser Agent
- browser-use for web navigation
- Can: fill forms, extract data, monitor prices, submit applications
- Screenshots stored in Supabase Storage
- Replay available in dashboard

### 4. Automations (Scheduled Tasks)
- User creates recurring task with cron schedule
- BullMQ runs at scheduled time
- Results delivered via WhatsApp
- Pause/resume/delete from dashboard

### 5. Skills Marketplace
- Pre-built task templates
- Categories: Research, E-commerce, Government, Finance, HR
- One-click activate
- GCC-specific: DubaiNow, Absher, Noon, Talabat connectors

### 6. WhatsApp Interface
- Evolution API self-hosted
- User texts task → agent executes → result texted back
- Approval flow fully WhatsApp-native
- Supports Arabic + English

---

## Database Schema (Key Tables)

```sql
users           -- Supabase auth users + profile
tasks           -- All task executions (id, user_id, prompt, status, result, tokens_used)
automations     -- Scheduled tasks (cron, prompt, last_run, next_run, active)
skills          -- Skill templates (name, category, prompt_template, icon)
user_skills     -- Activated skills per user
usage           -- Monthly credit tracking per user
approvals       -- Pending approval requests (task_id, expires_at, decision)
```

---

## Environment Variables

```bash
# ── OpenRouter (Single LLM Gateway) ──────────────────────────
OPENROUTER_API_KEY=sk-or-...
OPENROUTER_BASE_URL=https://openrouter.ai/api/v1
OPENROUTER_SITE_URL=https://gulfagent.com
OPENROUTER_APP_NAME=GulfAgent

# ── Supabase ─────────────────────────────────────────────────
SUPABASE_URL=postgresql+asyncpg://postgres:[password]@db.[ref].supabase.co:5432/postgres
SUPABASE_URL_HTTP=https://[ref].supabase.co
SUPABASE_SERVICE_KEY=eyJ...
SUPABASE_ANON_KEY=eyJ...

# ── Supabase (Next.js public vars) ───────────────────────────
NEXT_PUBLIC_SUPABASE_URL=https://[ref].supabase.co
NEXT_PUBLIC_SUPABASE_ANON_KEY=eyJ...

# ── Evolution API (WhatsApp) ─────────────────────────────────
EVOLUTION_API_URL=http://localhost:8080
EVOLUTION_API_KEY=your-evolution-api-key
WHATSAPP_INSTANCE=gulfagent

# ── Redis (BullMQ) ───────────────────────────────────────────
REDIS_URL=redis://localhost:6379

# ── Stripe ───────────────────────────────────────────────────
STRIPE_SECRET_KEY=sk_test_...
STRIPE_WEBHOOK_SECRET=whsec_...
STRIPE_PRICE_BASIC=price_...    # AED 150/mo
STRIPE_PRICE_PRO=price_...      # AED 500/mo

# ── HyperPay (GCC Payment Gateway) ───────────────────────────
HYPERPAY_ENTITY_ID=...
HYPERPAY_ACCESS_TOKEN=...
HYPERPAY_BASE_URL=https://test.oppwa.com

# ── BNPL (Tabby/Tamara) ──────────────────────────────────────
TABBY_API_KEY=...
TABBY_BASE_URL=https://api.tabby.ai
TAMARA_API_KEY=...
TAMARA_BASE_URL=https://api.tamara.co

# ── App ──────────────────────────────────────────────────────
NEXT_PUBLIC_APP_URL=http://localhost:3000
NEXT_PUBLIC_API_URL=http://localhost:8000
LANGUAGE_DETECTION_ENABLED=true

# ── Observability (optional) ─────────────────────────────────
# LANGFUSE_PUBLIC_KEY=pk-...
# LANGFUSE_SECRET_KEY=sk-...
# LANGFUSE_HOST=https://cloud.langfuse.com
# SENTRY_DSN=https://...@...ingest.sentry.io/...
```

---

## Pricing Tiers (AED)

| Tier | Price | Credits/mo | Key Limits |
|---|---|---|---|
| Basic | AED 150/mo | 5,000 | 50 tasks, 5 automations |
| Pro | AED 500/mo | 20,000 | 200 tasks, unlimited automations, API access |
| Enterprise | Custom | Custom | Air-gapped, on-prem, SLA |

1 credit = 1 simple task action
Complex browser tasks = 50-200 credits
Overage: AED 1 per 100 credits

---

## Coding Standards

- Python: type hints everywhere, Pydantic v2 models
- TypeScript: strict mode, no `any`
- All API routes return `{ data, error, meta }` envelope
- SSE for live task updates (no WebSockets)
- All agent actions logged to `tasks` table before execution
- Approval required for: email sending, form submission, payment, file deletion
- Arabic text always stored as UTF-8

---

## Key Constraints

- DO NOT use WebSockets — use SSE for real-time updates
- DO NOT store API keys in code — always from env
- DO NOT run browser agent without task record in DB first
- All Stripe amounts in AED (currency: "aed")
- WhatsApp phone numbers stored in E.164 format (+971...)
- Credit deduction happens AFTER task completion, not before
