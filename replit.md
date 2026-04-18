# FreelanceBot v15.0 — Self-Learning Autonomous Freelance Agent

## Overview
A 24/7 Python async service that continuously monitors 7 freelance platforms for jobs
related to Viber bots, webhooks, and automation. It finds relevant orders, generates
personalized proposals via DeepSeek/OpenAI, autonomously executes accepted orders,
and systematically self-improves through Five Learning Pillars after every project.

**v15.0 Additions (Переписка tab + Tablet UI):**
- **"💬 Переписка" tab** in dashboard — real Kwork inbox via web-scrape (KWORK_SESSION_COOKIE) + FL.ru inbox via session login (FL_USERNAME/FL_PASSWORD)
- **`/api/messages`** — scrapes `kwork.ru/inbox`, parses threads, fetches last message text, sender, date, unread status; shows direct links to open on Kwork
- **`/api/reply-message`** — sends reply to Kwork thread via POST with CSRF token
- **Unread badge** on Переписка tab; auto-refreshes every 3 min in background
- **Tablet-responsive CSS** — `@media(max-width:900px)` breakpoint added: tabs scroll horizontally, stat grid 2-col, smaller fonts, stacked controls
- **Zero fake data** — DB is clean; all mock job generators neutered

**v14.0 Additions (Telegram Control Panel + Client Messaging + Platform Promotion):**
- **TelegramCommandBot** — interactive control panel via Telegram slash-commands:
  - `/status` — bot state (paused/active, job counts, avg score, healthy platforms)
  - `/jobs` — last 7 orders with emoji status + score
  - `/pause` / `/resume` — pause/resume the main search cycle (`_BOT_PAUSED` global)
  - `/stats` — win-rate + conversion by platform
  - `/promote` — manual trigger of promotion cycle (Kwork ranking + FL.ru activity)
  - `/help` — full command list
  - Polls `getUpdates` every 15 seconds; only responds to configured `TELEGRAM_CHAT_ID`
- **`_BOT_PAUSED` global flag** — `main_cycle()` checks this flag at start and skips if paused
- **KworkManager inbox monitoring** (v14.0):
  - `check_messages()` — fetches unread messages from Kwork API inbox
  - `auto_reply_message()` — LLM-generated professional reply (2-4 sentences)
  - `check_and_reply_all()` — combined loop; sends Telegram notification with count
- **FLruManager full suite** (v14.0):
  - `setup_profile_full()` — LLM-generated bio (200-300 words RU) + skills tags via HTML form
  - `check_messages()` — HTML-scrapes FL.ru inbox for unread message blocks
  - `auto_reply_message()` — LLM reply, posted via FL.ru form API
  - `check_and_reply_all()` — loop + Telegram notification
  - `promote_account()` — activity signals: refresh profile page, browse Python projects, visit dashboard — updates "last seen" in FL.ru search
- **Scheduler jobs (10 total):**
  - `platform_messages` — every 5 min (Kwork + FL.ru inbox check + auto-reply)
  - `flru_promotion` — every 4 hours (FL.ru activity signals)
  - All previous 8 jobs retained
- **Startup** — `telegram_cmd_bot.start()` called before `main_cycle()`; startup Telegram message updated to v14.0 listing all 10 jobs
- **Self-Test** — 22/22 tests pass (tests 20=TelegramCommandBot, 21=KworkInbox, 22=FLruV14)

**v13.0 Additions (Next.js / TypeScript / Browser Automation — full JS/TS stack):**
- **3 new project types** (total: 29):
  - `nextjs_app` — Next.js 14 App Router + TypeScript strict + Tailwind CSS + multi-stage Docker (node:20-alpine)
  - `browser_automation` — Playwright/Puppeteer Node.js scripts (async/await, env config, retry logic, screenshot on error)
  - `typescript_api` — Express + TypeScript + Zod + Winston + JWT + ESLint + multi-stage Docker (node:20-alpine)
