"""
Action Agent — the final step. Executes a recommendation once it has either
been auto-cleared (low risk) or explicitly approved by a human. Each
action_type maps to a handler; in this reference implementation the handlers
are simulated (they log a structured result) but are written as the natural
seam for wiring up real systems (ERP, ticketing, email, Slack, etc).
"""
import json
import uuid
import datetime as dt
from app.database import get_conn


def _handle_create_reorder(rec: dict, domain: str) -> dict:
    return {"system": "ERP/Procurement", "operation": "purchase_order.create",
            "detail": f"Draft purchase order created for review: {rec['action']}"}


def _handle_send_alert(rec: dict, domain: str) -> dict:
    return {"system": "Alerting", "operation": "alert.send",
            "detail": f"Alert dispatched to {domain} channel: {rec['action']}"}


def _handle_escalate_to_manager(rec: dict, domain: str) -> dict:
    return {"system": "Ticketing", "operation": "escalation.create",
            "detail": f"Escalation ticket opened for {domain} manager: {rec['action']}"}


def _handle_hold_shipment(rec: dict, domain: str) -> dict:
    return {"system": "WMS", "operation": "shipment.hold",
            "detail": f"Shipment hold flag set: {rec['action']}"}


def _handle_create_hr_ticket(rec: dict, domain: str) -> dict:
    return {"system": "HRIS", "operation": "case.create",
            "detail": f"HR case created: {rec['action']}"}


def _handle_adjust_budget_flag(rec: dict, domain: str) -> dict:
    return {"system": "Finance", "operation": "budget.flag",
            "detail": f"Budget variance flagged for review: {rec['action']}"}


def _handle_supplier_review(rec: dict, domain: str) -> dict:
    return {"system": "Procurement", "operation": "supplier.review.open",
            "detail": f"Supplier performance review opened: {rec['action']}"}


def _handle_schedule_maintenance(rec: dict, domain: str) -> dict:
    return {"system": "CMMS", "operation": "workorder.create",
            "detail": f"Maintenance work order scheduled: {rec['action']}"}


def _handle_launch_promotion(rec: dict, domain: str) -> dict:
    return {"system": "CRM", "operation": "campaign.create",
            "detail": f"Promotion campaign drafted: {rec['action']}"}


def _handle_notify(rec: dict, domain: str) -> dict:
    return {"system": "Notification", "operation": "notify.log",
            "detail": rec['action']}


HANDLERS = {
    "create_reorder": _handle_create_reorder,
    "send_alert": _handle_send_alert,
    "escalate_to_manager": _handle_escalate_to_manager,
    "hold_shipment": _handle_hold_shipment,
    "create_hr_ticket": _handle_create_hr_ticket,
    "adjust_budget_flag": _handle_adjust_budget_flag,
    "supplier_review": _handle_supplier_review,
    "schedule_maintenance": _handle_schedule_maintenance,
    "launch_promotion": _handle_launch_promotion,
    "notify": _handle_notify,
}


class ActionAgent:
    name = "action_agent"

    def execute(self, workflow_id: str, domain: str, recommendation: dict) -> dict:
        handler = HANDLERS.get(recommendation.get("action_type"), _handle_notify)
        action_id = str(uuid.uuid4())
        try:
            result = handler(recommendation, domain)
            status = "executed"
        except Exception as exc:  # noqa: BLE001
            result = {"error": str(exc)}
            status = "failed"

        record = {
            "id": action_id,
            "workflow_id": workflow_id,
            "domain": domain,
            "action_type": recommendation.get("action_type", "notify"),
            "description": recommendation.get("action", ""),
            "result_json": json.dumps(result),
            "status": status,
            "created_at": dt.datetime.utcnow().isoformat(),
        }
        with get_conn() as conn:
            conn.execute(
                "INSERT INTO actions (id, workflow_id, domain, action_type, description, result_json, status, created_at) "
                "VALUES (:id, :workflow_id, :domain, :action_type, :description, :result_json, :status, :created_at)",
                record,
            )
        return {**record, "result": result}
