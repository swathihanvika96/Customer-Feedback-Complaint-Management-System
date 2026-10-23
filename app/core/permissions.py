from sqlalchemy.orm import Session

from app.core.constants import MANAGER_ROLES, Role
from app.core.exceptions import ForbiddenError
from app.models import Complaint, User
from app.repositories import agent_repository, customer_repository


def is_manager(user: User) -> bool:
    return user.role in MANAGER_ROLES


def is_staff(user: User) -> bool:
    return user.role != Role.CUSTOMER


def ensure_can_access_complaint(db: Session, user: User, complaint: Complaint) -> None:
    """Admins/managers: all. Agents: only complaints assigned to them. Customers: only their own."""
    if is_manager(user):
        return
    if user.role == Role.CUSTOMER:
        customer = customer_repository.get_by_user_id(db, user.id)
        if customer and customer.id == complaint.customer_id:
            return
    elif user.role == Role.SUPPORT_AGENT:
        agent = agent_repository.get_by_user_id(db, user.id)
        if agent and complaint.assigned_agent_id == agent.id:
            return
    raise ForbiddenError("You do not have access to this complaint")


def ensure_can_work_complaint(db: Session, user: User, complaint: Complaint) -> None:
    """Staff who may change a complaint's state: managers/admins or the assigned agent."""
    if is_manager(user):
        return
    if user.role == Role.SUPPORT_AGENT:
        agent = agent_repository.get_by_user_id(db, user.id)
        if agent and complaint.assigned_agent_id == agent.id:
            return
    raise ForbiddenError("Only a manager or the assigned agent can perform this action")
