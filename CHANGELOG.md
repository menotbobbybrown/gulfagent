# Changelog

All notable changes to GulfAgent are documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

---

## [0.7] — Pre-deployment Fixes (Current)

**Date:** June 2025

### Added
- `railway.toml` for Railway deployment (Dockerfile-based build, health check path)
- WhatsApp webhook auto-registration on startup via lifespan
- Active automation restoration from DB on scheduler restart (re-registers BullMQ repeatable jobs)
- `MODEL_COST_MAP` for accurate per-model cost tracking in `model_orchestrator.py`
- Updated `CLAUDE.md` to reflect OpenRouter as the single LLM gateway

### Changed
- Deployment configuration streamlined for Railway + Vercel

---

## [0.6] — OpenRouter Migration

**Date:** May 2026

### Added
- `model_orchestrator.py` — single LLM gateway with 8 task type model routing
- `MODEL_ROUTES` dictionary with primary/secondary/emergency fallback chains
- `MODEL_COST_MAP` for input/output token cost calculation
- Cost optimizer for Basic tier (prefers `gemini-flash-1.5` for non-sensitive types)
- Admin endpoints: `GET /api/admin/orchestrator/status`, `POST /api/admin/orchestrator/test`
- Arabic context prompting for `arabic_task` type
- `connector_format` task type for formatting connector structured data

### Removed
- All Anthropic SDK dependencies (`anthropic` package, Claude API calls)
- All Ollama dependencies and Qwen3 model references
- `arabic_router.py` — Arabic routing now handled by classifier + `arabic_task` model route

### Changed
- `config.py` — replaced Anthropic/Ollama env vars with OpenRouter config
- `requirements.txt` — removed `anthropic`, kept `openai` as the sole LLM SDK
- `.env.example` — removed `ANTHROPIC_API_KEY`, `OLLAMA_BASE_URL`; added OpenRouter vars
- `browser_agent.py` — uses orchestrator instead of direct Claude calls
- `langgraph_pipeline.py` — all nodes route through orchestrator
- `admin.py` — orchestrator status + test endpoints
- `agents/__init__.py` — cleaned up imports

### Files
```
NEW:    backend/core/model_orchestrator.py
DEL:    backend/agents/arabic_router.py
UPD:    backend/config.py
UPD:    backend/requirements.txt
UPD:    .env.example
UPD:    backend/agents/browser_agent.py
UPD:    backend/core/langgraph_pipeline.py
UPD:    backend/api/admin.py
UPD:    backend/agents/__init__.py
```

---

## [0.5] — Phase 5: GCC Localization

**Date:** May 2026

### Added
- **RTL Arabic UI** — dir attribute toggle with Noto Sans Arabic font in `rtl-provider.tsx`
- **Careem Connector** — `connectors/careem.py` — book ride, fare check
- **Noon Connector** — `connectors/noon.py` — product search, pricing
- **Talabat Connector** — `connectors/talabat.py` — menu browse, order status
- **DubaiNow Connector** — `connectors/dubai_now.py` — fine checks, renewals
- **HyperPay Gateway** — `payments/hyperpay.py` — AED payment processing skeleton
- **Tabby/Tamara BNPL** — `payments/tabby.py` — buy-now-pay-later integration
- **Arabic Onboarding** — `welcome/page.tsx` — Arabic-first welcome page for GCC phone numbers
- `connector_format` model route for formatting connector results

### Changed
- `webhooks.py` — Arabic acknowledgement messages, GCC phone number detection, Arabic welcome flow
- `globals.css` — RTL-aware styles
- `DashboardShell.tsx` — language toggle in sidebar
- `admin.py` — connector test endpoints
- `langgraph_pipeline.py` — added `execute_connector` node with keyword pre-screening

### Files
```
NEW:    backend/connectors/careem.py
NEW:    backend/connectors/noon.py
NEW:    backend/connectors/talabat.py
NEW:    backend/connectors/dubai_now.py
NEW:    backend/payments/hyperpay.py
NEW:    backend/payments/tabby.py
NEW:    frontend/app/components/rtl-provider.tsx
NEW:    frontend/app/welcome/page.tsx
UPD:    backend/api/webhooks.py
UPD:    frontend/app/globals.css
UPD:    frontend/app/dashboard/DashboardShell.tsx
UPD:    backend/api/admin.py
UPD:    backend/core/langgraph_pipeline.py
```

---

## [0.4] — Phase 4: Billing + Polish

**Date:** May 2026

### Added
- **Stripe Billing** — full integration with 4 webhook event handlers:
  - `checkout.session.completed` — activate subscription
  - `invoice.paid` — sync subscription, reset credits
  - `customer.subscription.updated` — handle plan changes
  - `customer.subscription.deleted` — downgrade to basic
- **Credit limit enforcement** — 5 automations for Basic, unlimited for Pro (403 on exceed)
- **Low credits alert** — WhatsApp message at 20% remaining via usage tracker
- **Usage dashboard** — `usage/page.tsx` with credit progress bars
- **Error boundaries** — `ErrorBoundary.tsx` wrapping all dashboard pages
- **Structured error responses** — all API errors return `{ error: { code, message } }`
- **Rate limiting** — slowapi configuration (60/min default, 10/min POST, 30/min GET)
- **Task timeout** — 5-minute maximum for browser agent execution (`TASK_TIMEOUT_SECONDS = 300`)
- **Retry logic** — failed tasks retry once automatically (not for timeout errors)
- **Langfuse** — commented-out observability integration
- **Sentry** — commented-out error tracking integration
- **nginx config** — rate limiting zones, SSL redirect, gzip compression
- **deploy.sh** — one-command deploy with health check retry and rollback

