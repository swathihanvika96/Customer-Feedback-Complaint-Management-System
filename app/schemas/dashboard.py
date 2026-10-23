from datetime import date

from pydantic import BaseModel


class PriorityCount(BaseModel):
    priority: str
    count: int


class DashboardSummary(BaseModel):
    date_from: date | None
    date_to: date | None
    total_customers: int
    total_feedback: int
    total_complaints: int
    open_complaints: int
    resolved_complaints: int
    overdue_complaints: int
    average_resolution_hours: float | None
    average_customer_rating: float | None
    complaints_by_priority: list[PriorityCount]


class AgentComplaintCount(BaseModel):
    agent_id: int
    agent_name: str
    total: int
    open: int
    resolved: int
    overdue: int
