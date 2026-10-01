"""
Risk Engine — rule-based (deliberately not LLM-based, for auditability)
scoring that decides whether a workflow's recommendations can auto-execute
or must stop for human approval. Combines ML anomaly severity, domain
criticality, and keyword-based impact signals from the Decision Agent's
own recommendation text.
"""
from app.config import settings

DOMAIN_CRITICALITY = {
    "quality": 25,       # customer/safety facing
    "finance": 20,
    "hr": 15,
    "procurement": 15,
    "production": 15,
    "inventory": 10,
    "sales": 10,
    "operations": 10,
    "projects": 10,
    "reporting": 5,
}

HIGH_IMPACT_KEYWORDS = [
    "shutdown", "halt", "hold shipment", "terminate", "layoff", "recall",
    "switch supplier", "legal", "compliance", "safety", "customer refund",
]

PRIORITY_WEIGHT = {"low": 5, "medium": 15, "high": 30}

HIGH_RISK_ACTION_TYPES = {"hold_shipment", "supplier_review", "adjust_budget_flag"}


class RiskEngine:
    name = "risk_engine"

    def assess(self, decision_output: dict, ml_findings: dict, domain: str) -> dict:
        score = 0
        factors = []

        domain_points = DOMAIN_CRITICALITY.get(domain, 10)
        score += domain_points
        factors.append(f"Domain '{domain}' base criticality: +{domain_points}")

        anomaly_rate = ml_findings.get("anomaly_rate") or 0.0
        anomaly_points = min(30, int(anomaly_rate * 300))
        if anomaly_points:
            score += anomaly_points
            factors.append(f"ML anomaly rate {anomaly_rate:.1%}: +{anomaly_points}")

        trend = ml_findings.get("trend") or {}
        pct_change = abs(trend.get("pct_change_first_vs_second_half") or 0)
        if pct_change >= 20:
            score += 15
            factors.append(f"Sharp trend shift of {pct_change:.1f}% across the window: +15")

        recs = decision_output.get("recommendations", [])
        max_priority_points = 0
        keyword_hit = False
        action_type_hit = False
        for rec in recs:
            max_priority_points = max(max_priority_points, PRIORITY_WEIGHT.get(rec.get("priority", "low"), 5))
            text = f"{rec.get('action', '')} {rec.get('rationale', '')}".lower()
            if any(kw in text for kw in HIGH_IMPACT_KEYWORDS):
                keyword_hit = True
            if rec.get("action_type") in HIGH_RISK_ACTION_TYPES:
                action_type_hit = True

        if max_priority_points:
            score += max_priority_points
            factors.append(f"Highest recommendation priority contributes: +{max_priority_points}")

        if keyword_hit:
            score += 20
            factors.append("Recommendation language matches a high-impact keyword: +20")

        if action_type_hit:
            score += 15
            factors.append("Recommendation includes a high-risk action type (e.g. hold shipment, supplier switch): +15")

        confidence = decision_output.get("confidence", 0.5)
        if confidence < 0.4:
            score += 10
            factors.append(f"Low Decision Agent confidence ({confidence}): +10")

        score = max(0, min(100, score))
        level = self._level(score)
        requires_approval = score >= settings.RISK_APPROVAL_THRESHOLD or keyword_hit or action_type_hit

        return {
            "score": score,
            "level": level,
            "factors": factors,
            "requires_approval": requires_approval,
            "threshold": settings.RISK_APPROVAL_THRESHOLD,
        }

    @staticmethod
    def _level(score: int) -> str:
        if score >= 80:
            return "critical"
        if score >= 55:
            return "high"
        if score >= 30:
            return "medium"
        return "low"
