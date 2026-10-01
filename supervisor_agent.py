"""
Supervisor Agent — coordinates the complete workflow end to end, matching
the architecture:

    Supervisor -> Data Agent -> SQL Agent -> ML Agent -> RAG Agent
               -> Decision Agent -> Risk Engine -> Human Approval -> Action

Every run is persisted as a "workflow" row with a full step-by-step trace,
so the API can return either the live result or replay it later via
GET /api/workflows/{id}.
"""
import json
import uuid
import datetime as dt

from app.database import get_conn
from app.agents.data_agent import DataAgent
from app.agents.sql_agent import SQLAgent
from app.agents.ml_agent import MLAgent
from app.agents.rag_agent import RAGAgent
from app.agents.decision_agent import DecisionAgent
from app.agents.risk_engine import RiskEngine
from app.agents.action_agent import ActionAgent


class SupervisorAgent:
    name = "supervisor_agent"

    def __init__(self):
        self.data_agent = DataAgent()
        self.sql_agent = SQLAgent()
        self.ml_agent = MLAgent()
        self.rag_agent = RAGAgent()
        self.decision_agent = DecisionAgent()
        self.risk_engine = RiskEngine()
        self.action_agent = ActionAgent()

    def run_workflow(self, query: str, domain: str) -> dict:
        workflow_id = str(uuid.uuid4())
        trace: dict = {"steps": []}

        def log(step: str, output: dict):
            trace["steps"].append({
                "step": step,
                "output": output,
                "timestamp": dt.datetime.utcnow().isoformat(),
            })

        # 1. Data Agent
        data_result = self.data_agent.gather(domain)
        log("data_agent", data_result)

        # 2. SQL Agent
        sql_result = self.sql_agent.query(query, domain)
        log("sql_agent", sql_result)

        # 3. ML Agent
        ml_result = self.ml_agent.analyze(data_result["records"], data_result["metric_column"])
        log("ml_agent", ml_result)

        # 4. RAG Agent
        rag_result = self.rag_agent.retrieve(query, domain)
        log("rag_agent", rag_result)

        # 5. Decision Agent
        decision_result = self.decision_agent.recommend(
            query, domain, data_result["summary"], sql_result, ml_result, rag_result
        )
        log("decision_agent", decision_result)

        # 6. Risk Engine
        risk_result = self.risk_engine.assess(decision_result, ml_result, domain)
        log("risk_engine", risk_result)

        # 7. Human Approval / Action
        status = "completed"
        approval_record = None
        executed_actions = []

        if risk_result["requires_approval"] and decision_result.get("recommendations"):
            from app.approval.approval_manager import ApprovalManager
            approval_record = ApprovalManager().create(
                workflow_id=workflow_id,
                domain=domain,
                summary=decision_result.get("summary", ""),
                payload=decision_result,
                risk=risk_result,
            )
            status = "awaiting_approval"
            log("human_approval", {"status": "pending", "approval_id": approval_record["id"]})
        else:
            for rec in decision_result.get("recommendations", []):
                executed_actions.append(self.action_agent.execute(workflow_id, domain, rec))
            log("action_agent", {"executed_actions": executed_actions, "auto_approved": True})

        self._persist(workflow_id, domain, query, status, trace)

        return {
            "workflow_id": workflow_id,
            "domain": domain,
            "query": query,
            "status": status,
            "trace": trace,
            "decision": decision_result,
            "risk": risk_result,
            "approval": approval_record,
            "executed_actions": executed_actions,
        }

    def record_approval_outcome(self, workflow_id: str, approval_status: str,
                                 executed_actions: list, decided_by: str, comment: str | None) -> None:
        """Called by ApprovalManager.decide() once a human makes a decision, to
        close the loop on the workflow's persisted trace/status."""
        workflow = self.get_workflow(workflow_id)
        if workflow is None:
            return

        trace = workflow["trace"]
        trace["steps"].append({
            "step": "human_approval",
            "output": {
                "status": approval_status,
                "decided_by": decided_by,
                "comment": comment,
            },
            "timestamp": dt.datetime.utcnow().isoformat(),
        })
        if approval_status == "approved":
            trace["steps"].append({
                "step": "action_agent",
                "output": {"executed_actions": executed_actions, "auto_approved": False},
                "timestamp": dt.datetime.utcnow().isoformat(),
            })
            new_status = "completed"
        else:
            new_status = "rejected"

        self._persist(workflow_id, workflow["domain"], workflow["query"], new_status, trace)

    def get_workflow(self, workflow_id: str) -> dict | None:
        with get_conn() as conn:
            row = conn.execute("SELECT * FROM workflows WHERE id = ?", (workflow_id,)).fetchone()
        if row is None:
            return None
        d = dict(row)
        d["trace"] = json.loads(d["trace_json"])
        return d

    def list_workflows(self, limit: int = 50) -> list[dict]:
        with get_conn() as conn:
            rows = conn.execute(
                "SELECT id, domain, query, status, created_at, updated_at FROM workflows "
                "ORDER BY created_at DESC LIMIT ?", (limit,)
            ).fetchall()
        return [dict(r) for r in rows]

    @staticmethod
    def _persist(workflow_id: str, domain: str, query: str, status: str, trace: dict) -> None:
        now = dt.datetime.utcnow().isoformat()
        with get_conn() as conn:
            existing = conn.execute("SELECT id FROM workflows WHERE id = ?", (workflow_id,)).fetchone()
            if existing:
                conn.execute(
                    "UPDATE workflows SET status = ?, trace_json = ?, updated_at = ? WHERE id = ?",
                    (status, json.dumps(trace, default=str), now, workflow_id),
                )
            else:
                conn.execute(
                    "INSERT INTO workflows (id, domain, query, status, trace_json, created_at, updated_at) "
                    "VALUES (?, ?, ?, ?, ?, ?, ?)",
                    (workflow_id, domain, query, status, json.dumps(trace, default=str), now, now),
                )
