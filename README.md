# Orbit AI Assistant

Multi-agent AI assistant for **Orbit Engineering Solutions**, an Industrial AI Platform based in Tunisia. Orbit AI handles commercial inquiries, email management, calendar planning, and automated reply generation through a coordinated multi-agent architecture, with a full authentication system, per-client token quotas, and an admin dashboard for real-time monitoring.

---

## Table of Contents

1. [Overview](#overview)
2. [Architecture](#architecture)
3. [Tech Stack](#tech-stack)
4. [Project Structure](#project-structure)
5. [Getting Started](#getting-started)
6. [Configuration](#configuration)
7. [Authentication & Authorization](#authentication--authorization)
8. [Agents](#agents)
9. [RAG (Retrieval-Augmented Generation)](#rag-retrieval-augmented-generation)
10. [Token Usage & Quota System](#token-usage--quota-system)
11. [Admin Dashboard](#admin-dashboard)
12. [Database Schema (Key Tables)](#database-schema-key-tables)
13. [API Reference](#api-reference)
14. [Known Limitations & Roadmap](#known-limitations--roadmap)
15. [Security Notes](#security-notes)

---

## Overview

Orbit AI Assistant is a chat-based assistant that:

- Qualifies commercial leads and answers product/pricing questions as a knowledgeable sales rep (Commercial Agent).
- Reads and classifies a connected Gmail inbox (Email Agent).
- Reviews a connected Google Calendar and produces a daily briefing with conflict detection (Planning Agent).
- Drafts email replies — either from an existing inbox message or from a raw instruction — using a business or personal persona (Reply Agent).
- Routes every user message to the right specialized agent automatically (Orchestrator Agent).

The system supports both **guest trial** access (limited, unauthenticated) and **authenticated** access with persistent memory, per-plan token quotas, and Google OAuth integration for Gmail/Calendar.

---

## Architecture

```
                         USER
                          |
                          v
                 OrchestratorAgent
        (3-layer routing: jargon allowlist regex
         -> deterministic keyword regex -> LLM classifier)
                          |
      -----------------------------------------------
      |            |             |             |
      v            v             v             v
 Commercial      Email        Planning        Reply
   Agent         Agent         Agent          Agent
```

All agents inherit from a shared `BaseAgent`, which centralizes:

- LLM parameter defaults (temperature, top_p, top_k, repeat_penalty, max_tokens) from `config/llm.yaml`, overridable per agent.
- The `call_llm()` / `call_llm_raw()` interface to Ollama.
- Token usage logging (`utils/token_tracker.py`), attributed to the current client (`client_email`, `current_user_id`).
- RAG context retrieval (`use_rag`, `rag_top_k`, `rag_type_filter`).
- Shared response-cleaning utilities (`clean_text_response`, JSON-parsing helpers).

### Routing logic (`OrchestratorAgent`)

Each incoming message is routed via three layers, in order, so the more expensive step (an LLM call) is only used when the cheaper deterministic checks are inconclusive:

1. **Jargon allowlist regex** — domain terms (EMS, SCADA, ISO 50001, vendor names, etc.) route directly to Commercial.
2. **Deterministic keyword regex** — per-intent patterns for reply-to-existing-email, reply-compose, email/inbox, and planning/calendar requests.
3. **LLM classifier fallback** — a lightweight, system-prompt-free call (`call_llm_raw`) decides between `email`, `reply`, `planning`, `commercial` for anything the regex layers didn't resolve, with short-message and "awaiting clarification" heuristics to avoid unnecessary re-classification mid-conversation.

---

## Tech Stack

| Layer | Technology |
|---|---|
| Frontend | React + Vite (`orbit-frontend`) |
| Backend | FastAPI (`api/main_api.py`) |
| Database | PostgreSQL |
| LLM runtime | Ollama (local), model `qwen2.5:7b` |
| RAG | FAISS (`IndexFlatIP`, cosine similarity via normalized vectors) |
| Auth | JWT (access + refresh tokens) |
| External integrations | Google Gmail API, Google Calendar API (per-user OAuth) |

---

## Project Structure

```
orbit-ai-assistant/
│
├── agents/
│   ├── base_agent.py          # Shared LLM interface, token logging, RAG helper
│   ├── orchestrator_agent.py  # Routing + delegation to specialized agents
│   ├── commercial_agent.py    # Sales/qualification agent (RAG-backed)
│   ├── email_agent.py         # Gmail reading + classification
│   ├── planning_agent.py      # Google Calendar briefing + conflict detection
│   ├── reply_agent.py         # Draft/revise email replies (business/personal persona)
│   └── google_auth.py         # Legacy single-user desktop OAuth flow (CLI/dev)
│
├── api/
│   └── main_api.py            # FastAPI app: auth, chat, OAuth, admin routes
│
├── prompts/
│   ├── commercial.txt         # CommercialAgent system prompt
│   ├── reply_business.txt     # ReplyAgent system prompt (business persona)
│   └── reply_personal.txt     # ReplyAgent system prompt (personal persona)
│
├── data/
│   ├── client_memory.json      # NOTE: legacy/leftover JSON file — distinct from utils/client_memory.py
│   │                            #       (the actual PostgreSQL-backed module used today). Verify whether
│   │                            #       this file is still read anywhere before relying on it.
│   ├── token_usage.json        # Global token usage log (all agents/clients/guests), written by token_tracker.py
│   └── rag/
│       ├── sources/           # JSON knowledge base (products, FAQ, pricing, sectors...)
│       ├── index/             # Generated FAISS index + chunk metadata
│       ├── chunker.py         # JSON -> chunk conversion
│       ├── embeddings.py      # Embedding generation via Ollama
│       ├── ingest.py          # Builds the FAISS index from sources/
│       └── retriever.py       # Query-time similarity search
│
├── config/
│   ├── llm.yaml                # Default model + generation parameters
│   ├── plans.json              # Token limits per plan (standard/premium)
│   ├── token_policy.json       # Per-plan history cap + RAG top_k
│   ├── settings.json           # Debug toggle state
│   └── tokens/{email}.json     # Per-account Google OAuth tokens (legacy flow)
│
├── utils/
│   ├── db.py                   # Centralized PostgreSQL connection
│   ├── auth.py                 # Signup/login/JWT/verification/password reset
│   ├── client_memory.py        # Conversation memory, quota, plans, client profiles
│   ├── token_tracker.py        # Token usage logging (JSON + PostgreSQL)
│   ├── token_policy.py         # Per-plan history/RAG policy loader
│   ├── token_estimator.py      # Admin diagnostic: fast, approximate pre-call estimation
│   ├── token_inspector.py      # Admin diagnostic: exact tokenization via the real Qwen tokenizer
│   ├── session_store.py        # DB-backed session <-> user mapping
│   ├── settings.py             # Debug mode read/write
│   └── google_oauth.py         # Per-user web OAuth flow (PostgreSQL-backed)
│
├── check_rag_scores.py         # Standalone script used to calibrate RAG_RELEVANCE_THRESHOLD
├── Dockerfile
├── requirements.txt
│
└── orbit-frontend/
    └── src/
        ├── components/
        │   └── admin/
        │       ├── ClientDrawer.jsx        # Full client detail side panel
        │       ├── ClientsTable.jsx        # Searchable/filterable client list
        │       ├── CostSummaryCard.jsx
        │       ├── IndustryChart.jsx
        │       ├── MachineDistributionChart.jsx
        │       ├── PlansSplitChart.jsx
        │       ├── RagSourcesPanel.jsx      # Manage data/rag/sources/*.json from the dashboard
        │       ├── TokenInspectorPanel.jsx  # UI for utils/token_inspector.py
        │       └── TokensTimelineChart.jsx
        ├── pages/
        │   ├── ChatPage.jsx
        │   ├── AdminPage.jsx      # Composes the admin/ panels above
        │   ├── LoginPage.jsx
        │   ├── SignupPage.jsx
        │   ├── ForgotPasswordPage.jsx
        │   ├── ResetPasswordPage.jsx
        │   ├── IntegrationsPage.jsx  # Google OAuth connect/disconnect UI
        │   └── VerifyEmailPage.jsx
        ├── context/                  # (AuthContext, etc. — not yet reviewed in detail)
        ├── hooks/                    # (not yet reviewed in detail)
        └── api.js                    # Fetch wrapper with auto token refresh
```

---

## Getting Started

### Prerequisites

- Python 3.11+
- Node.js 18+
- PostgreSQL 14+
- [Ollama](https://ollama.com) running locally with `qwen2.5:7b` pulled:
  ```bash
  ollama pull qwen2.5:7b
  ```

### Backend setup

```bash
python -m venv venv
venv\Scripts\activate          # Windows
# source venv/bin/activate     # macOS/Linux

pip install -r requirements.txt
```

Create a `.env` file at the project root:

```env
DB_HOST=localhost
DB_PORT=5432
DB_NAME=orbit_ai
DB_USER=orbit_app
DB_PASSWORD=your_password_here
```

Run the database migrations (see [Database Schema](#database-schema-key-tables)), then build the RAG index:

```bash
python rag/ingest.py
```

Start the API:

```bash
uvicorn api.main_api:app --reload
```

### Frontend setup

```bash
cd orbit-frontend
npm install
npm run dev
```

### CLI mode (no API, direct terminal chat)

```bash
python main.py
```

---

## Configuration

| File | Purpose |
|---|---|
| `config/llm.yaml` | Default model name + generation parameters (`temperature`, `top_p`, `top_k`, `repeat_penalty`, `max_tokens`). Agents only override what genuinely differs (e.g. `EmailAgent` uses `temperature=0.0` for reliable JSON output). |
| `config/plans.json` | Token limit per plan: Standard (5,000) / Premium (50,000). |
| `config/token_policy.json` | Per-plan conversation memory cap (`max_history_messages`) and RAG retrieval depth (`rag_top_k`) — see [Token Usage & Quota System](#token-usage--quota-system). |
| `config/settings.json` | Debug mode flag, toggled via `toggle_debug.py` or the admin dashboard. |

---

## Authentication & Authorization

- **Signup / login**: email + password, JWT access + refresh token pair.
- **Email verification**: a one-time-use token is emailed on signup; the account is unusable until verified.
- **Password reset**: token-based, emailed on request.
- **Guest trial**: unauthenticated visitors get a limited number of free messages (`GUEST_MESSAGE_LIMIT`), tracked in-memory per session, before being asked to sign up.
- **Admin routes**: every `/api/admin/*` route requires a valid JWT **and** `is_admin=True` on the account (`require_admin` dependency).
- **Google OAuth (per user)**: each authenticated user connects their own Gmail/Calendar account via a standard OAuth2 web flow; tokens are stored in PostgreSQL and refreshed automatically. `EmailAgent` and `PlanningAgent` always use the requesting user's own credentials in the authenticated API path (`run_for_user`) — the legacy shared desktop-flow tokens (`config/tokens/{email}.json`) remain only for CLI/dev usage.

---

## Agents

### OrchestratorAgent
Central router. Owns the four child agent instances for a session, propagates `client_email` / `current_user_id` / `client_plan` to each of them before delegating, and tracks `total_messages` for admin monitoring. Never contains business logic itself.

### CommercialAgent
- System prompt: `prompts/commercial.txt` — a compact **company anchor** (name, contact, module names) plus behavioral rules (formatting, off-topic detection, anti-loop, anti-letter-format). Detailed factual content (module descriptions, differentiators, sector qualification, objection handling, FAQ, pricing) is **not** hardcoded — it's retrieved dynamically from the RAG index and injected as a context block only when relevant, avoiding duplicate token cost.
- Topic classification: jargon allowlist + hard off-topic blocklist + LLM classifier fallback (`_is_in_scope`), aware of the assistant's last question so short factual replies ("8 factories", "MQTT") aren't misclassified as off-topic.
- Never invents pricing/specs: if RAG retrieval finds no relevant chunk above the similarity threshold for a fact-seeking question, it returns an explicit "let me connect you with the team" fallback instead of guessing.
- Output is passed through `_strip_letter_artifacts()`, a mechanical safety net that removes any residual email-letter formatting (greeting, sign-off, wrapping quotes, meta-commentary preamble) the model might still produce despite the prompt rules.

### EmailAgent
Reads the connected Gmail inbox and classifies each message into one of 10 fixed categories (Academic, Commercial, Recruitment, Meeting, Notification, Newsletter, Personal, Support, Spam, Other) with priority, summary, action items, and a suggested next action — always returned as strict JSON, validated against the allowed category/priority sets post-generation.

### PlanningAgent
Pulls today's and tomorrow's Google Calendar events, assigns a priority (1 = funding/investors, 2 = customers/prospects, 3 = internal/personal) via keyword matching, detects time conflicts, and generates a short daily briefing.

### ReplyAgent
Drafts email replies in one of two personas:
- **business** — represents Orbit's sales/support team, signs off as "Orbit Team", never commits to a price/date not already given.
- **personal** — drafts on behalf of the user's own inbox, never signs a company name, inserts an explicit placeholder rather than inventing the user's decision on yes/no questions.

Supports three modes: replying to an existing inbox email, composing from a raw instruction, and revising a previously drafted reply on a short follow-up instruction (e.g. "make it shorter").

---

## RAG (Retrieval-Augmented Generation)

- **Sources** (`data/rag/sources/*.json`): `orbit_products.json`, `faq_objections.json`, `sector_qualification.json`, `clients.json`, `pricing.json`, `plans.json`.
- **Pipeline**: `chunker.py` splits each JSON source into retrievable chunks → `embeddings.py` generates embeddings via Ollama → `ingest.py` normalizes and indexes them in a FAISS `IndexFlatIP` (cosine similarity) → `retriever.py` performs query-time top-k search.
- **Relevance threshold**: `RAG_RELEVANCE_THRESHOLD = 0.68` (in `commercial_agent.py`), calibrated empirically — chunks below this cosine score are discarded rather than injected as noise.
- **Pricing-aware retrieval**: pricing-related questions additionally query the index with `type_filter="pricing"` and merge those results ahead of the general top-k, so exact pricing tiers aren't crowded out by more generic chunks.
- Rebuild the index after any change to `data/rag/sources/`:
  ```bash
  python rag/ingest.py
  ```

---

## Token Usage & Quota System

### How a token count is produced

Every LLM call goes through `BaseAgent.call_llm()` / `call_llm_raw()`, which read the **exact** counts reported by Ollama itself:

```python
total_tokens = prompt_eval_count + eval_count
```

- `prompt_eval_count` — tokens Ollama had to process as input (system prompt + conversation history + RAG context + the new user message).
- `eval_count` — tokens generated in the response.

This is logged via `utils/token_tracker.log_usage()`, which writes to **two** places:
1. `data/token_usage.json` — global dashboard breakdown by agent, all clients/guests included.
2. PostgreSQL `token_usage` table (when a `user_id` is available) — the source of truth for per-client quota enforcement and the admin per-client/per-agent breakdown.

### Where the cost actually comes from

Because Ollama is stateless, the **entire** system prompt and conversation history must be resent on every single call — a short user message does not mean a cheap call. The dominant cost driver is almost always the fixed system prompt, not the user's message:

| Agent | System prompt (approx. tokens/call) |
|---|---|
| CommercialAgent | ~2,900 |
| EmailAgent | ~1,300 |
| ReplyAgent (business) | ~900 |
| ReplyAgent (personal) | ~630 |
| PlanningAgent | ~270 |
| OrchestratorAgent | 0 (no system prompt — classification uses `call_llm_raw`) |

Run `python -m utils.token_estimator` any time to get this breakdown fresh from the real prompt files (nothing here is hardcoded — see [Diagnostic tooling](#diagnostic-tooling-admin-only) below).

### Controls in place

| Lever | Mechanism | Location |
|---|---|---|
| System prompt size | Factual content (product specs, FAQ, objections, sector qualification) lives in the RAG index, not the prompt — retrieved only when relevant. | `prompts/commercial.txt`, `data/rag/sources/` |
| Conversation memory sent per call | Capped **per plan** — only the last N messages of `commercial_history` are forwarded to the model, regardless of how long the session has run. Full history is still persisted in PostgreSQL for continuity across sessions. | `config/token_policy.json` → `max_history_messages` |
| RAG context depth | Number of chunks retrieved per query, also **per plan**. | `config/token_policy.json` → `rag_top_k` |
| Quota enforcement | `check_quota()` sums `token_usage` since the client's last reset and compares against their plan's `token_limit`; blocks further messages once exceeded. | `utils/client_memory.py` |
| Quota reset | Admin can reset a client's counter to 0 (like a new billing cycle) **without deleting any usage history** — only the calculation start point (`users.quota_reset_at`) advances. | `reset_client_quota()`, exposed via the admin dashboard |

### Diagnostic tooling (admin only)

Two complementary tools exist — one fast/approximate, one exact/slower:

**`utils/token_estimator.py`** — pre-call estimation, before contacting Ollama:
```bash
python -m utils.token_estimator
```
Uses a `chars / 4 ≈ 1 token` approximation (the same rule publicly documented by other LLM providers; realistic margin of error ±15-20%). All figures are computed live from the real prompt files / instantiated agent classes, never hardcoded, so they stay accurate as prompts evolve.

**`utils/token_inspector.py`** — exact tokenization using the real `Qwen/Qwen2.5-7B-Instruct` tokenizer (via HuggingFace `tokenizers`), not an approximation:
- `inspect_tokens(text)` — returns the exact token count, numeric token IDs, and the individual text pieces Qwen actually splits the input into (visibility Ollama's API never exposes).
- `compare_with_ollama_count(text, ollama_reported_count)` — cross-checks our independent exact count against a real `prompt_eval_count` returned by Ollama for the same text, to confirm the two agree.

Exposed in the admin dashboard as the **Token Inspector** panel: paste any text and inspect exactly how Qwen2.5 would split it before it's ever sent to the model.

---

## Admin Dashboard

Accessible at `/admin` to accounts with `is_admin=True`. Built as a set of composable panels under `orbit-frontend/src/components/admin/`, rather than a single monolithic page:

- **Live metrics**: total LLM calls, total tokens, active sessions, debug mode toggle.
- **Clients table** (`ClientsTable.jsx`) — searchable and filterable (by email, plan, industry, sorted by token usage), showing plan, industry, machine count, token usage vs. limit, and last seen. Clicking a row opens `ClientDrawer.jsx` for full client detail.
- **Cost Summary** (`CostSummaryCard.jsx`) — aggregate cost/usage overview.
- **Charts**:
  - `TokensTimelineChart.jsx` — token usage over time (1d/7d/30d views).
  - `PlansSplitChart.jsx` — Standard vs. Premium distribution.
  - `IndustryChart.jsx` — client breakdown by industry (auto-extracted by `CommercialAgent.extract_profile_info`).
  - `MachineDistributionChart.jsx` — client breakdown by machine count bracket.
  - Tokens by agent — legend/breakdown of consumption per agent.
- **Token Inspector** (`TokenInspectorPanel.jsx`) — paste any text and see exactly how the real Qwen2.5 tokenizer splits it, backed by `utils/token_inspector.py` (see [Diagnostic tooling](#diagnostic-tooling-admin-only)).
- **Knowledge Base / RAG panel** (`RagSourcesPanel.jsx`) — lists every file in `data/rag/sources/` with size and last-modified date, supports adding a new source file and deleting an existing one directly from the dashboard.
- **Active sessions**: per-session message count and associated client email.
- **Per-client actions**: upgrade/downgrade plan, **reset quota** (counter → 0, history untouched — highlighted when a client has hit their limit), reset conversation history, toggle persistent memory.

> Components not yet documented in detail here (`ClientDrawer.jsx` internals, exact `RagSourcesPanel.jsx` upload/delete API contract) — see the component source for the authoritative behavior, or extend this section once reviewed.

---

## Database Schema (Key Tables)

| Table | Purpose |
|---|---|
| `users` | Account, plan, `token_limit`, `is_admin`, `memory_enabled`, `quota_reset_at`. |
| `conversation_history` | Persistent chat memory per user (capped to the last 20 messages on load). |
| `token_usage` | One row per LLM call: `user_id`, `agent_name`, `prompt_tokens`, `response_tokens`, `total_tokens`, `created_at`. Source of truth for quota + admin breakdown. |
| `client_profile` | Auto-extracted `industry_type` / `machine_count` per client, inferred from conversation by `CommercialAgent`. |
| `oauth_credentials` | Per-user Google OAuth tokens (Gmail + Calendar), refreshed automatically. |

> Run `migration_quota_reset.sql` (adds `users.quota_reset_at`) if upgrading from a version predating the quota-reset feature.

---

## API Reference

### Auth
| Method | Route | Description |
|---|---|---|
| POST | `/api/auth/signup` | Create an account |
| POST | `/api/auth/login` | Get access + refresh tokens |
| GET | `/api/auth/verify-email` | Verify via emailed token |
| POST | `/api/auth/refresh` | Exchange refresh token for a new access token |
| POST | `/api/auth/forgot-password` / `/api/auth/reset-password` | Password reset flow |
| GET | `/api/auth/me` | Current user info |

### Chat
| Method | Route | Description |
|---|---|---|
| POST | `/api/chat` | Send a message (guest or authenticated) |
| POST | `/api/chat/reset` | Clear conversation history |
| GET / POST | `/api/chat/memory` | Get/set persistent memory toggle |

### Google OAuth
| Method | Route | Description |
|---|---|---|
| GET | `/api/oauth/google/connect` | Get the authorization URL |
| GET | `/api/oauth/google/callback` | OAuth redirect target (not JWT-protected) |
| GET | `/api/oauth/google/status` | Connection status |
| DELETE | `/api/oauth/google/disconnect` | Revoke access |

### Admin (all require admin JWT)
| Method | Route | Description |
|---|---|---|
| GET | `/api/admin/tokens` | Global token usage by agent |
| GET | `/api/admin/usage_by_client` | Token usage by client + agent |
| GET | `/api/admin/sessions` | Active session list |
| GET | `/api/admin/clients` | All clients with plan/quota/profile |
| GET | `/api/admin/clients/{email}/detail` | Full client detail (usage, profile, history) |
| POST | `/api/admin/set_plan` | Change a client's plan |
| POST | `/api/admin/reset_quota` | Reset a client's token counter to 0 |
| POST | `/api/admin/clients/{email}/reset_history` | Clear a client's conversation history |
| POST | `/api/admin/clients/{email}/toggle_memory` | Enable/disable persistent memory |
| GET / POST | `/api/admin/debug` | Get/set debug mode |

---

## Known Limitations & Roadmap

- **`data/client_memory.json` naming collision**: there's a JSON file at `data/client_memory.json` sitting alongside the (actively used, PostgreSQL-backed) `utils/client_memory.py` module — same name, very different purpose. Confirm whether the JSON file is legacy/dead, or still read by some code path, before assuming it's safe to ignore or delete.
- **Token estimation has two tiers of accuracy**: `utils/token_estimator.py` is a fast approximation (`chars/4`); `utils/token_inspector.py` gives the exact Qwen2.5 tokenizer count but requires downloading/loading the real tokenizer. Use the inspector when precision matters (e.g. validating a prompt change), the estimator for quick day-to-day checks.
- **Guest trial state is in-memory**: resets on server restart; acceptable for a trial limit, not meant to survive across processes/workers.
- **No automatic quota renewal**: resets are currently manual (admin action), not scheduled — a periodic job (e.g. monthly cron) is a natural next step.
- **Single shared Ollama model instance**: all agents share one `qwen2.5:7b` model; no per-agent model selection yet.
- **RAG threshold is static**: `RAG_RELEVANCE_THRESHOLD` was calibrated once against the current corpus — revisit if `data/rag/sources/` changes significantly.

Planned extensions (from the original architecture design):
- CRM Agent (automatic lead creation, HubSpot/Odoo sync)
- Fundraising Agent (investor research, follow-up tracking)
- Orbit Technical Expert Agent (connected to InfluxDB/MongoDB + IEC/IEEE/ISO standards for deep technical Q&A)

---

## Security Notes

- OAuth token files (`config/tokens/*.json`) and any `.env` file must **never** be committed or shared. Revoke and regenerate immediately if exposed.
- Admin routes are gated by `is_admin` on the JWT-verified user — never trust a client-supplied email/role for privileged actions.
- `client_email` used for chat/token attribution is derived exclusively from the verified JWT server-side, never from client-supplied request fields, to prevent impersonation of another client's quota or history.