
import re
from app.database import get_conn, dict_rows
from app.llm_client import complete
from app.agents.data_agent import DOMAIN_TABLE_MAP

SCHEMA_DESCRIPTIONS = {
    "production": "production(id, date, line, units_planned, units_produced, defect_units, downtime_minutes)",
    "inventory": "inventory(id, date, sku, warehouse, quantity_on_hand, reorder_point, unit_cost)",
    "sales": "sales(id, date, region, product, units_sold, revenue)",
    "hr": "hr(id, date, department, headcount, open_positions, attrition_count)",
    "finance": "finance(id, date, department, budget, actual_spend)",
    "procurement": "procurement(id, date, supplier, item, order_qty, lead_time_days, on_time)",
    "quality": "quality(id, date, line, inspections, failures, complaint_count)",
    "projects": "projects(id, name, department, status, percent_complete, budget, actual_spend, due_date)",
}

FORBIDDEN = re.compile(r"\b(INSERT|UPDATE|DELETE|DROP|ALTER|ATTACH|PRAGMA|CREATE|REPLACE)\b", re.IGNORECASE)

SYSTEM_PROMPT = (
    "You are the SQL Agent inside an enterprise operations platform. You write a single "
    "SQLite SELECT statement that answers the user's question using ONLY the provided table "
    "schema. Never write INSERT/UPDATE/DELETE/DROP or any statement that modifies data. "
    "Always include a LIMIT clause (max 50) unless the question requires an aggregate. "
    "Return ONLY the raw SQL statement, nothing else — no explanation, no markdown fences."
)


class SQLAgent:
    name = "sql_agent"

    def query(self, question: str, domain: str) -> dict:
        domain = domain.lower().strip()
        table_cfg = DOMAIN_TABLE_MAP.get(domain, DOMAIN_TABLE_MAP["operations"])
        table = table_cfg["table"]
        schema = SCHEMA_DESCRIPTIONS.get(table, "")

        prompt = f"Table schema:\n{schema}\n\nQuestion: {question}\n\nWrite the SQLite SELECT statement."
        sql = complete(SYSTEM_PROMPT, prompt, max_tokens=300).strip().rstrip(";")

        is_safe, reason = self._validate(sql, allowed_table=table)
        if not is_safe:
            return {
                "sql": sql,
                "executed": False,
                "reason": reason,
                "rows": [],
            }

        try:
            with get_conn() as conn:
                rows = conn.execute(sql).fetchall()
            return {"sql": sql, "executed": True, "reason": None, "rows": dict_rows(rows)[:50]}
        except Exception as exc:  # noqa: BLE001 — surface any SQLite error to the trace
            return {"sql": sql, "executed": False, "reason": f"SQL execution error: {exc}", "rows": []}

    @staticmethod
    def _validate(sql: str, allowed_table: str) -> tuple[bool, str | None]:
        if not sql or not sql.strip().upper().startswith("SELECT"):
            return False, "Rejected: statement is not a SELECT."
        if FORBIDDEN.search(sql):
            return False, "Rejected: statement contains a disallowed keyword (only read queries are permitted)."
        if ";" in sql:
            return False, "Rejected: multiple statements are not permitted."
        if allowed_table.lower() not in sql.lower():
            return False, f"Rejected: query must reference the '{allowed_table}' table for this domain."
        return True, None
