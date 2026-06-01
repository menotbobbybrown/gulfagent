# GulfAgent — TASKS.md

90-day build roadmap. Work phase by phase. Do not skip ahead.
Mark tasks ✅ when complete.

---

## PHASE 1 — Foundation (Week 1-2)
> Goal: Auth working, task submission working, basic agent returning results.

### Backend Setup
- [ ] T01 — Init FastAPI app with `/health` endpoint
- [ ] T02 — Connect Supabase (auth + DB) via `supabase-py`
- [ ] T03 — Create Pydantic config with all env vars
- [ ] T04 — Create DB tables: `users`, `tasks`, `usage`
- [ ] T05 — `POST /api/tasks` — create task, save to DB, return task_id
- [ ] T06 — `GET /api/tasks/{id}` — fetch task status + result
- [ ] T07 — `GET /api/tasks` — list user's tasks (paginated)
- [ ] T08 — Basic LangGraph pipeline — takes prompt, returns Claude response
- [ ] T09 — Usage tracker — deduct credits after task, check limit before

### Frontend Setup
- [ ] T10 — Init Next.js 14 with Tailwind, dark theme (#0A0A0A background)
- [ ] T11 — Supabase Auth — magic link login/signup page
- [ ] T12 — Protected route middleware
- [ ] T13 — Dashboard shell — sidebar nav, header with usage bar
- [ ] T14 — TaskInput component — textarea + submit button
- [ ] T15 — TaskFeed component — list of tasks with status badges
- [ ] T16 — Connect TaskInput to `POST /api/tasks`
- [ ] T17 — SSE endpoint `GET /api/tasks/stream` — live status updates
- [ ] T18 — TaskFeed subscribes to SSE, updates in real-time

### Infra
- [ ] T19 — docker-compose.yml (FastAPI + Next.js + Redis + Postgres)
- [ ] T20 — .env.example with all required vars documented

---

## PHASE 2 — Browser Agent + WhatsApp (Week 3-4)
> Goal: Agent can browse the web. User can submit tasks via WhatsApp.

### Browser Agent
- [ ] T21 — Install browser-use, wrap in `BrowserAgent` class
- [ ] T22 — `browser_agent.py` — `run(prompt)` → returns result + screenshots
- [ ] T23 — Store screenshots in Supabase Storage, link to task
- [ ] T24 — Add browser tool to LangGraph pipeline
- [ ] T25 — Task type classifier — route to browser vs simple LLM
- [ ] T26 — Dashboard: task detail page showing screenshots + steps taken

### Approval Flow
- [ ] T27 — `approvals` table — task_id, type, payload, expires_at, decision
- [ ] T28 — Before destructive actions: create approval record, pause agent
- [ ] T29 — `GET /api/approvals/pending` — list pending approvals
- [ ] T30 — `POST /api/approvals/{id}/decide` — approve or deny
- [ ] T31 — ApprovalModal component in dashboard — shows what agent wants to do
- [ ] T32 — Auto-deny after 5 min timeout (BullMQ delayed job)

### WhatsApp
- [ ] T33 — Evolution API setup, webhook registration
- [ ] T34 — `POST /api/webhooks/whatsapp` — receive incoming messages
- [ ] T35 — Parse incoming message → create task → execute
- [ ] T36 — Send result back to user via WhatsApp
- [ ] T37 — Approval via WhatsApp — "Reply Y to approve, N to deny"
- [ ] T38 — Arabic message detection → route to Qwen3 via Ollama
- [ ] T39 — User phone number linked to Supabase user account

---

## PHASE 3 — Automations + Skills (Week 5-6)
> Goal: Scheduled tasks running. Skills marketplace live.

### Automations
- [ ] T40 — `automations` table — cron, prompt, active, last_run, next_run
- [ ] T41 — `POST /api/automations` — create automation
- [ ] T42 — BullMQ repeatable jobs — register cron on creation
- [ ] T43 — `PATCH /api/automations/{id}` — pause/resume/update
- [ ] T44 — `DELETE /api/automations/{id}` — remove + cancel BullMQ job
- [ ] T45 — Automations page — list, create, pause, delete UI
- [ ] T46 — Cron builder UI — human-readable schedule picker
- [ ] T47 — WhatsApp delivery of automation results at completion

### Skills Marketplace
- [ ] T48 — `skills` table — seed with 10 GCC-specific templates
- [ ] T49 — `user_skills` table — activated skills per user
- [ ] T50 — Skills page — grid of available skills with categories
- [ ] T51 — One-click activate skill → creates automation pre-filled
- [ ] T52 — Skill categories: Research, E-commerce, Government, Finance, HR

### Seed Skills (build these 10)
- [ ] T53 — "Daily Gulf News Briefing" → scrape Gulf News + Zawya, WhatsApp summary
- [ ] T54 — "Price Monitor" → watch product on Noon/Amazon.ae, alert on drop
- [ ] T55 — "Lead Researcher" → company name in → org info, contacts, news out
- [ ] T56 — "Gmail to Linear" → scan Gmail for bugs/issues, create Linear tickets
- [ ] T57 — "Weekly Competitor Intel" → monitor 3 URLs, summarize changes
- [ ] T58 — "DubaiNow Reminder" → check fine/renewal status, alert if due
- [ ] T59 — "LinkedIn Outreach" → draft personalized message for prospect
- [ ] T60 — "Mag 7 Stock Brief" → daily pre-market prices via WhatsApp
- [ ] T61 — "Tender Monitor" → scan government portals for new tenders
- [ ] T62 — "WhatsApp Report" → compile week's task results into PDF, send

---

## PHASE 4 — Billing + Polish (Week 7-8)
> Goal: Stripe live. Usage limits enforced. Production ready.

### Billing
- [ ] T63 — Stripe products + prices setup (Basic AED 150, Pro AED 500)
- [ ] T64 — `POST /api/billing/checkout` — create Stripe checkout session
- [ ] T65 — `POST /api/webhooks/stripe` — handle subscription events
- [ ] T66 — Subscription status synced to Supabase `users` table
- [ ] T67 — Credit limits enforced — 403 with upgrade prompt when exceeded
- [ ] T68 — Usage page — credits used, tasks run, automations active
- [ ] T69 — Low credits alert — WhatsApp message at 20% remaining
- [ ] T70 — Upgrade flow — in-app modal → Stripe checkout

### Production Polish
- [ ] T71 — Error boundaries in all React pages
- [ ] T72 — All API errors return structured `{ error: { code, message } }`
- [ ] T73 — Rate limiting on all API routes (slowapi)
- [ ] T74 — Supabase RLS policies — users can only see own data
- [ ] T75 — Task timeout — kill browser agent after 5 min, mark as failed
- [ ] T76 — Retry logic — failed tasks retry once automatically
- [ ] T77 — Langfuse integration — observability for all LLM calls
- [ ] T78 — Sentry integration — error tracking frontend + backend
- [ ] T79 — nginx config — SSL, reverse proxy, gzip
- [ ] T80 — deploy.sh — one-command deploy to Hetzner via Dokploy

---

## PHASE 5 — GCC Localization (Week 9-10)
> Goal: Arabic working. Regional connectors live.

- [ ] T81 — Arabic UI — RTL layout toggle in dashboard
- [ ] T82 — Qwen3-8B via Ollama — fully tested Arabic task pipeline
- [ ] T83 — Language detection middleware — auto-route Arabic to Qwen3
- [ ] T84 — Careem connector — book ride via agent
- [ ] T85 — Noon connector — search products, get prices
- [ ] T86 — Talabat connector — menu browse, order status
- [ ] T87 — DubaiNow connector — check fines, renewals
- [ ] T88 — HyperPay integration — AED payment processing
- [ ] T89 — Tabby/Tamara — BNPL options in billing
- [ ] T90 — Arabic onboarding flow — Welcome message in Arabic via WhatsApp

---

## Notes for CTO

- Start with T01-T09 backend, then T10-T18 frontend in parallel
- browser-use requires Playwright — `playwright install chromium` in Dockerfile
- Evolution API needs a WhatsApp number — use a dedicated SIM
- All LangGraph nodes must catch exceptions and update task status to "failed"
- Test approval flow manually before connecting to WhatsApp
- Stripe test mode first — switch to live after first real user
- Hetzner CX32 (4 vCPU, 8GB RAM) is minimum for browser agent
