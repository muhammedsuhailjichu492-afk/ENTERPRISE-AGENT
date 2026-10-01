"""
FastAPI entrypoint for the Autonomous Enterprise Intelligence & Operations
Agent platform.

Run with:
    uvicorn app.main:app --reload
"""
from pathlib import Path

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse

from app.config import settings
from app.database import init_db, seed_sample_data, get_conn, dict_rows
from app import vector_store
from app.models import AnalyzeRequest, ApprovalDecisionRequest
from app.agents.supervisor_agent import SupervisorAgent
from app.approval.approval_manager import ApprovalManager

app = FastAPI(
    title="Autonomous Enterprise Intelligence & Operations Agent",
    description=(
        "AI-powered multi-agent platform that analyzes enterprise data, identifies "
        "operational problems, generates recommendations, and executes approved "
        "workflows across Production, Inventory, Quality, Operations, Procurement, "
        "HR, Sales, Finance, Projects, and Reporting."
    ),
    version="1.0.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

supervisor = SupervisorAgent()
approvals = ApprovalManager()

STATIC_DIR = Path(__file__).resolve().parent.parent / "static"
if STATIC_DIR.exists():
    app.mount("/static", StaticFiles(directory=str(STATIC_DIR)), name="static")


@app.on_event("startup")
def on_startup():
    init_db()
    seed_sample_data()
    vector_store.seed_if_empty()


@app.get("/")
def root():
    index = STATIC_DIR / "index.html"
    if index.exists():
        return FileResponse(str(index))
    return {"message": "Autonomous Enterprise Intelligence & Operations Agent API. See /docs."}


@app.get("/api/health")
def health():
    return {
        "status": "ok",
        "llm_configured": settings.llm_enabled,
        "domains": settings.DOMAINS,
        "risk_approval_threshold": settings.RISK_APPROVAL_THRESHOLD,
    }


@app.post("/api/analyze")
def analyze(payload: AnalyzeRequest):
    domain = payload.domain.lower().strip()
    if domain not in settings.DOMAINS:
        raise HTTPException(status_code=400, detail=f"Unknown domain '{domain}'. Valid domains: {settings.DOMAINS}")
    if not payload.query.strip():
        raise HTTPException(status_code=400, detail="query must not be empty.")

    result = supervisor.run_workflow(payload.query.strip(), domain)
    return result


@app.get("/api/workflows")
def list_workflows(limit: int = 50):
    return supervisor.list_workflows(limit=limit)


@app.get("/api/workflows/{workflow_id}")
def get_workflow(workflow_id: str):
    workflow = supervisor.get_workflow(workflow_id)
    if workflow is None:
        raise HTTPException(status_code=404, detail="Workflow not found")
    return workflow


@app.get("/api/approvals")
def list_approvals(status: str = "pending"):
    if status == "pending":
        return approvals.list_pending()
    return approvals.list_all()


@app.get("/api/approvals/{approval_id}")
def get_approval(approval_id: str):
    approval = approvals.get(approval_id)
    if approval is None:
        raise HTTPException(status_code=404, detail="Approval not found")
    return approval


@app.post("/api/approvals/{approval_id}/decide")
def decide_approval(approval_id: str, decision: ApprovalDecisionRequest):
    try:
        return approvals.decide(approval_id, decision.approved, decision.decided_by, decision.comment)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@app.get("/api/domains/{domain}/data")
def get_domain_data(domain: str, limit: int = 30):
    domain = domain.lower().strip()
    if domain not in settings.DOMAINS:
        raise HTTPException(status_code=400, detail=f"Unknown domain '{domain}'.")
    from app.agents.data_agent import DataAgent
    return DataAgent().gather(domain, limit=limit)


@app.get("/api/actions")
def list_actions(limit: int = 50):
    with get_conn() as conn:
        rows = conn.execute(
            "SELECT * FROM actions ORDER BY created_at DESC LIMIT ?", (limit,)
        ).fetchall()
    return dict_rows(rows)