- **TSStaticAnalyzer** — JS/TS equivalent of PylintStaticAnalyzer. Heuristic checks (async/await, try/catch, process.env, hardcoded secrets, package.json, tsconfig strict). Tries `tsc --noEmit` when available. Returns score 0-10.
- **StaticAnalysisFeedbackLoop** updated — routes JS/TS types to TSStaticAnalyzer, Python types to PylintStaticAnalyzer
- **AnalystAgent** updated — new keyword detection: "next.js", "playwright", "puppeteer", "nestjs", "typescript api"
- **Keywords** expanded — typescript, next.js, playwright, puppeteer, nestjs, etc.
- **TesterAgent** — new `_DEFAULT_TESTS` templates for all 3 types (file existence, TypeScript types, env config, error handling, health endpoints)
- **TesterAgent.run()** — `_NO_SYNTAX` / `_NO_EXEC` extended: JS/TS types skip Python syntax check and execution loop
- **DeploymentAgent** — new Dockerfiles for nextjs_app (3-stage: deps→builder→runner) and typescript_api (2-stage: builder→runner)
- **Self-Test** — 19/19 tests pass (tests 18=TSStaticAnalyzer, 19=new project types)

**v12.0 Additions (Visual Debugging + Live Deployment — closing the Devin gap):**
- **VisualDebugAgent** — Generates a rich, self-contained `visual_preview.html` for every project (dark GitHub-style theme, code cards, quality/security scores, iframe embed for landing pages). After deployment, uses WordPress mshots API to take a real screenshot of the live URL and sends it to Telegram as a photo attachment.
- **LiveDeploymentAgent** — Actually deploys generated projects to hosting providers:
  - **HTML/landing pages** → Vercel API v13 (if `VERCEL_TOKEN` set) or Netlify zip API (if `NETLIFY_TOKEN` set)
  - **Python bots/apps** → Render.com REST API (if `RENDER_API_KEY` set), free web service tier
  - **No tokens** → always generates `render.yaml` + `Procfile` + `fly.toml` in the project package + detailed instructions in `DELIVERY.md`
- **Pipeline order**: `DeploymentAgent` → `LiveDeploymentAgent` → `PackagerAgent` → `VisualDebugAgent` → `DeliveryBriefAgent`
- **report.json** — now includes `live_url`, `deploy_provider`, `preview_screenshot_url`
- **Telegram completion message** — shows live URL and deploy provider (or "инструкции в DELIVERY.md" if no tokens)
- **Config** — 3 new optional secrets: `RENDER_API_KEY`, `VERCEL_TOKEN`, `NETLIFY_TOKEN`
- **AgentContext** — 3 new fields: `live_url`, `preview_screenshot_url`, `deploy_provider`
- **Self-Test** — 17/17 tests pass on startup (tests 16=VisualDebug, 17=LiveDeploy)

**v10.4 Additions (Superior Code Generation Pipeline):**
- **PylintStaticAnalyzer** — runs pylint on every generated file in a subprocess. Returns score 0-10 + structured issue list (Error/Warning/Refactor categories). pylint installed globally.
- **StaticAnalysisFeedbackLoop** — after `ExecutionRefinementLoop` clears runtime errors, runs pylint and feeds issues back to LLM for targeted fix (2 rounds, target ≥ 7.0/10). Devin doesn't have this — it's our genuine advantage.
- **pytest runner** — `TesterAgent._run_tests_sync` upgraded from `python -m unittest` to `pytest -v --tb=short`. Richer output (diffs, line numbers, assertion detail) feeds much better into LLM micro-fix prompts. Falls back to unittest if pytest unavailable in temp env.
- **Pylint score in Reviewer** — `ReviewerAgent` receives objective pylint score alongside LLM score for composite review decision.
- **Self-Test Result** — 14/14 tests pass on startup

**v10.3 Additions (Persistent Memory + Real Platform Access):**
- **Persistent Learning Memory** — All 4 self-learning engines now survive process restarts via SQLite `learning_state` table:
  - `BayesianStrategyEngine` saves Beta(α,β) beliefs per platform×variant on every `update()`
  - `HebbianPatternMemory` saves full weight matrix + freq counts on every `learn()`
  - `EloPatternRating` saves all pattern ratings on every `update()`
  - `PoincareRecurrenceDetector` saves error window + recurrences on every `record()`
  - `load_persistent_states()` called at startup restores all states before first cycle runs
