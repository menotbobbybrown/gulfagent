# GulfAgent 🤖

> **AI Agent Platform for GCC Founders — WhatsApp-first, Arabic-native, production-ready**

GulfAgent is a sovereign AI agent platform built for GCC businesses. Users submit tasks via WhatsApp or a Next.js dashboard. The LangGraph-powered agent classifies tasks, routes through OpenRouter to the best-fit model, executes browser actions via browser-use, and returns results via WhatsApp or SSE live feed.

Built by **ModelNorth Ventures** — target market: UAE SMEs, Saudi enterprise, Pakistani diaspora in Gulf.

---

## Tech Stack

| Layer | Technology |
|---|---|
| **Frontend** | FastAPI · Next.js 14 · Supabase |
| **Backend** | OpenRouter · Redis · Docker |
| **Agent** | LangGraph · browser-use · Evolution API |
| **Payments** | Stripe (AED) · HyperPay · Tabby/Tamara |

![FastAPI](https://img.shields.io/badge/FastAPI-005571?style=for-the-badge&logo=fastapi)
![Next.js 14](https://img.shields.io/badge/Next.js_14-000000?style=for-the-badge&logo=nextdotjs)
![Supabase](https://img.shields.io/badge/Supabase-3ECF8E?style=for-the-badge&logo=supabase)
![OpenRouter](https://img.shields.io/badge/OpenRouter-FF6B6B?style=for-the-badge&logo=openai)
![Redis](https://img.shields.io/badge/Redis-DC382D?style=for-the-badge&logo=redis)
![Docker](https://img.shields.io/badge/Docker-2496ED?style=for-the-badge&logo=docker)

---

## Features

### 10 Seed Skills
| Skill | Description |
|---|---|
| 📰 **Daily Gulf News Briefing** | Scrape Gulf News + Zawya, deliver WhatsApp summary |
| 💰 **Price Monitor** | Watch products on Noon/Amazon.ae, alert on price drops |
| 🔍 **Lead Researcher** | Company name → org info, contacts, news |
| 📧 **Gmail to Linear** | Scan Gmail for bugs/issues, create Linear tickets |
| 📊 **Weekly Competitor Intel** | Monitor 3 URLs, summarize changes weekly |
| 🏛️ **DubaiNow Reminder** | Check fine/renewal status, alert if due |
| 💼 **LinkedIn Outreach** | Draft personalized messages for prospects |
| 📈 **Mag 7 Stock Brief** | Daily pre-market prices via WhatsApp |
| 📋 **Tender Monitor** | Scan government portals for new tenders |
| 🗂️ **WhatsApp Report** | Compile week's task results into PDF, send |

### Core Platform
- **WhatsApp Interface** — Submit tasks, get results, approve actions — all via WhatsApp
- **Browser Agent** — browser-use powered web navigation with screenshot capture and replay
- **Automations** — Recurring tasks with cron scheduling via BullMQ
- **Approval Flow** — 5-minute timeout with Y/N approval via WhatsApp
- **Skills Marketplace** — One-click activate pre-built GCC-focused templates
- **Stripe Billing** — AED 150/mo Basic · AED 500/mo Pro · Custom Enterprise
- **RTL Arabic UI** — Full Arabic language support with dir-aware layout
- **GCC Connectors** — Careem, Noon, Talabat, DubaiNow integrations
- **Payment Gateways** — HyperPay + Tabby/Tamara BNPL

---

## Architecture

```
┌─────────────┐     ┌──────────────┐     ┌─────────────┐
│  WhatsApp   │────▶│   FastAPI    │────▶│  OpenRouter │
│  Dashboard  │     │  (LangGraph) │     │  (8 models) │
└─────────────┘     └──────┬───────┘     └─────────────┘
                           │
                    ┌──────▼───────┐
                    │   Supabase   │
                    │  (Postgres)  │
                    └──────────────┘
```

### Task Flow
1. **User sends prompt** via WhatsApp text message or dashboard TaskInput
2. **FastAPI creates Task record** in Supabase with `status: pending`
3. **BackgroundTasks triggers LangGraph pipeline**
4. **classify_task** uses Orchestrator's `classify()` to determine task type
5. **route_by_type** selects execution path: simple LLM, browser, or connector
6. **Execution node runs** against OpenRouter with appropriate model
7. **Task record updated** with result, tokens, cost, metadata
8. **WhatsApp notification** or **SSE event** sent to user

---

## Quick Start

```bash
# Clone the repository
git clone https://github.com/ModelNorth/gulfagent.git
cd gulfagent

# Copy environment variables
cp .env.example .env

# Fill in your API keys (see table below)

# Start all services
docker compose up

# Open the dashboard
open http://localhost:3000
```

---

## Environment Variables

| # | Variable | Description | Required |
|---|---|---|---|
| **OpenRouter** | | | |
| 1 | `OPENROUTER_API_KEY` | API key from openrouter.ai/keys | ✅ |
| 2 | `OPENROUTER_BASE_URL` | `https://openrouter.ai/api/v1` | ✅ |
| 3 | `OPENROUTER_SITE_URL` | Site URL for OpenRouter rankings | ✅ |
| 4 | `OPENROUTER_APP_NAME` | App name for OpenRouter | ✅ |
| **Supabase** | | | |
| 5 | `SUPABASE_URL` | Postgres connection string (asyncpg) | ✅ |
| 6 | `SUPABASE_URL_HTTP` | HTTP URL for Storage + Auth SDK | ✅ |
| 7 | `SUPABASE_SERVICE_KEY` | `service_role` key | ✅ |
| 8 | `SUPABASE_ANON_KEY` | Anonymous key (safe for frontend) | ✅ |
| **Next.js Public** | | | |
| 9 | `NEXT_PUBLIC_SUPABASE_URL` | Supabase HTTP URL | ✅ |
| 10 | `NEXT_PUBLIC_SUPABASE_ANON_KEY` | Anon key for browser | ✅ |
| 11 | `NEXT_PUBLIC_APP_URL` | App URL (`http://localhost:3000`) | ✅ |
| 12 | `NEXT_PUBLIC_API_URL` | API URL (`http://localhost:8000`) | ✅ |
| **Evolution API** | | | |
| 13 | `EVOLUTION_API_URL` | Self-hosted Evolution API URL | ✅ |
| 14 | `EVOLUTION_API_KEY` | Evolution API key | ✅ |
| 15 | `WHATSAPP_INSTANCE` | Instance name (e.g. `gulfagent`) | ✅ |
| **Redis** | | | |
| 16 | `REDIS_URL` | `redis://localhost:6379` | ✅ |
| **Stripe** | | | |
| 17 | `STRIPE_SECRET_KEY` | Stripe secret key | ✅ |
| 18 | `STRIPE_WEBHOOK_SECRET` | Webhook signing secret | ✅ |
| 19 | `STRIPE_PRICE_BASIC` | Price ID for Basic (AED 150) | ✅ |
| 20 | `STRIPE_PRICE_PRO` | Price ID for Pro (AED 500) | ✅ |
| **HyperPay** | | | |
| 21 | `HYPERPAY_ENTITY_ID` | HyperPay merchant entity | ❌ |
| 22 | `HYPERPAY_ACCESS_TOKEN` | HyperPay access token | ❌ |
| 23 | `HYPERPAY_BASE_URL` | HyperPay API base URL | ❌ |
| **BNPL** | | | |
| 24 | `TABBY_API_KEY` | Tabby API key | ❌ |
| 25 | `TABBY_BASE_URL` | Tabby API base URL | ❌ |
| 26 | `TAMARA_API_KEY` | Tamara API key | ❌ |
| 27 | `TAMARA_BASE_URL` | Tamara API base URL | ❌ |
| **Other** | | | |
| 28 | `LANGUAGE_DETECTION_ENABLED` | `true` to enable Arabic detection | ❌ |

---

## API Endpoints

### Tasks
| Method | Endpoint | Description | Rate Limit |
|---|---|---|---|
| `POST` | `/api/tasks` | Create a new task | 10/min |
| `GET` | `/api/tasks` | List user's tasks (paginated) | 30/min |
| `GET` | `/api/tasks/{id}` | Get task status + result | 30/min |
| `GET` | `/api/tasks/stream` | SSE live task updates | 30/min |

### Automations
| Method | Endpoint | Description | Rate Limit |
|---|---|---|---|
| `POST` | `/api/automations` | Create automation with cron | 10/min |
| `GET` | `/api/automations` | List user's automations | 30/min |
| `GET` | `/api/automations/{id}` | Get automation details | 30/min |
| `PATCH` | `/api/automations/{id}` | Update/pause/resume | 10/min |
| `DELETE` | `/api/automations/{id}` | Delete automation | 10/min |

### Skills Marketplace
| Method | Endpoint | Description | Rate Limit |
|---|---|---|---|
| `POST` | `/api/skills/seed` | Seed skill templates | 10/min |
| `GET` | `/api/skills` | List available skills | 30/min |
| `GET` | `/api/skills/mine` | List activated skills | 30/min |
| `POST` | `/api/skills/{slug}/activate` | Activate a skill | 10/min |
| `DELETE` | `/api/skills/{slug}/deactivate` | Deactivate a skill | 10/min |

### Billing
| Method | Endpoint | Description | Rate Limit |
|---|---|---|---|
| `POST` | `/api/billing/setup` | Create Stripe products/prices | 10/min |
| `POST` | `/api/billing/checkout` | Create checkout session | 10/min |
| `POST` | `/api/billing/portal` | Stripe customer portal | 10/min |

### Approvals
| Method | Endpoint | Description | Rate Limit |
|---|---|---|---|
| `GET` | `/api/approvals/pending` | List pending approvals | 30/min |
| `POST` | `/api/approvals/{id}/decide` | Approve or deny | 10/min |

### Users
| Method | Endpoint | Description | Rate Limit |
|---|---|---|---|
| `GET` | `/api/users/me` | Get user profile | 30/min |
| `PATCH` | `/api/users/me/phone` | Link WhatsApp phone | 10/min |
| `PATCH` | `/api/users/me/language` | Set language (en/ar) | 10/min |

### Usage
| Method | Endpoint | Description | Rate Limit |
|---|---|---|---|
| `GET` | `/api/usage` | Monthly usage summary | 30/min |

### Webhooks
| Method | Endpoint | Description | Rate Limit |
|---|---|---|---|
| `POST` | `/api/webhooks/whatsapp` | WhatsApp message receiver | — |
| `POST` | `/api/webhooks/whatsapp/register` | Register webhook with Evolution | — |
| `GET` | `/api/webhooks/whatsapp/status` | WhatsApp instance status | — |
| `POST` | `/api/webhooks/stripe` | Stripe event receiver | — |

### Admin
| Method | Endpoint | Description | Rate Limit |
|---|---|---|---|
| `GET` | `/api/admin/orchestrator/status` | Model orchestrator stats | 30/min |
| `POST` | `/api/admin/orchestrator/test` | Test model routing | 10/min |

### System
| Method | Endpoint | Description | Rate Limit |
|---|---|---|---|
| `GET` | `/health` | Health check | — |
| `GET` | `/` | Root redirect | — |
| `GET` | `/docs` | Swagger UI | — |
| `GET` | `/redoc` | ReDoc UI | — |

---

## Deployment

### Backend — Railway (Dockerfile)
```bash
# Deployment is handled via railway.toml
# Build: docker build -f backend/Dockerfile
# Start: uvicorn main:app --host 0.0.0.0 --port 8000
# Health: GET /health
```

### Frontend — Vercel (Next.js SSR)
```bash
# Connect to Vercel with env vars from .env.example
# Framework preset: Next.js
# Build command: npm run build
# Output: .next
```

---

## Screenshots

| Dashboard | Task Feed | Skills Marketplace |
|---|---|---|
| ![Dashboard](https://placehold.co/600x400/0A0A0A/FFFFFF?text=Dashboard) | ![Tasks](https://placehold.co/600x400/0A0A0A/FFFFFF?text=Task+Feed) | ![Skills](https://placehold.co/600x400/0A0A0A/FFFFFF?text=Skills) |

| WhatsApp | Approvals | Settings |
|---|---|---|
| ![WhatsApp](https://placehold.co/600x400/0A0A0A/FFFFFF?text=WhatsApp+Interface) | ![Approvals](https://placehold.co/600x400/0A0A0A/FFFFFF?text=Approval+Flow) | ![Settings](https://placehold.co/600x400/0A0A0A/FFFFFF?text=Settings) |

---

## Pricing

| Tier | Price | Credits/mo | Limits |
|---|---|---|---|
| **Basic** | AED 150/mo | 5,000 | 50 tasks, 5 automations |
| **Pro** | AED 500/mo | 20,000 | 200 tasks, unlimited automations, API access |
| **Enterprise** | Custom | Custom | Air-gapped, on-prem, SLA |

- 1 credit = 1 simple task action
- Complex browser tasks = 50–200 credits
- Overage: AED 1 per 100 credits

---

## License

MIT © 2025 ModelNorth Ventures

---

## Links

- [Architecture Documentation](./ARCHITECTURE.md)
- [Changelog](./CHANGELOG.md)
- [Task Roadmap](./TASKS.md)
- [AI Context (CLAUDE.md)](./CLAUDE.md)