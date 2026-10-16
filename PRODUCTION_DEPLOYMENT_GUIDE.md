# 🚀 Production Deployment & Future Engineering Roadmap
### Personal Finance AI Assistant (GraphRAG + Neo4j + FastAPI + React)

This document outlines the step-by-step procedure to deploy the application completely free to cloud infrastructure, followed by the prioritized roadmap for advanced enterprise-grade features.

---

## 📊 Current Audit Status: ~95% Production Ready

All critical architectural and engineering gaps from the **Senior AI Engineer Production Audit** have been implemented and verified:

* ✅ **C1 (LLM Integration Depth):** Exponential-backoff retries, token usage tracking (`prompt_tokens`, `completion_tokens`), latency calculation, and fallback response.
* ✅ **C2 (Engine Test Suite):** 51 mock-based unit tests for deterministic math formulas (zero database dependencies, running in CI).
* ✅ **C3 (Structured Logging):** Formatted logging throughout the entire pipeline (`%(asctime)s | %(levelname)-8s | %(name)s | %(message)s`).
* ✅ **C4 (DB Singletons):** Eliminated module-level database instances via FastAPI dependency injection (`Depends(get_neo4j_service)`).
* ✅ **C5 (Rate Limiting):** SlowAPI rate limiting enabled (`20 req/min` for AI queries, `10 req/min` for imports).
* ✅ **C6 (Async LLM Client):** Non-blocking `AsyncGroq` client and asynchronous GraphRAG pipeline (`process_query_async`).
* ✅ **C7 (Rigorous Benchmark):** Tolerance-based numerical evaluation assertions saving to `benchmark_results.json`.
* ✅ **C8 (Secret Validation):** Hard fail on missing `SESSION_SECRET` at application startup.
* ✅ **H1 (Prompt Versioning):** Structured prompt registry (`v1.0`, `v1.1`) with rollback and API introspection (`GET /api/assistant/prompt-versions`).
* ✅ **H2 (Stage Latency):** Per-stage latency metrics (`nlu_ms`, `graph_ms`, `engine_ms`, `llm_ms`, `total_ms`) tracked and displayed live in UI.
* ✅ **H3 (Multi-Turn Memory):** Conversational context forwarding and session management.
* ✅ **H4 (Deep Health Check):** `/health` verifies live Neo4j connectivity and Groq API readiness, returning HTTP 503 on dependency failures.
* ✅ **H5 (Pinned Dependencies):** Exact versions specified across all libraries in `requirements.txt`.
* ✅ **H6 (Containerization):** `Dockerfile` and `docker-compose.yml` for reproducible single-command builds.
* ✅ **H7 (Frontend Telemetry):** Latency breakdown chips, token usage counters, and animated thinking states in React UI.
* ✅ **CI/CD:** GitHub Actions workflow running tests across Python 3.11 and 3.12 (**111 passing tests, 91% engine coverage**).

---

## 🌐 Part 1: Free-Tier Cloud Deployment Guide

The stack can be deployed 100% free with no credit card required using coordinated free-tier cloud providers:

```
┌─────────────────────────────────┐
│       Vercel (Free CDN)         │
│  - React + Vite SPA             │
│  - Automatic HTTPS & CDN        │
└────────────────┬────────────────┘
                 │ /api/* proxy (no CORS issues)
┌────────────────▼────────────────┐
│   Railway / Render (Free Tier)  │
│  - Dockerized FastAPI Backend   │
│  - 20 req/min Rate Limiting     │
│  - Async LLM Streaming          │
└────────┬───────────────┬────────┘
         │               │
┌────────▼──────┐ ┌──────▼────────┐
│ Neo4j AuraDB  │ │  Groq Cloud   │
│ (Free Tier)   │ │  Free API Key │
│ 200MB Graph   │ │  Llama 3.3    │
└───────────────┘ └───────────────┘
```

---

### Step 1: Set Up Free Neo4j AuraDB (Cloud Database)