### Changed
- `billing.py` — setup, checkout, portal endpoints
- `webhooks.py` — Stripe event handling functions
- `usage_tracker.py` — check + deduct with tier-aware limits
- `tasks.py` — timeout and retry logic in background executor

### Files
```
NEW:    backend/core/rate_limiter.py
NEW:    frontend/app/dashboard/usage/page.tsx
NEW:    frontend/app/components/ErrorBoundary.tsx
UPD:    backend/api/billing.py
UPD:    backend/api/webhooks.py
UPD:    backend/core/usage_tracker.py
UPD:    infra/nginx.conf
UPD:    infra/deploy.sh
```

---

## [0.3] — Phase 3: Automations + Skills

**Date:** May 2026

### Added
- **Automations CRUD** — `POST`, `GET`, `PATCH`, `DELETE` for scheduled tasks
- **BullMQ repeatable jobs** — cron-based scheduling via `scheduler_agent.py`
- **Automation worker** — processes scheduled tasks, sends WhatsApp results
- **Skills marketplace** — 10 GCC-specific skill templates
- **One-click activate** — skill activation creates pre-filled automation
- **Frontend automations page** — list, create, pause, delete with cron builder

### Skills Seeded
| # | Skill | Category | Cron |
|---|---|---|---|
| T53 | Daily Gulf News Briefing | Research | `0 8 * * 1-5` |
| T54 | Price Monitor | E-commerce | `0 */6 * * *` |
| T55 | Lead Researcher | Research | — |
| T56 | Gmail to Linear | Productivity | `0 */4 * * *` |
| T57 | Weekly Competitor Intel | Research | `0 9 * * 1` |
| T58 | DubaiNow Reminder | Government | `0 10 * * 1` |
| T59 | LinkedIn Outreach | HR | — |
| T60 | Mag 7 Stock Brief | Finance | `0 8 * * 1-5` |
| T61 | Tender Monitor | Government | `0 9 * * 1-5` |
| T62 | WhatsApp Report | Productivity | `0 18 * * 5` |

### Files
```
NEW:    backend/db/seed_skills.py
UPD:    backend/api/automations.py
UPD:    backend/api/skills.py
UPD:    backend/agents/scheduler_agent.py
UPD:    frontend/app/dashboard/automations/page.tsx
UPD:    frontend/app/dashboard/skills/page.tsx
```

---

## [0.2] — Phase 2: Browser Agent + WhatsApp

**Date:** April 2026

### Added
- **BrowserAgent** — `browser_agent.py` wrapping browser-use with screenshot capture
- **Screenshot storage** — Supabase Storage bucket upload with per-task organization
- **Task type classifier** — LLM-based classification (originally Claude Haiku, migrated v0.6)
- **Approvals table** — `approvals` with 5-minute timeout
- **Approval flow** — create approval record, pause agent, decide via dashboard or WhatsApp
- **ApprovalModal** — dashboard overlay for approve/deny
- **Auto-deny** — BullMQ delayed job at 5 minutes
- **Evolution API integration** — WhatsApp message send/receive
- **WhatsApp webhook** — receive messages, create tasks, send results
- **Arabic detection** — Unicode range check for Arabic script
- **Phone linking** — `PATCH /api/users/me/phone` to link WhatsApp number

### Files
```
NEW:    backend/agents/browser_agent.py
NEW:    backend/agents/screenshot_storage.py
NEW:    backend/agents/whatsapp_agent.py
NEW:    backend/agents/arabic_router.py          (deleted v0.6)
NEW:    backend/api/approvals.py
NEW:    backend/api/webhooks.py
NEW:    backend/api/users.py
NEW:    backend/core/approval_manager.py
NEW:    frontend/app/components/ApprovalModal.tsx
```

---

## [0.1] — Phase 1: Foundation

**Date:** April 2026

### Added
- **FastAPI app** — `/health` endpoint with Supabase connectivity check on startup
- **Pydantic config** — all environment variables via `pydantic-settings`
- **SQLAlchemy models** — `users`, `tasks`, `usage`, `automations`, `skills`, `user_skills`, `approvals`
- **Raw SQL migrations** — all table DDL with RLS policies for Supabase
- **Task CRUD** — `POST /api/tasks`, `GET /api/tasks`, `GET /api/tasks/{id}` with pagination
- **LangGraph pipeline** — classifier + simple LLM execution via `StateGraph`
- **Usage tracker** — pre-check credits before task, deduct after completion
- **Next.js 14 frontend** — Tailwind dark theme (#0A0A0A), Supabase magic link auth
- **Protected routes** — middleware.ts with Supabase session validation
- **Dashboard shell** — sidebar navigation with usage bar
- **TaskInput + TaskFeed** — components with SSE live updates
- **Docker Compose** — FastAPI + Next.js + Redis stack
- `.env.example` — all 23 documented environment variables

### Files
```
NEW:    backend/main.py
NEW:    backend/config.py
NEW:    backend/db/models.py
NEW:    backend/db/session.py
NEW:    backend/api/tasks.py
NEW:    backend/core/langgraph_pipeline.py
NEW:    backend/core/usage_tracker.py
NEW:    backend/core/tool_registry.py
NEW:    frontend/ (Next.js scaffold)
NEW:    frontend/app/layout.tsx
NEW:    frontend/app/page.tsx
NEW:    frontend/app/globals.css
NEW:    frontend/middleware.ts
NEW:    frontend/app/components/TaskFeed.tsx
NEW:    frontend/app/components/TaskInput.tsx
NEW:    frontend/app/components/UsageBar.tsx
NEW:    frontend/app/dashboard/page.tsx
NEW:    frontend/app/dashboard/tasks/page.tsx
NEW:    frontend/app/dashboard/settings/page.tsx
NEW:    docker-compose.yml
NEW:    .env.example
```