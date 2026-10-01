# Autonomous Enterprise Intelligence & Operations Agent

An AI-powered multi-agent platform that analyzes enterprise data, identifies
operational problems, generates recommendations, and executes approved
workflows — with a human-in-the-loop gate on anything risky.

This implements the architecture:

```
Supervisor Agent
   -> Data Agent
   -> SQL Agent
   -> ML Agent
   -> RAG Agent
   -> Decision Agent
   -> Risk Engine
   -> Human Approval
   -> Action
```

Tech: **FastAPI · Anthropic Claude (LLM/Agentic AI) · Multi-Agent orchestration
· RAG · scikit-learn (ML) · SQLite (SQL) · ChromaDB (Vector DB)**

Domains covered: Production, Inventory, Quality, Operations, Procurement,
HR, Sales, Finance, Projects, Reporting.

---

## 1. What each agent does

| Agent | File | Role |
|---|---|---|
| Supervisor | `app/agents/supervisor_agent.py` | Orchestrates the full pipeline, persists the run as a `workflow`, and closes the loop after a human decision. |
| Data Agent | `app/agents/data_agent.py` | Pulls the relevant domain data from SQLite and computes a statistical summary. |
| SQL Agent | `app/agents/sql_agent.py` | Translates the operator's question into a **read-only** SQL query (LLM-generated, validated, then executed). |
| ML Agent | `app/agents/ml_agent.py` | Runs IsolationForest anomaly detection + a linear trend/forecast on the domain's key metric. |
| RAG Agent | `app/agents/rag_agent.py` | Retrieves relevant company SOPs/policies from the vector DB (ChromaDB). |
| Decision Agent | `app/agents/decision_agent.py` | LLM synthesizes data + SQL + ML + RAG context into a root-cause analysis and ranked recommendations. |
| Risk Engine | `app/agents/risk_engine.py` | Rule-based (auditable) scoring of each recommendation; decides if human approval is required. |
| Approval Manager | `app/approval/approval_manager.py` | Persists pending approvals; on decision, triggers execution and updates the workflow. |
| Action Agent | `app/agents/action_agent.py` | Executes approved/auto-cleared recommendations (simulated integrations — see below). |

Everything runs **fully offline** with zero configuration: if `ANTHROPIC_API_KEY`
isn't set, the LLM calls fall back to clearly-labeled deterministic stubs so
you can explore the whole pipeline, UI, and approval flow immediately. Set
the key to get real reasoning from the SQL and Decision agents.

## 2. Project layout

```
enterprise-agent/
├── app/
│   ├── main.py                 # FastAPI app + all routes
│   ├── config.py                # env-driven settings
│   ├── database.py              # SQLite schema + synthetic data seeding
│   ├── models.py                 # Pydantic request/response schemas
│   ├── llm_client.py              # Anthropic wrapper + offline fallback
│   ├── vector_store.py            # ChromaDB wrapper (RAG)
│   ├── agents/
│   │   ├── supervisor_agent.py
│   │   ├── data_agent.py
│   │   ├── sql_agent.py
│   │   ├── ml_agent.py
│   │   ├── rag_agent.py
│   │   ├── decision_agent.py
│   │   ├── risk_engine.py
│   │   └── action_agent.py
│   ├── approval/approval_manager.py
│   └── knowledge_base/sample_docs.py   # seed SOP/policy documents for RAG
├── static/index.html            # single-page operations console (no build step)
├── scripts/seed_data.py         # standalone DB/vector-store seeding
├── tests/                       # pytest suite (runs fully offline)
├── requirements.txt
└── .env.example
```

## 3. Setup (VS Code)

1. Open this folder in VS Code (`File > Open Folder…`).
2. Create and activate a virtual environment:

   ```bash
   python -m venv .venv
   # macOS/Linux
   source .venv/bin/activate
   # Windows
   .venv\Scripts\activate
   ```