1. Go to [neo4j.com/cloud/platform/aura-graph-database/](https://neo4j.com/cloud/platform/aura-graph-database/) and sign up.
2. Click **Create an Instance** $\rightarrow$ select **AuraDB Free**.
3. **Save your credentials file (`credentials.txt`)**:
   * **Connection URI:** `neo4j+s://<instance-id>.databases.neo4j.io`
   * **Username:** `neo4j`
   * **Password:** `<generated-password>`
4. In your local terminal, test connecting and seed the initial baseline financial graph:
   ```powershell
   $env:NEO4J_URI="neo4j+s://<instance-id>.databases.neo4j.io"
   $env:NEO4J_USERNAME="neo4j"
   $env:NEO4J_PASSWORD="<generated-password>"

   # Populate the cloud database with Rahul's baseline data
   .\.venv\Scripts\python.exe -m backend.scripts.seed_db
   ```

---

### Step 2: Deploy Backend to Railway or Render

1. Push all latest changes to GitHub:
   ```powershell
   git push origin main
   ```
2. Log into [Railway.app](https://railway.app) (or [Render.com](https://render.com)) with your GitHub account.
3. Click **New Project** $\rightarrow$ **Deploy from GitHub repo** $\rightarrow$ select `Personal_Finance_AI_FYP`.
4. Railway will automatically detect the root `Dockerfile`.
5. Under **Variables / Settings**, add the production environment variables:
   ```ini
   NEO4J_URI=neo4j+s://<your-instance-id>.databases.neo4j.io
   NEO4J_USERNAME=neo4j
   NEO4J_PASSWORD=<your-auradb-password>
   GROQ_API_KEY=gsk_...
   SESSION_SECRET=<generate with python -c "import secrets; print(secrets.token_hex(32))">
   SESSION_COOKIE_SECURE=true
   DEFAULT_PROMPT_VERSION=v1.1
   CORS_ORIGINS=https://<your-app-name>.vercel.app
   ```
6. Click **Deploy**. Test the live health endpoint in your browser:
   `https://<your-railway-domain>/health`
   Expected response:
   ```json
   {
     "api": "ONLINE",
     "neo4j": "ONLINE",
     "llm_configured": true
   }
   ```

---

### Step 3: Deploy Frontend to Vercel

1. Log into [Vercel](https://vercel.com) with GitHub.
2. Click **Add New Project** $\rightarrow$ import `Personal_Finance_AI_FYP`.
3. In Project Build Settings:
   * **Root Directory:** `./frontend`
   * **Framework Preset:** `Vite`
   * **Build Command:** `npm run build`
   * **Output Directory:** `dist`
4. Deploy the project to get your live URL (e.g. `https://personal-finance-ai.vercel.app`).
5. In `frontend/vercel.json`, configure the `/api` rewrite to point to your Railway domain so cookies remain first-party without CORS friction:
   ```json
   {
     "rewrites": [
       {
         "source": "/api/:path*",
         "destination": "https://<your-railway-domain>/api/:path*"
       },
       {
         "source": "/(.*)",
         "destination": "/index.html"
       }
     ]
   }
   ```

---

## 🛠️ Part 2: High-Value Engineering Roadmap (Post-MVP)

Once cloud deployment is active, here is the feature checklist for scaling into commercial production:

### 1. Vector Semantic Indexing (True Hybrid GraphRAG)
* **Goal:** Understand semantic nuances in transaction descriptions and fuzzy question phrasing (e.g., *"How much did I spend eating out last weekend?"* when the user didn't write the literal word `"Food"`).
* **Technical Plan:**
  - Create a **Neo4j Vector Index** over merchant names and transaction notes.
  - Compute embeddings using a lightweight local model (`all-MiniLM-L6-v2`) or Groq/OpenAI embeddings.
  - Hybrid query combines vector similarity (top $k$ matches) with Cypher path traversal for deep financial context.

### 2. Async Task Queue for Massive Imports (Celery / Redis)
* **Goal:** Ingest multi-year bank statements with 10,000+ rows without HTTP request timeouts.
* **Technical Plan:**
  - Decouple the CSV parser using **Celery** with **Redis** as message broker.
  - Expose a WebSocket or SSE endpoint streaming live progress to `ImportManager.jsx` (`Processing row 1,420 of 10,000...`).
  - Store background task status with cancel and retry capability.

### 3. Financial Advice Disclaimers & Safety Guardrails
* **Goal:** Regulatory compliance (SEBI/SEC guidelines: automated tools cannot give unauthorized investment advice).
* **Technical Plan:**
  - Integrate **NeMo Guardrails** or output filter rules.
  - Automatically append statutory disclaimer banner on queries with high purchase risk ratings:
    > *"This automated assessment is for budgeting and planning purposes only and does not constitute certified financial or investment advice."*
  - Add spending threshold trigger alerts when discretionary spend crosses 50% of monthly income.

### 4. Continuous Evaluation & Benchmark Tracking
* Run `test_evaluation_benchmark.py` against the cloud AuraDB database.
* Save the output `benchmark_results.json` directly into git to publish verified latency and hallucination-free metrics on documentation and portfolio showcases.
