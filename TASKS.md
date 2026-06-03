# GulfAgent — TASKS.md

90-day build roadmap. Work phase by phase. Do not skip ahead.
Mark tasks ✅ when complete.

---

## PHASE 1 — Foundation (Week 1-2)
> Goal: Auth working, task submission working, basic agent returning results.

### Backend Setup
- [x] T01 — Init FastAPI app with `/health` endpoint
- [x] T02 — Connect Supabase (auth + DB) via `supabase-py`
- [x] T03 — Create Pydantic config with all env vars
- [x] T04 — Create DB tables: `users`, `tasks`, `usage`
- [x] T05 — `POST /api/tasks` — create task, save to DB, return task_id
- [x] T06 — `GET /api/tasks/{id}` — fetch task status + result
- [x] T07 — `GET /api/tasks` — list user's tasks (paginated)
- [x] T08 — Basic LangGraph pipeline — takes prompt, returns Claude response
- [x] T09 — Usage tracker — deduct credits after task, check limit before

### Frontend Setup
- [x] T10 — Init Next.js 14 with Tailwind, dark theme (#0A0A0A background)
- [x] T11 — Supabase Auth — magic link login/signup page
- [x] T12 — Protected route middleware
- [x] T13 — Dashboard shell — sidebar nav, header with usage bar
- [x] T14 — TaskInput component — textarea + submit button
- [x] T15 — TaskFeed component — list of tasks with status badges
- [x] T16 — Connect TaskInput to `POST /api/tasks`
- [x] T17 — SSE endpoint `GET /api/tasks/stream` — live status updates
- [x] T18 — TaskFeed subscribes to SSE, updates in real-time

### Infra
- [x] T19 — docker-compose.yml (FastAPI + Next.js + Redis + Postgres)
- [x] T20 — .env.example with all required vars documented

---

## PHASE 2 — Browser Agent + WhatsApp (Week 3-4)
> Goal: Agent can browse the web. User can submit tasks via WhatsApp.

### Browser Agent
- [x] T21 — Install browser-use, wrap in `BrowserAgent` class
- [x] T22 — `browser_agent.py` — `run(prompt)` → returns result + screenshots
- [x] T23 — Store screenshots in Supabase Storage, link to task
- [x] T24 — Add browser tool to LangGraph pipeline
- [x] T25 — Task type classifier — route to browser vs simple LLM
- [x] T26 — Dashboard: task detail page showing screenshots + steps taken

### Approval Flow
- [x] T27 — `approvals` table — task_id, type, payload, expires_at, decision
- [x] T28 — Before destructive actions: create approval record, pause agent
- [x] T29 — `GET /api/approvals/pending` — list pending approvals
- [x] T30 — `POST /api/approvals/{id}/decide` — approve or deny
- [x] T31 — ApprovalModal component in dashboard — shows what agent wants to do
- [x] T32 — Auto-deny after 5 min timeout (BullMQ delayed job)

### WhatsApp
- [x] T33 — Evolution API setup, webhook registration
- [x] T34 — `POST /api/webhooks/whatsapp` — receive incoming messages
- [x] T35 — Parse incoming message → create task → execute
- [x] T36 — Send result back to user via WhatsApp
- [x] T37 — Approval via WhatsApp — "Reply Y to approve, N to deny"
- [x] T38 — Arabic message detection → route to Qwen3 via Ollama
- [x] T39 — User phone number linked to Supabase user account

---

## PHASE 3 — Automations + Skills (Week 5-6)
> Goal: Scheduled tasks running. Skills marketplace live.

### Automations
- [x] T40 — `automations` table — cron, prompt, active, last_run, next_run
- [x] T41 — `POST /api/automations` — create automation
- [x] T42 — BullMQ repeatable jobs — register cron on creation
- [x] T43 — `PATCH /api/automations/{id}` — pause/resume/update
- [x] T44 — `DELETE /api/automations/{id}` — remove + cancel BullMQ job
- [x] T45 — Automations page — list, create, pause, delete UI
- [x] T46 — Cron builder UI — human-readable schedule picker
- [x] T47 — WhatsApp delivery of automation results at completion

### Skills Marketplace
- [x] T48 — `skills` table — seed with 10 GCC-specific templates
- [x] T49 — `user_skills` table — activated skills per user
- [x] T50 — Skills page — grid of available skills with categories
- [x] T51 — One-click activate skill → creates automation pre-filled
- [x] T52 — Skill categories: Research, E-commerce, Government, Finance, HR

### Seed Skills (build these 10)
- [x] T53 — "Daily Gulf News Briefing" → scrape Gulf News + Zawya, WhatsApp summary
- [x] T54 — "Price Monitor" → watch product on Noon/Amazon.ae, alert on drop
- [x] T55 — "Lead Researcher" → company name in → org info, contacts, news out
- [x] T56 — "Gmail to Linear" → scan Gmail for bugs/issues, create Linear tickets
- [x] T57 — "Weekly Competitor Intel" → monitor 3 URLs, summarize changes
- [x] T58 — "DubaiNow Reminder" → check fine/renewal status, alert if due
- [x] T59 — "LinkedIn Outreach" → draft personalized message for prospect
- [x] T60 — "Mag 7 Stock Brief" → daily pre-market prices via WhatsApp
- [x] T61 — "Tender Monitor" → scan government portals for new tenders
- [x] T62 — "WhatsApp Report" → compile week's task results into PDF, send

---

## PHASE 4 — Billing + Polish (Week 7-8)
> Goal: Stripe live. Usage limits enforced. Production ready.

### Billing
- [x] T63 — Stripe products + prices setup (Basic AED 150, Pro AED 500)
- [x] T64 — `POST /api/billing/checkout` — create Stripe checkout session
- [x] T65 — `POST /api/webhooks/stripe` — handle subscription events
- [x] T66 — Subscription status synced to Supabase `users` table
- [x] T67 — Credit limits enforced — 403 with upgrade prompt when exceeded
- [x] T68 — Usage page — credits used, tasks run, automations active
- [x] T69 — Low credits alert — WhatsApp message at 20% remaining
- [x] T70 — Upgrade flow — in-app modal → Stripe checkout

### Production Polish
- [x] T71 — Error boundaries in all React pages
- [x] T72 — All API errors return structured `{ error: { code, message } }`
- [x] T73 — Rate limiting on all API routes (slowapi)
- [x] T74 — Supabase RLS policies — users can only see own data
- [x] T75 — Task timeout — kill browser agent after 5 min, mark as failed
- [x] T76 — Retry logic — failed tasks retry once automatically
- [x] T77 — Langfuse integration — observability for all LLM calls
- [x] T78 — Sentry integration — error tracking frontend + backend
- [x] T79 — nginx config — SSL, reverse proxy, gzip
- [x] T80 — deploy.sh — one-command deploy to Hetzner via Dokploy

---

## PHASE 5 — GCC Localization (Week 9-10)
> Goal: Arabic working. Regional connectors live.

- [x] T81 — Arabic UI — RTL layout toggle in dashboard
- [x] T82 — Qwen3-8B via Ollama — fully tested Arabic task pipeline
- [x] T83 — Language detection middleware — auto-route Arabic to Qwen3
- [x] T84 — Careem connector — book ride via agent
- [x] T85 — Noon connector — search products, get prices
- [x] T86 — Talabat connector — menu browse, order status
- [x] T87 — DubaiNow connector — check fines, renewals
- [x] T88 — HyperPay integration — AED payment processing
- [x] T89 — Tabby/Tamara — BNPL options in billing
- [x] T90 — Arabic onboarding flow — Welcome message in Arabic via WhatsApp

---

## PHASE 7 — E2B Sandbox + Multi-Agent System
> Goal: Secure code execution, intelligent task delegation, WhatsApp file processing.

- [x] P1 — E2B SandboxExecutor with execute_code, execute_with_files, execute_data_analysis
- [x] P2 — AgentManager with BrowserAgent, CodeAgent, ResearchAgent delegation
- [x] P3 — code_execution task type in model_orchestrator (→ kimi-k2.6)
- [x] P4 — WhatsApp media message handling (CSV, Excel, PDF, images)
- [x] P5 — 5 new skills: Data Analyst, Excel Automator, PDF Summarizer, Script Runner, Market Data
- [x] P6 — Destructive code pattern detection + approval flow
- [x] P7 — E2B_API_KEY env var + e2b-code-interpreter dependency
- [x] P8 — execute_code_tool in tool_registry
- [x] P9 — Docs updated for new features

---

## Notes for CTO

- Start with T01-T09 backend, then T10-T18 frontend in parallel
- browser-use requires Playwright — `playwright install chromium` in Dockerfile
- Evolution API needs a WhatsApp number — use a dedicated SIM
- All LangGraph nodes must catch exceptions and update task status to "failed"
- Test approval flow manually before connecting to WhatsApp
- Stripe test mode first — switch to live after first real user
- Hetzner CX32 (4 vCPU, 8GB RAM) is minimum for browser agent
