
from fastapi.testclient import TestClient


def test_data_agent_returns_summary():
    from app.agents.data_agent import DataAgent
    result = DataAgent().gather("production")
    assert result["domain"] == "production"
    assert result["record_count"] > 0
    assert "mean" in result["summary"]


def test_ml_agent_flags_anomalies_on_synthetic_drift():
    from app.agents.data_agent import DataAgent
    from app.agents.ml_agent import MLAgent

    data = DataAgent().gather("production")
    ml_result = MLAgent().analyze(data["records"], data["metric_column"])
    assert "anomaly_rate" in ml_result
    assert ml_result["anomaly_rate"] >= 0.0


def test_sql_agent_rejects_unsafe_queries():
    from app.agents.sql_agent import SQLAgent
    agent = SQLAgent()
    safe, reason = agent._validate("DROP TABLE production", allowed_table="production")
    assert not safe
    safe, reason = agent._validate("SELECT * FROM production; DELETE FROM production", allowed_table="production")
    assert not safe
    safe, reason = agent._validate("SELECT * FROM production LIMIT 5", allowed_table="production")
    assert safe


def test_rag_agent_retrieves_domain_policy():
    from app.agents.rag_agent import RAGAgent
    result = RAGAgent().retrieve("defect rate deviation", "production")
    assert len(result["results"]) > 0
    assert any("defect" in r["text"].lower() or "production" in r["domain"] for r in result["results"])


def test_risk_engine_flags_high_impact_keywords():
    from app.agents.risk_engine import RiskEngine
    decision_output = {
        "confidence": 0.9,
        "recommendations": [
            {"action": "Hold shipment for lot 4471", "rationale": "quality issue",
             "priority": "high", "action_type": "hold_shipment"}
        ],
    }
    risk = RiskEngine().assess(decision_output, {"anomaly_rate": 0.1, "trend": {}}, "quality")
    assert risk["requires_approval"] is True
    assert risk["score"] > 0


def test_full_pipeline_runs_end_to_end():
    from app.agents.supervisor_agent import SupervisorAgent
    result = SupervisorAgent().run_workflow("Why is Line-A's defect rate rising?", "production")
    assert result["status"] in ("completed", "awaiting_approval")
    assert "decision" in result and "risk" in result
    assert len(result["trace"]["steps"]) >= 6  # data, sql, ml, rag, decision, risk (+ approval/action)


def test_api_health():
    from app.main import app
    client = TestClient(app)
    res = client.get("/api/health")
    assert res.status_code == 200
    assert "domains" in res.json()


def test_api_analyze_and_workflow_retrieval():
    from app.main import app
    client = TestClient(app)
    res = client.post("/api/analyze", json={"query": "Which SKUs need reordering?", "domain": "inventory"})
    assert res.status_code == 200
    body = res.json()
    workflow_id = body["workflow_id"]

    res2 = client.get(f"/api/workflows/{workflow_id}")
    assert res2.status_code == 200
    assert res2.json()["id"] == workflow_id


def test_api_rejects_unknown_domain():
    from app.main import app
    client = TestClient(app)
    res = client.post("/api/analyze", json={"query": "test", "domain": "not_a_real_domain"})
    assert res.status_code == 400
