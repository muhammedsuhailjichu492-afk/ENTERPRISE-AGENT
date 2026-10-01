
import json
import uuid
import datetime as dt
from app.database import get_conn, dict_rows
from app.agents.action_agent import ActionAgent

_action_agent = ActionAgent()


class ApprovalManager:
    name = "approval_manager"

    def create(self, workflow_id: str, domain: str, summary: str, payload: dict, risk: dict) -> dict:
        approval_id = str(uuid.uuid4())
        now = dt.datetime.utcnow().isoformat()
        record = {
            "id": approval_id,
            "workflow_id": workflow_id,
            "domain": domain,
            "summary": summary,
            "payload_json": json.dumps(payload, default=str),
            "risk_score": risk["score"],
            "risk_level": risk["level"],
            "status": "pending",
            "decided_by": None,
            "decision_comment": None,
            "created_at": now,
            "decided_at": None,
        }
        with get_conn() as conn:
            conn.execute(
                "INSERT INTO approvals (id, workflow_id, domain, summary, payload_json, risk_score, risk_level, "
                "status, decided_by, decision_comment, created_at, decided_at) VALUES "
                "(:id, :workflow_id, :domain, :summary, :payload_json, :risk_score, :risk_level, :status, "
                ":decided_by, :decision_comment, :created_at, :decided_at)",
                record,
            )
        return record

    def list_pending(self) -> list[dict]:
        with get_conn() as conn:
            rows = conn.execute(
                "SELECT * FROM approvals WHERE status = 'pending' ORDER BY created_at DESC"
            ).fetchall()
        return dict_rows(rows)

    def list_all(self) -> list[dict]:
        with get_conn() as conn:
            rows = conn.execute("SELECT * FROM approvals ORDER BY created_at DESC").fetchall()
        return dict_rows(rows)

    def get(self, approval_id: str) -> dict | None:
        with get_conn() as conn:
            row = conn.execute("SELECT * FROM approvals WHERE id = ?", (approval_id,)).fetchone()
        return dict(row) if row else None

    def decide(self, approval_id: str, approved: bool, decided_by: str, comment: str | None) -> dict:
        approval = self.get(approval_id)
        if approval is None:
            raise ValueError(f"No approval found with id={approval_id}")
        if approval["status"] != "pending":
            raise ValueError(f"Approval {approval_id} was already {approval['status']}")

        now = dt.datetime.utcnow().isoformat()
        new_status = "approved" if approved else "rejected"
        with get_conn() as conn:
            conn.execute(
                "UPDATE approvals SET status = ?, decided_by = ?, decision_comment = ?, decided_at = ? WHERE id = ?",
                (new_status, decided_by, comment, now, approval_id),
            )

        payload = json.loads(approval["payload_json"])
        executed_actions = []
        if approved:
            for rec in payload.get("recommendations", []):
                executed_actions.append(
                    _action_agent.execute(approval["workflow_id"], approval["domain"], rec)
                )

        # Update the parent workflow's status + trace so GET /workflows/{id} reflects the outcome
        from app.agents.supervisor_agent import SupervisorAgent  # local import avoids circular import
        SupervisorAgent().record_approval_outcome(
            approval["workflow_id"], new_status, executed_actions, decided_by, comment
        )

        return {
            "approval_id": approval_id,
            "status": new_status,
            "executed_actions": executed_actions,
        }