- **Real Platform Scrapers (3 fixed):**
  - **Upwork** — Real RSS feed (`httpx` GET, regex XML parser) with mock fallback
  - **Weblancer** — Real HTTP scraping with regex HTML parser extracting job cards and budgets
  - **Kwork** — Fixed HTML parser: extracts `/projects/<id>-<slug>` cards with title + budget
  - **FL.ru** — Enhanced parser: now extracts budgets (`от X руб`) + adds `content_hash` to all jobs
- **Test 13** — New self-test verifies SQLite round-trip + all 4 engine attributes + `learning_state` table existence
- **Self-Test Result** — 13/13 tests pass on startup

**v7.0 Additions:**
- **HumanExpertGate** — Telegram-based human expert verification before every client delivery. Expert can approve, request fixes with feedback, or skip. Timeout auto-approves. Gracefully degrades to auto-approve when Telegram not configured.
- **ReputationAgent** — Tracks win/loss outcomes per platform (FL.ru, Kwork special dynamics), computes bid multipliers based on rating (1.15x premium for 4.8+ rating), injects platform-specific hints into proposals.
- **26 Project Types** — Added `universal`, `mobile_app`, `game`, `design_task`, `test_automation`, `devops` to the existing 20 types.
- **Production Self-Test** — 11-check suite runs on startup, verifies all system components.
- **Weekly Reputation Report** — Scheduled Monday 09:00 UTC.
- **v7.0 Outcome Tracking** — Every completed project records reputation outcome per platform with response time metrics.

**v8.0 Additions:**
- **ProfilePortfolioAgent** — Fully autonomous profile and portfolio manager for FL.ru and Kwork:
  - After each successful delivery (score ≥ 8.0): generates a standalone HTML showcase page with code preview, quality scores, and project metadata
  - Maintains portfolio DB (portfolio_entries table) with featured/non-featured classification
  - Rebuilds `deliverables/showcase/index.html` gallery after every project — visual catalog with quality badges
  - Weekly AI-optimized bio generation: LLM crafts platform-specific profile descriptions using project history, win rates, and specialization stats
  - Platform-specific tone: FL.ru (reliability, speed, examples) vs Kwork (fixed packages, guarantees)
  - Posts bio to FL.ru/Kwork automatically when credentials are configured
  - Scheduled Monday 07:30 UTC optimization cycle
- **7 Scheduled Jobs** — all active: search_cycle, execution_queue, learning_cycle, weekly_learning_report, weekly_report, weekly_reputation_report, weekly_portfolio_optimization

## Tech Stack
- **Language**: Python 3.11
- **Async Runtime**: asyncio + APScheduler 3.10.4
- **HTTP Client**: httpx 0.27.0
- **Database**: SQLite (file: `jobs.db`)
- **LLM**: OpenAI API (optional; mock proposals used when key not set)
- **Config**: python-dotenv 1.0.0

## Project Structure
```
main.py           — Single-file service (all modules inline)
requirements.txt  — Python dependencies
.env.example      — Template for environment variables
service.log       — Runtime log (auto-created)
jobs.db           — SQLite database (auto-created)
```

## Platforms Monitored
| Platform     | Method           | Notes                              |
|--------------|------------------|------------------------------------|
| Upwork       | API / mock       | Requires UPWORK_ACCESS_TOKEN       |
| Freelancer   | Public REST API  | Works without token                |
| Fiverr       | Mock             | Real API requires partner approval |
| PeoplePerHour| Mock             | API requires approval              |
| Kwork        | HTTP scraping    | Russian platform; seller via KworkManager |
| Weblancer    | Mock             | Russian platform                   |
| FL.ru        | HTTP scraping    | Russian platform; seller via FLruManager  |

## Seller Account Managers
| Manager       | Platform | Capabilities                                    |
|---------------|----------|-------------------------------------------------|
| KworkManager  | Kwork.ru | Auth via mobile API, profile update, create kvorki (gigs) |
| FLruManager   | FL.ru    | CSRF-aware login, profile update, proposal submission |

