"""
InfernoX Phase 9: Admin HQ Endpoints
Platform-wide administration restricted strictly to SUPER_ADMIN users.
"""

from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from sqlalchemy import func
import structlog

from app.db.session import get_db
from app.models.saas import (
    User, Organization, OrganizationMember, Subscription, PlatformAuditLog
)
from app.models.facility import Facility
from app.models.risk_alert import Alert
from app.schemas.saas import (
    OrganizationResponse, PlatformAuditLogOut
)
from app.api.auth_deps import require_superadmin

logger = structlog.get_logger(__name__)
router = APIRouter()


@router.get("/overview")
def get_platform_overview(
    admin_user: User = Depends(require_superadmin),
    db: Session = Depends(get_db)
):
    """
    Returns platform-wide metrics across all tenants.
    """
    total_orgs = db.query(Organization).count()
    active_orgs = db.query(Organization).filter(Organization.status == "ACTIVE").count()
    total_users = db.query(User).count()
    active_users = db.query(User).filter(User.status == "ACTIVE").count()
    total_facilities = db.query(Facility).count()
    total_alerts = db.query(Alert).count()

    plan_breakdown = dict(
        db.query(Organization.plan, func.count(Organization.id))
        .group_by(Organization.plan)
        .all()
    )

    return {
        "organizations": {
            "total": total_orgs,
            "active": active_orgs,
            "by_plan": plan_breakdown
        },
        "users": {
            "total": total_users,
            "active": active_users
        },
        "intelligence": {
            "total_facilities_monitored": total_facilities,
            "total_alerts_generated": total_alerts
        },
        "system_status": "OPERATIONAL"
    }


@router.get("/organizations", response_model=List[OrganizationResponse])
def list_all_organizations(
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
    admin_user: User = Depends(require_superadmin),
    db: Session = Depends(get_db)
):
    """
    Lists all platform organizations with pagination.
    """
    return db.query(Organization).offset(offset).limit(limit).all()


@router.patch("/organizations/{org_id}/status")
def update_organization_status(
    org_id: str,
    status: str = Query(..., pattern="^(ACTIVE|SUSPENDED|TRIAL|DEACTIVATED)$"),
    admin_user: User = Depends(require_superadmin),
    db: Session = Depends(get_db)
):
    """
    Suspends, activates, or deactivates an organization across the platform.
    """
    org = db.query(Organization).filter(Organization.id == org_id).first()
    if not org:
        raise HTTPException(status_code=404, detail="Organization not found.")

    old_status = org.status
    org.status = status

    audit = PlatformAuditLog(
        actor_id=admin_user.id,
        actor_email=admin_user.email,
        organization_id=org.id,
        action="admin.organization_status_changed",
        resource_type="Organization",
        resource_id=org.id,
        details={"old_status": old_status, "new_status": status}
    )
    db.add(audit)
    db.commit()

    return {"message": f"Organization status updated to {status}", "org_id": org_id}


@router.get("/audit-logs", response_model=List[PlatformAuditLogOut])
def list_platform_audit_logs(
    limit: int = Query(50, ge=1, le=500),
    offset: int = Query(0, ge=0),
    action: Optional[str] = None,
    org_id: Optional[str] = None,
    admin_user: User = Depends(require_superadmin),
    db: Session = Depends(get_db)
):
    """
    Queries platform-wide audit log trail with optional filters.
    """
    query = db.query(PlatformAuditLog)
    if action:
        query = query.filter(PlatformAuditLog.action == action)
    if org_id:
        query = query.filter(PlatformAuditLog.organization_id == org_id)

    return query.order_by(PlatformAuditLog.created_at.desc()).offset(offset).limit(limit).all()
