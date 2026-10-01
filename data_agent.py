"""
Data Agent — first stop in the pipeline. Pulls the relevant slice of
enterprise data for the requested domain and produces both a structured
summary (for the ML Agent) and a compact text digest (for the Decision Agent
prompt).
"""
import pandas as pd
from app.database import get_conn, dict_rows

# Which table(s) back each domain, and which numeric column is the primary
# metric the ML Agent should look for anomalies/trends in.
DOMAIN_TABLE_MAP = {
    "production": {"table": "production", "metric": "defect_units", "order": "date"},
    "inventory": {"table": "inventory", "metric": "quantity_on_hand", "order": "date"},
    "quality": {"table": "quality", "metric": "failures", "order": "date"},
    "operations": {"table": "production", "metric": "downtime_minutes", "order": "date"},
    "procurement": {"table": "procurement", "metric": "on_time", "order": "date"},
    "hr": {"table": "hr", "metric": "attrition_count", "order": "date"},
    "sales": {"table": "sales", "metric": "revenue", "order": "date"},
    "finance": {"table": "finance", "metric": "actual_spend", "order": "date"},
    "projects": {"table": "projects", "metric": "actual_spend", "order": "name"},
    "reporting": {"table": "sales", "metric": "revenue", "order": "date"},  # cross-domain default
}


class DataAgent:
    name = "data_agent"

    def gather(self, domain: str, limit: int = 200) -> dict:
        domain = domain.lower().strip()
        if domain not in DOMAIN_TABLE_MAP:
            domain = "operations"

        cfg = DOMAIN_TABLE_MAP[domain]
        with get_conn() as conn:
            rows = conn.execute(
                f"SELECT * FROM {cfg['table']} ORDER BY {cfg['order']} DESC LIMIT ?", (limit,)
            ).fetchall()
        records = dict_rows(rows)
        records.reverse()  # chronological order for trend analysis

        df = pd.DataFrame(records)
        summary = self._summarize(df, cfg["metric"])

        return {
            "domain": domain,
            "table": cfg["table"],
            "metric_column": cfg["metric"],
            "record_count": len(records),
            "records": records,
            "summary": summary,
        }

    @staticmethod
    def _summarize(df: pd.DataFrame, metric: str) -> dict:
        if df.empty or metric not in df.columns:
            return {"note": "No records found for this domain in the selected window."}

        numeric = pd.to_numeric(df[metric], errors="coerce").dropna()
        if numeric.empty:
            return {"note": f"Metric column '{metric}' had no numeric values."}

        return {
            "metric": metric,
            "count": int(numeric.count()),
            "mean": round(float(numeric.mean()), 3),
            "min": round(float(numeric.min()), 3),
            "max": round(float(numeric.max()), 3),
            "std": round(float(numeric.std() or 0.0), 3),
            "recent_avg_last5": round(float(numeric.tail(5).mean()), 3) if len(numeric) >= 5 else None,
            "baseline_avg_first_half": round(float(numeric.head(max(1, len(numeric) // 2)).mean()), 3),
        }
