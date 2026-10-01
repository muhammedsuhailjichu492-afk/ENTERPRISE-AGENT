"""Pydantic schemas shared across the API layer and agents."""
from typing import Any, Optional
from pydantic import BaseModel, Field


class AnalyzeRequest(BaseModel):
    query: str = Field(..., description="Business question or operational concern, in plain English.")
    domain: str = Field(..., description="One of: production, inventory, quality, operations, "
                                          "procurement, hr, sales, finance, projects, reporting.")


class Recommendation(BaseModel):
    action: str
    rationale: str
    priority: str  # low | medium | high
    expected_impact: str
    action_type: str  # maps to an ActionAgent handler


class DecisionOutput(BaseModel):
    root_cause: str
    summary: str
    recommendations: list[Recommendation]
    confidence: float


class RiskAssessment(BaseModel):
    score: int
    level: str  # low | medium | high | critical
    factors: list[str]
    requires_approval: bool


class ApprovalDecisionRequest(BaseModel):
    approved: bool
    decided_by: str = "operations_manager"
    comment: Optional[str] = None


class WorkflowResponse(BaseModel):
    workflow_id: str
    domain: str
    query: str
    status: str
    trace: dict[str, Any]