## Configuration (via environment variables)
| Variable               | Default             | Description                          |
|------------------------|---------------------|--------------------------------------|
| SQLITE_DB              | `jobs.db`           | SQLite database file path            |
| DEEPSEEK_API_KEY       | (empty)             | DeepSeek key (priority 1 for LLM)   |
| OPENROUTER_API_KEY     | (empty)             | OpenRouter key (priority 2 for LLM) |
| OPENAI_API_KEY         | (empty)             | OpenAI key (priority 3 / fallback)  |
| LLM_MODEL              | auto-detected       | Override model name                  |
| SEARCH_INTERVAL_MINUTES| 20                  | How often to run search              |
| MIN_BUDGET             | 50.0                | Minimum USD budget filter            |
| TELEGRAM_BOT_TOKEN     | (empty)             | For Telegram notifications           |
| TELEGRAM_CHAT_ID       | (empty)             | Telegram chat/channel ID             |
| LOG_LEVEL              | INFO                | DEBUG / INFO / WARNING / ERROR       |
| KWORK_USERNAME         | (empty)             | Kwork login (email or username)      |
| KWORK_PASSWORD         | (empty)             | Kwork password                       |
| KWORK_SESSION_COOKIE   | (empty)             | **Alternative**: paste cookie string from browser DevTools (F12 → Application → Cookies → kwork.ru). Bypasses QRATOR anti-bot WAF. Format: `kwork_session=abc123; token=xyz` |
| FL_USERNAME            | (empty)             | FL.ru login (email or username)      |
| FL_PASSWORD            | (empty)             | FL.ru password                       |
| RENDER_API_KEY         | (empty)             | **v12.0** Render.com API key → [dashboard.render.com/u/settings#api-keys](https://dashboard.render.com/u/settings#api-keys). Enables auto-deploy Python bots/apps on Render free tier. Without it — `render.yaml` + `fly.toml` are always generated in the project package. |
| VERCEL_TOKEN           | (empty)             | **v12.0** Vercel token → [vercel.com/account/tokens](https://vercel.com/account/tokens). Enables auto-deploy HTML/landing pages to Vercel free tier. |
| NETLIFY_TOKEN          | (empty)             | **v12.0** Netlify token → [app.netlify.com/user/applications](https://app.netlify.com/user/applications). Fallback for HTML deploy if no VERCEL_TOKEN. |

## Running the Service
```bash
python main.py
```
The service will:
1. Initialize the database (`jobs.db`)
2. Run the first search cycle immediately
3. Schedule subsequent cycles every `SEARCH_INTERVAL_MINUTES` minutes
4. Generate a weekly analytics report every Monday at 09:00 UTC

## Key Architecture Features
- **In-memory TTL cache**: avoids redundant API calls within the same window
- **Exponential backoff**: automatic retry on 429/5xx errors with jitter
- **Graceful degradation**: if a platform fails repeatedly, it's skipped until recovered
- **Proposal tracking**: all sent proposals stored in DB with outcome tracking
- **Adaptive prompts**: LLM system prompt enriched with patterns from successful proposals
- **Weekly reports**: saved as `report_YYYYMMDD.json`

## Adding Real API Credentials
Copy `.env.example` to `.env` and fill in the keys. Do NOT commit `.env`.

## Deployment
Configured as a VM (always-running) deployment: `python main.py`

## Supported Project Types (v3.1 — 11 types)
Detected by AnalystAgent from job title/description. Each type has its own LLM prompt,
fallback template, unit tests and main-file name.

| Type              | Main File    | Stack                        |
|-------------------|--------------|------------------------------|
| viber_bot         | bot.py       | Flask + viberbot             |
| telegram_bot      | bot.py       | aiogram 3.x                  |
| payment_bot       | bot.py       | aiogram + Stripe/Robokassa   |
| discord_bot       | bot.py       | discord.py                   |
| whatsapp_bot      | bot.py       | Flask + twilio               |
| landing_page      | index.html   | HTML/CSS/JS (inline)         |
| web_app           | app.py       | Flask + SQLAlchemy           |
| microservice      | app.py       | FastAPI + Pydantic           |
| automation        | main.py      | Python scripts               |
| microcontroller   | main.py      | MicroPython (ESP32/Pico)     |
| parser            | parser.py    | httpx + BeautifulSoup        |

## Version History
- v2.0: Multi-platform (7 platforms), KworkManager, FLruManager, DB
- v3.0: Self-learning engine, A/B variants, quality gate ≥6.0/10, learning tables
- v3.1: Universal pipeline — 11 project types, type-aware agents, fixed discord detection bug

## v4.0 — World-Class Features (No Analogues)

### New Intelligence Engines
| Engine           | Description                                                          |
|------------------|----------------------------------------------------------------------|
| JobScorer        | 8-signal scoring (0-100): budget, clarity, urgency, client_quality, competition, keyword_fit, recency, feasibility |
| ClientProfiler   | Language detection (RU/EN/DE/UK), tone (formal/casual/technical), urgency, budget flexibility |
| BidOptimizer     | Psychological pricing with .75/.50 endings, platform-fee-aware, complexity-adjusted |
| TimingOptimizer  | Best hour+day per platform from real data, falls back to research-based defaults |
| MarketIntelligence | Keyword frequency + avg budget tracker, hot skills identifier |
| RevenuePipeline  | Full funnel: proposal_sent → viewed → replied → negotiating → won → delivered → paid |
| LiveDashboard    | Beautiful UTF-8 box dashboard printed after every cycle |

### New DB Tables (v4.0)
- `job_scores` — multi-dimensional quality scores per job
- `timing_stats` — platform × hour × day_of_week submission performance
- `phrase_performance` — genetic phrase evolution tracking
- `revenue_pipeline` — business funnel with weighted value
- `market_intelligence` — keyword frequency + budget trends

### What Each Proposal Now Contains
- Language-aware instructions (writes in client's language automatically)
- Tone-matched writing style (formal/casual/technical)
- Urgency-adaptive framing
- Specific bid price recommendation with psychological .75/.50 ending
- Informed by successful pattern history

## v4.1 — Execution Pipeline Upgrade
- **SecurityAuditorAgent**: OWASP Top-10 static scan on generated code
- **SmartAutoFixerAgent**: Surgical auto-fixes for identified issues (up to 3 passes)
- **DeploymentAgent**: Auto-generates Dockerfile, docker-compose.yml, nginx.conf, Makefile
- **DeliveryBriefAgent**: Writes professional DELIVERY.md for clients
- **OrderOrchestrator**: Quality convergence loop (tests + score≥7 + security≥6, MAX_ITERATIONS=4)

## v4.3 — World-Class Execution Pipeline Upgrade

### OrderOrchestrator — Raised Quality Bars
- **MAX_ITERATIONS**: 4 → **5** (больше попыток достичь качества)
- **QUALITY_TARGET**: 7/10 → **8/10** (только действительно production-ready код)
- **SECURITY_TARGET**: 6.0 → **7.0** (нулевая толерантность к критическим уязвимостям)

### DeveloperAgent — Elite Prompts
- Новый `_ELITE_SYSTEM` промпт: "world-class Senior Software Engineer, zero placeholders, all edge cases handled"
- Все 11 типов получили детальные checklist-hints (10-15 обязательных требований каждый)
- User prompt теперь включает: полное ТЗ заказчика (1200 символов), полную архитектуру (800 символов)
- **max_tokens**: 2200 → **4000** (полная реализация без усечений)
- **temperature**: 0.2 → **0.15** (более детерминированный, точный код)

### TesterAgent — Deep Tests
- Все 11 типов получили 8-11 тестов вместо 4-5
- Новые проверки: нет `debug=True`, нет hardcoded tokens/secrets, /health endpoint, error handling, logging, rate limiting (parser), env validation

### ReviewerAgent — Stricter Standards
- Approved только при score ≥ 8 И tests passed (было: score≥7 ИЛИ tests passed)
- Код для ревью: 2500 → **4000** символов (полный контекст)
- В промпте: полное ТЗ + требуемые функции + security score

### SmartAutoFixerAgent — More Powerful
- Код для фиксинга: 3000 → **6000** символов
- **max_tokens**: 2500 → **4000**
- **temperature**: 0.1 → **0.05** (максимально точные исправления)
- Включает ВСЕ security issues (не только critical)

### SecurityAuditorAgent — Zero Tolerance
- Pass threshold: 5.0 → **7.0** (код с 3+ warnings не пройдёт без фикса)

### ArchitectAgent — Detailed Design
- Промпт переписан: детальная архитектура (200-250 слов), max_tokens 500 → **800**

### Fixed Bugs
- web_app fallback: `debug=True` → `debug=os.getenv("DEBUG","false").lower() == "true"`

## v5.1 — Full Spec Architecture Implementation

### 3 New Content & Data Project Types (now 20 total)
`content_writing` (content.md), `data_analysis` (analysis.py), `copywriting` (copy.md)
- Elite prompts: content_writing uses SEO/structure specialist, copywriting uses AIDA/PAS copywriter, data_analysis uses pandas + matplotlib pipeline
- Dedicated test suites for each: word-count, structure, no-placeholders (content/copy), pandas/visualization/env (data)
- Fallbacks with production-ready templates for all 3
- Markdown types skip Python syntax check and Docker generation
- `_NON_PYTHON_TYPES` set added to DeveloperAgent to handle non-Python output correctly

### ClientCommunicationAgent (v5.1 Spec: "Client Communication Agent")
4 message stages, each generating professional personalized text:
- `clarification`: Asks 2-4 clarifying questions from RequirementsDeepDive risks/edge_cases
- `progress`: Mid-project status update (features being built, ETA)
- `delivery` ← **wired into Orchestrator Phase 3**: concise, warm, lists all files + features
- `support`: Post-delivery template for follow-up
- Saves `CLIENT_MESSAGE.md` to deliverables directory alongside `DELIVERY.md`
- Language adapts to match client's job language

### NegotiationAgent (v5.1 Spec: "Bidding & Negotiation Agent")
Intelligent counter-offer analysis with 3 strategies:
- `accept`: client counter ≥ 95% of our bid
- `counter`: client between floor (70%) and bid → suggest midpoint, value-justifying message
- `hold`: client below 70% floor → firm, value-focused response
- Never reveals our floor price to client; generates professional response_message
- `analyze_counter_offer()` async method callable from platform handlers

### ConcurrentProjectManager (v5.1 Spec: "Scalability Model")
Hard limit: MAX_CONCURRENT=3 active projects simultaneously
- `can_accept_project()`: capacity check before starting any execution
- `register_project()`: tracks title, platform, start_time
- `complete_project()` / `fail_project()`: free slot, log duration/reason
- `get_status_report()`: human-readable dashboard of active projects
- Global instance `concurrent_pm` wired into OrderOrchestrator.execute()
- Deferred projects logged as DEFERRED (not lost)

### Orchestrator Pipeline Update (v5.1)
Phase 1: `Analyst → RequirementsDeepDive → Architect → [ClientCommunication clarification]`
Phase 3: `Deployment → Packager → DeliveryBrief → ClientCommunication delivery`
Concurrency: `can_accept → register → [pipeline] → complete/fail`

## v5.0 — Multi-Agent System (Full v5.0)

### 17 Project Types (6 New)
Added: `react_app`, `api_integration`, `chrome_extension`, `data_pipeline`, `cli_tool`, `crm_integration`
Updated AnalystAgent keyword detection for all 17 types (more-specific types checked first).

### 3 New Advanced Agents

**RequirementsDeepDiveAgent** (Phase 1, before ArchitectAgent):
- Sends job description to LLM for deep requirement extraction
- Produces structured JSON: `detailed_requirements` (8-15 items), `technical_stack`, `edge_cases` (4-8), `acceptance_criteria` (5-10), `key_risks`
- Output injected into DeveloperAgent prompt as dedicated sections

**MultiCriticAgent** (Phase 2, after each DeveloperAgent pass, iterations 0-1):
- 3 specialist critics run in **parallel** (asyncio.gather)
- Security Critic: OWASP, hardcoded secrets, injection, insecure defaults
- Architecture Critic: SoC, error handling, resource leaks, retry logic, scalability
- Quality Critic: naming, docstrings, magic numbers, duplication, logging
- Each outputs score/10 + issues + fixes
- Issues injected into next DeveloperAgent pass AND SmartAutoFixerAgent
- Average score < 6.0 OR > 5 issues → appended to ctx.errors for fixer

**SandboxRunnerAgent** (Phase 2, after TesterAgent, iteration 0 only):
- Writes code to temp directory with `.env` stub
- `py_compile` syntax check
- Extracts imports (AST), auto-installs missing packages via `pip install`
- Executes with 8s timeout, detects fatal runtime errors (SyntaxError, ImportError, etc.)
- Sandbox failure triggers SmartAutoFixer pass
- Skipped for frontend-only types: `landing_page`, `react_app`, `chrome_extension`

### Updated Orchestrator Pipeline
`AnalystAgent → RequirementsDeepDiveAgent → ArchitectAgent → [DeveloperAgent → MultiCriticAgent → TesterAgent → SandboxRunnerAgent (iter 0) → SecurityAuditorAgent → (SmartAutoFixerAgent if needed) → ReviewerAgent] × MAX_ITER`

### DeveloperAgent Prompt Enrichment
- `═══ ДЕТАЛЬНЫЕ ТРЕБОВАНИЯ ═══` section (12 items from RequirementsDeepDive)
- `═══ КРИТЕРИИ ПРИЁМКИ ═══` section (8 items)
- `═══ ГРАНИЧНЫЕ СЛУЧАИ ═══` section (5 edge cases)
- `═══ ЗАМЕЧАНИЯ КРИТИКОВ ═══` section (top MultiCritic issues)

### New Test Suites
All 6 new project types have 6-8 deep type-specific tests in TesterAgent._DEFAULT_TESTS.

## v4.2 — Competitive-Research-Based Proposal Intelligence
- **JobScorer v2**: 12-signal scoring (added recency decay, competition estimation, red/green flag detection)
- **7 Proposal Variants**: Added plan_first, proof_first, question_led (total: 7 openers)
- **ABTestingTracker**: Wilson score confidence intervals for statistically significant variant selection
- **Optimal length targeting**: Research-based 150-220 word targets per proposal
- **Score context in prompts**: Job score + breakdown passed into LLM for smarter framing
- **Competition-aware pricing**: Anchor pricing strategy when competition is high
- **Flag logging**: Red/green flags from JobScorer surfaced in processing logs
- **Weekly A/B report**: Statistical win-rate by variant/platform/word-count logged every Monday

## v6.0 — Five Learning Pillars + OAuth Auth (Full Self-Improvement Architecture)

### Five Learning Pillars (Compounding Intelligence)

**Pillar 1: FeedbackLoopEngine**
- Coordinates all 5 pillars after every completed project
- Automatically records quality metrics, adds to knowledge base if score ≥ 7.5, runs WinLoss analysis
- Wired into OrderOrchestrator Phase 4 (after delivery)
- Weekly learning report scheduled every Monday 08:30 UTC

**Pillar 2: PersonalizationEngine**
- Detects 6 client archetypes: tech_expert, biz_owner, budget_hunter, quality_seeker, urgency_driven, long_term_partner
- Each archetype maps to optimal proposal variants and personalization hints
- Archetype injected into proposal prompt as "ПЕРСОНАЛИЗАЦИЯ ПОД КЛИЕНТА" instruction
- Win/loss correlation tracked per archetype in `client_archetypes` DB table
- Replaces pure ε-greedy variant selection with archetype-guided selection

**Pillar 3: WinLossAnalyzer**
- LLM-powered competitive intelligence from every bid outcome
- Extracts: win_factors, loss_factors, price_assessment, positioning_gap, next_bid_adjustment, competitive_threat
- Stores patterns in `win_loss_patterns` DB table
- `get_competitive_context()` provides per-platform/type win-rate context for proposals

**Pillar 4: QualityEvolutionTracker**
- Tracks: review_score, security_score, iterations, test_passed, sandbox_passed, delivery_time_s, fixes_applied
- `check_exceeded_expectation()`: score≥9 + tests + sandbox + ≤2 iters + security≥8.5 = "⭐ exceeded"
- `get_evolution_summary()`: compares last 10 vs last 100 projects (trend analysis)
- `get_excellence_bonus()`: injects "exceed expectations" instructions when baseline score ≥ 7.5
- Stores to `quality_evolution` DB table

**Pillar 5: KnowledgeBase**
- Saves successful projects (score≥7.5) as reusable patterns
- `get_prompt_context()`: injects proven solutions section into DeveloperAgent prompt
- Shows top-3 relevant entries: title, score, reuse_count, approach summary
- `add_from_execution()`: auto-catalogs every successful delivery
- Tracks `reuse_count` per pattern; stored in `knowledge_base` DB table

### API Auth Infrastructure

**OAuthTokenManager**
- Manages OAuth 2.0 tokens for Upwork and Fiverr (Authorization Code Flow)
- Reads initial tokens from env vars: `UPWORK_ACCESS_TOKEN`, `UPWORK_REFRESH_TOKEN`, `FIVERR_ACCESS_TOKEN`
- `ensure_valid_token()`: checks expiry (5-min buffer), refreshes automatically via `refresh_token()`
- Stores refreshed tokens in `oauth_tokens` DB table for persistence across restarts
- Client credentials: `UPWORK_CLIENT_ID`, `UPWORK_CLIENT_SECRET`, `FIVERR_CLIENT_ID`, `FIVERR_CLIENT_SECRET`

**RateLimitManager**
- Per-platform request limits: Upwork(50/min), Freelancer(20), Fiverr(30), PeoplePerHour(15), Kwork(10), Weblancer(8), FL.ru(10)
- `wait_if_needed()`: respects both backoff periods and rate windows
- `record_429()`: sets backoff from Retry-After header with jitter
- `record_error()`: exponential backoff (1s × 2^attempt, max 120s) wired into BasePlatform._record_error()

### LLMService Enhancement
- New `complete()` method: generic LLM call for agents (WinLossAnalyzer, FeedbackLoop)
- Takes system/user prompts + temperature/max_tokens → returns raw string

### New DB Tables (v6.0)
| Table | Purpose |
|-------|---------|
| `knowledge_base` | Proven solution patterns (project_type, code_snippet, tags, reuse_count) |
| `win_loss_patterns` | Bid outcome analysis (outcome, bid_ratio, win/loss_factors, archetype) |
| `quality_evolution` | Per-project quality metrics (score, iterations, delivery_time, exceeded) |
| `client_archetypes` | Client archetype tracking with win correlation |
| `oauth_tokens` | OAuth token storage for Upwork/Fiverr |

### Scheduler Jobs (now 5 total)
- `search_cycle`: every 20 min — main platform monitoring loop
- `weekly_report`: Monday 09:00 UTC — business analytics report
- `execution_queue`: every 5 min — pending order execution check
- `learning_cycle`: every 3 hours — LLM insight extraction
- `weekly_learning_report`: Monday 08:30 UTC — all 5 pillars summary

## v15.8 Quality Gates (Apr 2026)
- **SpecComplianceAgent** (~line 11067): anti-hallucination ТЗ→code gate. Classifies each spec feature as implemented/partial/missing, caps review_score by compliance %, prepends [SPEC-MISSING]/[SPEC-PARTIAL] notes for SmartAutoFixer.
- **DocFetcher.fetch_github_examples** (~line 9154): top-3 starred GitHub repos per project type, README code blocks injected into ctx.doc_context before DeveloperAgent.
- **SandboxRunnerAgent._http_probe** (~line 13144): for web/api types — actually launches process, waits for port, hits /, /health, /docs, /api, /healthz. <500 = served. Marks sandbox_passed=False if web project doesn't actually serve.
- **DesignReviewAgent** (~line 11045): only for landing_page. Hard semantic checks (viewport, h1, alt, OG tags, semantic HTML) + LLM critique on visual hierarchy / conversion / copy / trust / CTA. Caps review_score on issues.
- All 4 wired into OrderOrchestrator iteration loop after CrossProviderVerifierAgent.

## v15.8 Render Deploy
- render.yaml: starter $7/mo, Frankfurt, persistent disk 1GB at /opt/render/project/src/data, healthCheckPath=/health, autoDeploy=true.
- DATA_DIR env var redirects jobs.db, deliverables/, backups/ to persistent disk.
- Repo: github.com/Arharius/flscanwork (private). Latest commit: v15.8 quality gates.
- User must: add card in Render billing → connect GitHub → New Blueprint → Apply → fill secrets.
