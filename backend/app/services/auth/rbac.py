from enum import Enum
from typing import Set, Dict, List

class Role(str, Enum):
    SUPER_ADMIN = "SUPER_ADMIN"
    ORG_ADMIN = "ORG_ADMIN"
    ANALYST = "ANALYST"
    OPERATOR = "OPERATOR"
    VIEWER = "VIEWER"
    REPORT_MANAGER = "REPORT_MANAGER"

class Permission(str, Enum):
    # Events & Detections
    EVENTS_READ = "events.read"
    EVENTS_INVESTIGATE = "events.investigate"
    EVENTS_REVIEW = "events.review"

    # Facilities
    FACILITIES_READ = "facilities.read"
    FACILITIES_MANAGE = "facilities.manage"

    # Alerts & Anti-storm
    ALERTS_READ = "alerts.read"
    ALERTS_MANAGE = "alerts.manage"
    ALERTS_ACKNOWLEDGE = "alerts.acknowledge"
    ALERTS_ESCALATE = "alerts.escalate"

    # Reports
    REPORTS_READ = "reports.read"
    REPORTS_CREATE = "reports.create"
    REPORTS_EXPORT = "reports.export"

    # Analytics
    ANALYTICS_READ = "analytics.read"

    # Users & Team
    USERS_READ = "users.read"
    USERS_MANAGE = "users.manage"

    # Organization & Settings
    ORGANIZATION_READ = "organization.read"
    ORGANIZATION_MANAGE = "organization.manage"

    # Billing & Subscriptions
    BILLING_READ = "billing.read"
    BILLING_MANAGE = "billing.manage"

    # Platform & System
    SYSTEM_READ = "system.read"
    SYSTEM_MANAGE = "system.manage"


# Granular Role Permission Matrix
ROLE_PERMISSIONS: Dict[Role, Set[Permission]] = {
    Role.SUPER_ADMIN: {
        Permission.EVENTS_READ,
        Permission.EVENTS_INVESTIGATE,
        Permission.EVENTS_REVIEW,
        Permission.FACILITIES_READ,
        Permission.FACILITIES_MANAGE,
        Permission.ALERTS_READ,
        Permission.ALERTS_MANAGE,
        Permission.ALERTS_ACKNOWLEDGE,
        Permission.ALERTS_ESCALATE,
        Permission.REPORTS_READ,
        Permission.REPORTS_CREATE,
        Permission.REPORTS_EXPORT,
        Permission.ANALYTICS_READ,
        Permission.USERS_READ,
        Permission.USERS_MANAGE,
        Permission.ORGANIZATION_READ,
        Permission.ORGANIZATION_MANAGE,
        Permission.BILLING_READ,
        Permission.BILLING_MANAGE,
        Permission.SYSTEM_READ,
        Permission.SYSTEM_MANAGE,
    },
    Role.ORG_ADMIN: {
        Permission.EVENTS_READ,
        Permission.EVENTS_INVESTIGATE,
        Permission.EVENTS_REVIEW,
        Permission.FACILITIES_READ,
        Permission.FACILITIES_MANAGE,
        Permission.ALERTS_READ,
        Permission.ALERTS_MANAGE,
        Permission.ALERTS_ACKNOWLEDGE,
        Permission.ALERTS_ESCALATE,
        Permission.REPORTS_READ,
        Permission.REPORTS_CREATE,
        Permission.REPORTS_EXPORT,
        Permission.ANALYTICS_READ,
        Permission.USERS_READ,
        Permission.USERS_MANAGE,
        Permission.ORGANIZATION_READ,
        Permission.ORGANIZATION_MANAGE,
        Permission.BILLING_READ,
        Permission.BILLING_MANAGE,
        Permission.SYSTEM_READ,
    },
    Role.ANALYST: {
        Permission.EVENTS_READ,
        Permission.EVENTS_INVESTIGATE,
        Permission.EVENTS_REVIEW,
        Permission.FACILITIES_READ,
        Permission.ALERTS_READ,
        Permission.ALERTS_ACKNOWLEDGE,
        Permission.REPORTS_READ,
        Permission.REPORTS_CREATE,
        Permission.REPORTS_EXPORT,
        Permission.ANALYTICS_READ,
        Permission.USERS_READ,
        Permission.ORGANIZATION_READ,
        Permission.SYSTEM_READ,
    },
    Role.OPERATOR: {
        Permission.EVENTS_READ,
        Permission.EVENTS_INVESTIGATE,
        Permission.FACILITIES_READ,
        Permission.ALERTS_READ,
        Permission.ALERTS_ACKNOWLEDGE,
        Permission.ALERTS_ESCALATE,
        Permission.REPORTS_READ,
        Permission.ANALYTICS_READ,
        Permission.ORGANIZATION_READ,
        Permission.SYSTEM_READ,
    },
    Role.REPORT_MANAGER: {
        Permission.EVENTS_READ,
        Permission.FACILITIES_READ,
        Permission.ALERTS_READ,
        Permission.REPORTS_READ,
        Permission.REPORTS_CREATE,
        Permission.REPORTS_EXPORT,
        Permission.ANALYTICS_READ,
        Permission.ORGANIZATION_READ,
    },
    Role.VIEWER: {
        Permission.EVENTS_READ,
        Permission.FACILITIES_READ,
        Permission.ALERTS_READ,
        Permission.REPORTS_READ,
        Permission.ANALYTICS_READ,
        Permission.ORGANIZATION_READ,
    }
}


def has_permission(role: str, permission: str) -> bool:
    """
    Check if a given role possesses a specific permission.
    """
    try:
        r = Role(role)
        p = Permission(permission)
        return p in ROLE_PERMISSIONS.get(r, set())
    except (ValueError, KeyError):
        return False


def get_role_permissions(role: str) -> List[str]:
    """
    Get all permission string identifiers for a role.
    """
    try:
        r = Role(role)
        return sorted([p.value for p in ROLE_PERMISSIONS.get(r, set())])
    except ValueError:
        return []