3. Install dependencies:

   ```bash
   pip install -r requirements.txt
   ```

4. Copy the env template and (optionally) add your Anthropic API key:

   ```bash
   cp .env.example .env
   # then edit .env and set ANTHROPIC_API_KEY=sk-ant-...
   ```

   Get a key at https://console.anthropic.com/. Without a key the app still
   runs completely — the SQL and Decision agents just use offline stubs.

5. Run the server:

   ```bash
   uvicorn app.main:app --reload
   ```

6. Open the console: **http://localhost:8000/** — a full dashboard where you
   can pick a domain, ask a question, watch the pipeline run step by step,
   and approve/reject flagged recommendations.

   Interactive API docs (Swagger): **http://localhost:8000/docs**

The database (`data/enterprise.db`) and vector store (`data/chroma/`) are
created and seeded automatically on first startup — no manual setup step
required. To reset with fresh synthetic data at any time:

```bash
python scripts/seed_data.py --force
```

## 4. Try it

In the console, pick **Production** and ask:

> Why is Line-A's defect rate rising and what should we do about it?

The synthetic seed data deliberately drifts Line-A's defect/downtime rate
upward over the last ~6 days and spikes its complaint count, so the ML
Agent flags it as anomalous and the Decision Agent (with a real API key)
will trace it back through the retrieved SOP. Try **Inventory** ("which SKUs
need reordering?") or **Procurement** ("is any supplier's on-time delivery
degrading?") for other pre-baked scenarios.

High-risk recommendations (e.g. holding a shipment, switching a supplier)
will stop in **Pending approvals** until you approve or reject them.

## 5. API reference

| Method | Path | Purpose |
|---|---|---|
| POST | `/api/analyze` | Run the full pipeline: `{ "query": "...", "domain": "production" }` |
| GET | `/api/workflows` | List past workflow runs |
| GET | `/api/workflows/{id}` | Full step-by-step trace of one run |
| GET | `/api/approvals?status=pending` | List pending (or all) approvals |
| POST | `/api/approvals/{id}/decide` | `{ "approved": true, "decided_by": "...", "comment": "..." }` |
| GET | `/api/domains/{domain}/data` | Raw Data Agent pull for a domain (debugging) |
| GET | `/api/actions` | Log of every executed action |
| GET | `/api/health` | Service status, whether an LLM key is configured |

## 6. Risk & approval logic

`RiskEngine` (rule-based, not LLM-based — kept auditable on purpose) scores
0–100 from: domain criticality, ML-detected anomaly rate, trend volatility,
the Decision Agent's own recommendation priority, high-impact keywords
(e.g. "hold shipment", "layoff", "recall"), and specific high-risk
`action_type`s. Anything at/above `RISK_APPROVAL_THRESHOLD` (default `55`,
configurable in `.env`) — or matching a high-impact keyword/action type
regardless of score — stops for human approval instead of auto-executing.

## 7. Extending to real systems

`ActionAgent` handlers (`app/agents/action_agent.py`) are intentionally
simulated — each one logs a structured result and is the seam where you'd
wire up a real system:

```python
def _handle_create_reorder(rec: dict, domain: str) -> dict:
    # Replace with: your ERP/procurement API call
    return {"system": "ERP/Procurement", "operation": "purchase_order.create", ...}
```

Swap `app/vector_store.py` for a hosted vector DB (Pinecone, Weaviate, etc.)
by keeping the same `query()`/`seed_if_empty()` interface. Swap
`app/database.py`'s SQLite calls for a connection to your real warehouse —
the Data/SQL Agents only depend on `get_conn()` and the `DOMAIN_TABLE_MAP`.

## 8. Tests

```bash
pytest -v
```

Runs fully offline against a temporary SQLite DB + vector store (see
`tests/conftest.py`), covering each agent individually, the full
Supervisor-orchestrated pipeline, the approval loop, and the HTTP API.
