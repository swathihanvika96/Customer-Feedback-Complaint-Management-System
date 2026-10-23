from fastapi import APIRouter

from app.api.v1.endpoints import (
    agents, assignments, audit_logs, auth, categories, comments, complaints, customers,
    dashboard, feedback, notifications, reports, resolutions, sla, users,
)

api_router = APIRouter()
for module in (
    auth, users, customers, agents, categories, feedback, complaints, assignments,
    comments, resolutions, sla, notifications, dashboard, reports, audit_logs,
):
    api_router.include_router(module.router)
