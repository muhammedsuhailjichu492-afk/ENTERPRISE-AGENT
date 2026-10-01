
import json
from app.llm_client import complete_json

VALID_ACTION_TYPES = [
    "create_reorder", "send_alert", "escalate_to_manager", "hold_shipment",
    "create_hr_ticket", "adjust_budget_flag", "supplier_review", "notify",
    "schedule_maintenance", "launch_promotion",
]

SYSTEM_PROMPT = (
    "You are the Decision Agent in an autonomous enterprise operations platform. You receive "
    "a data summary, live SQL query results, ML anomaly/trend findings, and relevant company "
    "policy excerpts (RAG context) for one business domain. Produce a concise root-cause "
    "analysis and a ranked list of concrete, executable recommendations grounded in the policy "
    "context provided. Do not invent policy that wasn't given to you.\n\n"
    "Respond as JSON with this exact shape:\n"
    "{\n"
    '  "root_cause": "string, 1-3 sentences",\n'
    '  "summary": "string, plain-language summary for a business reader",\n'
    '  "recommendations": [\n'
    "    {\n"
    '      "action": "short imperative action",\n'
    '      "rationale": "why, tied to the data/policy",\n'
    '      "priority": "low|medium|high",\n'
    '      "expected_impact": "short business impact statement",\n'
    f'      "action_type": "one of {VALID_ACTION_TYPES}"\n'
    "    }\n"
    "  ],\n"
    '  "confidence": 0.0-1.0\n'
    "}"
)


class DecisionAgent:
    name = "decision_agent"

    def recommend(self, query: str, domain: str, data_summary: dict,
                   sql_result: dict, ml_findings: dict, rag_context: dict) -> dict:
        prompt = self._build_prompt(query, domain, data_summary, sql_result, ml_findings, rag_context)
        try:
            result = complete_json(SYSTEM_PROMPT, prompt, max_tokens=1400)
        except ValueError as exc:
            result = {
                "root_cause": f"Decision Agent could not parse a structured response ({exc}).",
                "summary": "Falling back to raw findings — see data_summary and ml_findings in the trace.",
                "recommendations": [],
                "confidence": 0.0,
            }

        result.setdefault("recommendations", [])
        result.setdefault("confidence", 0.5)

        for rec in result["recommendations"]:
            if rec.get("action_type") not in VALID_ACTION_TYPES:
                rec["action_type"] = "notify"
            rec.setdefault("priority", "medium")

        return result

    @staticmethod
    def _build_prompt(query, domain, data_summary, sql_result, ml_findings, rag_context) -> str:
        return (
            f"DOMAIN: {domain}\n"
            f"OPERATOR QUESTION: {query}\n\n"
            f"DATA SUMMARY:\n{json.dumps(data_summary, default=str)}\n\n"
            f"SQL AGENT RESULT (sql='{sql_result.get('sql')}'):\n"
            f"{json.dumps(sql_result.get('rows', [])[:20], default=str)}\n\n"
            f"ML FINDINGS:\n{json.dumps(ml_findings, default=str)}\n\n"
            f"RELEVANT POLICY CONTEXT (RAG):\n"
            f"{json.dumps([{'title': r['title'], 'text': r['text']} for r in rag_context.get('results', [])], default=str)}\n"
        )
