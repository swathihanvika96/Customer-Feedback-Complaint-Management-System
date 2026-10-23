import enum


class Role(str, enum.Enum):
    ADMIN = "admin"
    SUPPORT_MANAGER = "support_manager"
    SUPPORT_AGENT = "support_agent"
    CUSTOMER = "customer"


class ComplaintStatus(str, enum.Enum):
    OPEN = "open"
    ASSIGNED = "assigned"
    IN_PROGRESS = "in_progress"
    WAITING_FOR_CUSTOMER = "waiting_for_customer"
    RESOLVED = "resolved"
    CLOSED = "closed"
    REOPENED = "reopened"


class Priority(str, enum.Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"


class Severity(str, enum.Enum):
    MINOR = "minor"
    MAJOR = "major"
    CRITICAL = "critical"


class FeedbackStatus(str, enum.Enum):
    SUBMITTED = "submitted"
    REVIEWED = "reviewed"
    ARCHIVED = "archived"


class NotificationType(str, enum.Enum):
    COMPLAINT_ASSIGNED = "complaint_assigned"
    STATUS_CHANGED = "status_changed"
    NEW_COMMENT = "new_comment"
    SLA_APPROACHING = "sla_approaching"
    SLA_BREACHED = "sla_breached"
    COMPLAINT_RESOLVED = "complaint_resolved"


class AuditAction(str, enum.Enum):
    USER_REGISTERED = "user_registered"
    USER_CREATED = "user_created"
    USER_ACTIVATED = "user_activated"
    USER_DEACTIVATED = "user_deactivated"
    CUSTOMER_CREATED = "customer_created"
    CUSTOMER_UPDATED = "customer_updated"
    FEEDBACK_CREATED = "feedback_created"
    FEEDBACK_UPDATED = "feedback_updated"
    COMPLAINT_CREATED = "complaint_created"
    COMPLAINT_UPDATED = "complaint_updated"
    AGENT_ASSIGNED = "agent_assigned"
    AGENT_REASSIGNED = "agent_reassigned"
    STATUS_CHANGED = "status_changed"
    COMPLAINT_RESOLVED = "complaint_resolved"
    COMPLAINT_CLOSED = "complaint_closed"
    COMPLAINT_REOPENED = "complaint_reopened"
    SLA_RULE_UPDATED = "sla_rule_updated"


# Statuses in which a complaint still needs work (SLA clock is running).
ACTIVE_STATUSES = (
    ComplaintStatus.OPEN,
    ComplaintStatus.ASSIGNED,
    ComplaintStatus.IN_PROGRESS,
    ComplaintStatus.WAITING_FOR_CUSTOMER,
    ComplaintStatus.REOPENED,
)
FINISHED_STATUSES = (ComplaintStatus.RESOLVED, ComplaintStatus.CLOSED)

MANAGER_ROLES = (Role.ADMIN, Role.SUPPORT_MANAGER)
STAFF_ROLES = (Role.ADMIN, Role.SUPPORT_MANAGER, Role.SUPPORT_AGENT)

DEFAULT_SLA_HOURS = {Priority.HIGH: 4, Priority.MEDIUM: 12, Priority.LOW: 24}

DEFAULT_CATEGORIES = [
    ("Product Quality", "Issues or praise about product quality"),
    ("Customer Support", "Interactions with the support team"),
    ("Service Experience", "General service experience"),
    ("Delivery Experience", "Shipping and delivery"),
    ("Technical Issue", "Bugs, outages and technical problems"),
]

# Satisfaction thresholds (documented in README and /reports/satisfaction/formulas)
POSITIVE_RATING_MIN = 4
NEGATIVE_RATING_MAX = 2
