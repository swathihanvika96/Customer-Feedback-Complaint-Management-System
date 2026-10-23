from datetime import date

from pydantic import BaseModel


class SatisfactionSummary(BaseModel):
    total_feedback: int
    average_rating: float | None
    positive_count: int
    neutral_count: int
    negative_count: int
    satisfaction_percentage: float


class CategorySatisfaction(BaseModel):
    category_id: int
    category_name: str
    total_feedback: int
    average_rating: float | None
    positive_count: int
    negative_count: int
    satisfaction_percentage: float


class TrendPoint(BaseModel):
    date: date
    total_feedback: int
    average_rating: float | None


class ResolvedComplaintSatisfaction(SatisfactionSummary):
    resolved_complaints: int
    resolved_with_feedback: int
    feedback_response_rate: float


class ComplaintsByCategory(BaseModel):
    category_id: int
    category_name: str
    total: int
    open: int
    resolved: int


class AgentPerformance(BaseModel):
    agent_id: int
    agent_name: str
    assigned: int
    resolved: int
    average_resolution_hours: float | None
